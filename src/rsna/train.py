"""Train CenterNet-lite on split==train, select the epoch / score threshold on split==val (never touches test).

CLI: python -m rsna.train --config configs/baseline.yaml --seed 0 [--run-name X] [--overwrite]
     [--max-steps N --limit-train N --limit-val N --smoke] [--set train.epochs=2 --set aug.hflip=true]
An existing results/<run> or runs/<run> is refused unless --overwrite (which deletes both first), so results,
checkpoint and later test metrics always describe one training run. --max-steps N trains exactly N steps.
Outputs: results/<run>/ (config.yaml, meta.json, history.csv, val_predictions.csv, val_image_scores.csv,
threshold_sweep.csv, curves.png, threshold.png), runs/<run>/best.pt, MLflow run, a row in results/experiments.csv.
Batches are sliced from a uint8 RAM tensor in the main process (DataLoader spawn workers were slower on macOS).
MPS kernels are not bit-deterministic, so reruns with the same seed agree only approximately.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import platform
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import yaml
from sklearn.metrics import roc_auc_score

from . import paths
from .augment import augment_batch
from .dataset import Data, RSNADataset, collate, iterate_batches, load_data
from .decode import predict, to_frames
from .evaluate import write_preds
from .metric import load_gt, preds_from_df, threshold_sweep
from .model import build_model, centernet_loss, save_checkpoint
from .targets import build_targets
from .tracking import Tracker, append_ledger
from .utils import get_device, git_revision, load_config, save_config, seed_everything

LOG_EVERY = 50


def apply_overrides(cfg: dict[str, Any], items: list[str]) -> dict[str, Any]:
    """`a.b.c=value` overrides (value parsed as YAML)."""
    cfg = copy.deepcopy(cfg)
    for item in items:
        key, val = item.split("=", 1)
        *parents, leaf = key.split(".")
        node = cfg
        for p in parents:
            node = node.setdefault(p, {})
        node[leaf] = yaml.safe_load(val)
    return cfg


def lr_factor(step: int, warmup: int, total: int) -> float:
    if step < warmup:
        return (step + 1) / warmup
    return 0.5 * (1 + math.cos(math.pi * min(1.0, (step - warmup) / max(1, total - warmup))))


def plan_steps(n_train: int, batch_size: int, epochs: int, max_steps: int | None) -> tuple[int, int, int]:
    """(steps/epoch, total steps, epochs). max_steps, when given, is the exact step count (epochs grow to fit)."""
    spe = n_train // batch_size
    if spe < 1:
        raise ValueError(f"{n_train} train images < batch_size {batch_size}: no full batch (drop_last)")
    total = spe * epochs if max_steps is None else max_steps
    return spe, total, math.ceil(total / spe)


def prepare_dirs(out_dir: Path, run_dir: Path, overwrite: bool) -> None:
    """Refuse to mix two trainings under one run name; with overwrite, delete the old results and checkpoint."""
    used = [d for d in (out_dir, run_dir) if d.exists() and any(d.iterdir())]
    if used and not overwrite:
        raise FileExistsError(f"{', '.join(map(str, used))} already exist(s); pick another --run-name or pass --overwrite")
    for d in used:
        shutil.rmtree(d)
    out_dir.mkdir(parents=True, exist_ok=True)


def subsample(idx: np.ndarray, n: int | None, seed: int) -> np.ndarray:
    if n is None or n >= len(idx):
        return idx
    return np.sort(np.random.default_rng(seed).choice(idx, n, replace=False))


def validate(model: torch.nn.Module, data: Data, idx: np.ndarray, cfg: dict[str, Any], device: torch.device,
             gt: dict[str, np.ndarray]) -> dict[str, Any]:
    t0 = time.time()
    ids = data.meta.loc[idx, "patientId"].tolist()
    dets, img_scores = predict(model, data.images[torch.from_numpy(idx)], cfg, device, cfg["train"]["eval_batch_size"])
    pred_df, img_df = to_frames(ids, dets, img_scores)
    sweep = threshold_sweep(gt, preds_from_df(pred_df), ids)
    best = sweep.loc[sweep["map"].idxmax()]
    y = data.meta.loc[idx, "target"].to_numpy()
    auc = roc_auc_score(y, img_df["image_score"]) if 0 < y.sum() < len(y) else float("nan")
    return {"val_map": float(best["map"]), "val_thr": float(best["thr"]), "val_auc": float(auc),
            "sweep": sweep, "pred": pred_df, "img": img_df, "val_sec": time.time() - t0}


def plot_curves(hist: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    for c in [c for c in hist.columns if c.startswith("loss")]:
        ax[0].plot(hist["epoch"], hist[c], marker="o", label=c)
    ax[0].set(xlabel="epoch", ylabel="train loss", title="Train loss", yscale="log")
    ax[0].legend()
    ax[1].plot(hist["epoch"], hist["val_map"], marker="o", label="val mAP (best thr)")
    ax[1].plot(hist["epoch"], hist["val_auc"], marker="s", label="val image AUC")
    ax[1].set(xlabel="epoch", title="Validation")
    ax[1].legend()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def plot_threshold(sweep: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(5, 3.6))
    ax.plot(sweep["thr"], sweep["map"], marker="o")
    b = sweep.loc[sweep["map"].idxmax()]
    ax.axvline(b["thr"], ls="--", c="gray")
    ax.set(xlabel="score threshold", ylabel="val RSNA mAP", title=f"best thr={b['thr']:.2f}, mAP={b['map']:.4f}")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def train(cfg: dict[str, Any], seed: int, run_name: str, max_steps: int | None = None,
          limit_train: int | None = None, limit_val: int | None = None, smoke: bool = False,
          mlflow: bool = True, config_path: str = "", overrides: list[str] | None = None,
          overwrite: bool = False) -> dict[str, Any]:
    start = datetime.now()
    out_dir, run_dir = paths.RESULTS / run_name, paths.RUNS / run_name
    prepare_dirs(out_dir, run_dir, overwrite)
    overrides = list(overrides or [])
    gen = seed_everything(seed)
    aug_rng = np.random.default_rng(seed)
    device = get_device()
    tc, dc = cfg["train"], cfg["data"]
    data = load_data(dc["image_size"], dc.get("split_file"), smoke=smoke)
    tr_idx = subsample(data.indices("train"), limit_train, seed)
    va_idx = subsample(data.indices("val"), limit_val, 0)
    val_ids = data.meta.loc[va_idx, "patientId"].tolist()
    gt = load_gt(paths.BOXES, val_ids)

    model = build_model(cfg).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=tc["lr"], weight_decay=tc["weight_decay"])
    bs = tc["batch_size"]
    spe, total, epochs = plan_steps(len(tr_idx), bs, tc["epochs"], max_steps)
    warmup = min(tc["warmup_steps"], total // 5)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: lr_factor(s, warmup, total))

    resolved = {**cfg, "run": {"name": run_name, "seed": seed, "config_path": config_path, "overrides": overrides,
                               "max_steps": max_steps, "limit_train": limit_train, "limit_val": limit_val, "smoke": smoke,
                               "n_train": int(len(tr_idx)), "n_val": int(len(va_idx)), "total_steps": total}}
    save_config(resolved, out_dir / "config.yaml")
    sha = git_revision()
    tracker = Tracker(resolved, run_name, {"seed": str(seed), "git_sha": sha, "device": str(device)}, enabled=mlflow)
    print(f"[train] {run_name}: device={device} train={len(tr_idx)} val={len(va_idx)} "
          f"steps/epoch={spe} total={total} warmup={warmup}", flush=True)

    hist: list[dict[str, Any]] = []
    best: dict[str, Any] = {"val_map": -1.0}
    step, t_train = 0, 0.0
    try:
        for epoch in range(1, epochs + 1):
            model.train()
            t0 = time.time()
            parts_acc: list[torch.Tensor] = []
            if tc.get("num_workers", 0) > 0:
                loader = torch.utils.data.DataLoader(
                    RSNADataset(data.image_size, tr_idx, data.boxes), batch_size=bs, shuffle=True, drop_last=True,
                    num_workers=tc["num_workers"], collate_fn=collate, generator=gen, persistent_workers=False)
            else:
                loader = iterate_batches(data, tr_idx, bs, shuffle=True, generator=gen)
            for xb, boxes, _ in loader:
                x = xb.to(device, non_blocking=True).unsqueeze(1).float().div_(255)
                x, boxes = augment_batch(x, boxes, cfg.get("aug"), aug_rng)
                tgt = build_targets(boxes, data.image_size, model.stride, cfg["loss"].get("gaussian_min_overlap", 0.7), device)
                out = model(x)
                loss, parts = centernet_loss(out, tgt, cfg["loss"])
                opt.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), tc["grad_clip"])
                opt.step()
                sched.step()
                step += 1
                parts_acc.append(torch.stack([loss.detach()] + [v.detach() for v in parts.values()]))
                if step % LOG_EVERY == 0:
                    recent = torch.stack(parts_acc[-LOG_EVERY:]).mean(0).tolist()
                    tracker.log_metrics({"train_step_loss": recent[0], "lr_step": sched.get_last_lr()[0]}, step=step)
                    if step % (4 * LOG_EVERY) == 0:
                        print(f"[train]   step {step}/{total} loss={recent[0]:.4f} "
                              f"{len(parts_acc) / (time.time() - t0):.2f} it/s", flush=True)
                if step >= total:
                    break
            names = ["loss"] + [f"loss_{k}" for k in parts]
            ep_loss = dict(zip(names, torch.stack(parts_acc).mean(0).tolist()))
            ep_sec = time.time() - t0
            t_train += ep_sec
            v = validate(model, data, va_idx, cfg, device, gt)
            row = {"epoch": epoch, "steps": step, **ep_loss, "val_map": v["val_map"], "val_thr": v["val_thr"],
                   "val_auc": v["val_auc"], "lr": sched.get_last_lr()[0], "epoch_sec": round(ep_sec, 1),
                   "val_sec": round(v["val_sec"], 1), "it_per_sec": round(len(parts_acc) / ep_sec, 2)}
            hist.append(row)
            tracker.log_metrics({k: val for k, val in row.items() if k != "epoch"}, step=epoch)
            print(f"[train] epoch {epoch}/{epochs} " + " ".join(
                f"{k}={val:.4f}" if isinstance(val, float) else f"{k}={val}" for k, val in row.items()), flush=True)
            if v["val_map"] > best["val_map"]:
                best = {**v, "epoch": epoch}
                save_checkpoint(run_dir / "best.pt", model, resolved, epoch=epoch, val_map=v["val_map"],
                                val_thr=v["val_thr"])
    except BaseException:
        tracker.end("FAILED")
        raise

    end = datetime.now()
    hist_df = pd.DataFrame(hist)
    hist_df.to_csv(out_dir / "history.csv", index=False)
    write_preds(best["pred"], best["img"], out_dir, "val")  # frames are pre-rounded: CSV == what was scored
    best["sweep"].to_csv(out_dir / "threshold_sweep.csv", index=False, float_format="%.5f")
    plot_curves(hist_df, out_dir / "curves.png")
    plot_threshold(best["sweep"], out_dir / "threshold.png")
    summary = {"best_epoch": best["epoch"], "val_map": round(best["val_map"], 5), "val_thr": best["val_thr"],
               "val_auc": round(best["val_auc"], 5), "train_min": round(t_train / 60, 2)}
    meta = {"run_name": run_name, "git_sha": sha, "seed": seed, "device": str(device), "torch": torch.__version__,
            "python": platform.python_version(), "platform": platform.platform(), "start": start.isoformat(timespec="seconds"),
            "end": end.isoformat(timespec="seconds"), "train_seconds": round(t_train, 1),
            "wall_seconds": round((end - start).total_seconds(), 1), "n_train": int(len(tr_idx)), "n_val": int(len(va_idx)),
            "total_steps": step, "mlflow_run_id": tracker.run_id, **summary,
            "determinism": "MPS kernels are not bit-deterministic; same-seed reruns match only approximately"}
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    tracker.log_metrics({k if k in ("best_epoch", "train_min") else f"best_{k}": v for k, v in summary.items()})
    tracker.log_dir(out_dir)
    tracker.end()
    append_ledger({"run_name": run_name, "date": start.strftime("%Y-%m-%d %H:%M"), "git_sha": sha,
                   "config": config_path, "overrides": ";".join(overrides), "seed": seed, "hypothesis": cfg.get("meta", {}).get("hypothesis", ""),
                   **summary})
    print(f"[train] done: {json.dumps(summary)} -> {out_dir}", flush=True)
    return meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--run-name")
    ap.add_argument("--max-steps", type=int)
    ap.add_argument("--limit-train", type=int)
    ap.add_argument("--limit-val", type=int)
    ap.add_argument("--smoke", action="store_true", help="allow a temporary in-memory split if split_v1.csv is missing")
    ap.add_argument("--no-mlflow", action="store_true")
    ap.add_argument("--overwrite", action="store_true", help="delete existing results/<run> and runs/<run> first")
    ap.add_argument("--set", dest="overrides", action="append", default=[], metavar="KEY=VALUE")
    a = ap.parse_args()
    cfg = apply_overrides(load_config(a.config), a.overrides)
    run_name = a.run_name or f"{Path(a.config).stem}_s{a.seed}"
    train(cfg, a.seed, run_name, a.max_steps, a.limit_train, a.limit_val, a.smoke, not a.no_mlflow, a.config,
          a.overrides, a.overwrite)


if __name__ == "__main__":
    main()
