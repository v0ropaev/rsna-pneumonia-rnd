"""Evaluate a run on val/test, compare two runs (paired bootstrap), summarize seeds.

CLI:
  python -m rsna.evaluate --run results/<run> --split {val,test} [--threshold from_val|<float>] [--limit N] [--repredict]
  python -m rsna.evaluate compare --a results/X --b results/Y --split val [--n-boot 2000]
  python -m rsna.evaluate summarize --runs results/a results/b ... --split val [--out results/summary_x]

A "run directory" holds `<split>_predictions.csv` (patientId, score, x, y, width, height), `<split>_image_scores.csv`
(patientId, image_score) and `threshold_sweep.csv` (the VAL sweep). The score threshold is always chosen on val
(`from_val`); on split=val that number is selection-biased (the threshold was fit on the same images).
split=test predicts from runs/<run>/best.pt and is the only code path, besides `rsna.baselines --split test`,
that reads test images. Outputs: results/<run>/<split>_metrics.json + .md (+ test_predictions.csv / image scores).
`--limit N` (smoke) uses the first N images of the split and writes `<split>_lim<N>_*` files instead.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from . import paths
from .metric import (IMAGE_SCORE_DECIMALS, bootstrap_ci, image_level_metrics, image_scores_from_preds, load_gt,
                     matched_iou, paired_bootstrap_diff, preds_from_df, round_preds, rsna_map, threshold_sweep)

AGE_BINS = [0, 20, 40, 60, 101]
AGE_LABELS = ["<20", "20-40", "40-60", "60+"]
SLICES = ["view", "sex", "age_bucket", "cls", "n_boxes"]
SLICE_ORDER = {"age_bucket": AGE_LABELS + ["invalid"], "n_boxes": ["0", "1", "2", "3+"]}
PRED_COLS = ["patientId", "score", "x", "y", "width", "height"]


# ----------------------------------------------------------------------------- data access

def load_meta(split_file: str | Path | None = None) -> pd.DataFrame:
    """metadata.csv + split column + slice columns (age_bucket, n_boxes capped at '3+').

    `split_file` is relative to the repo root (as in config `data.split_file`); default data/splits/split_v1.csv.
    """
    meta = pd.read_csv(paths.METADATA, dtype={"patientId": str, "nih_patient": str})
    split_path = paths.ROOT / split_file if split_file else paths.SPLIT_FILE
    split = pd.read_csv(split_path, usecols=["patientId", "split"], dtype=str)
    meta = meta.merge(split, on="patientId", how="left", validate="one_to_one")
    age = meta["age"]
    meta["age_bucket"] = pd.cut(age, AGE_BINS, right=False, labels=AGE_LABELS).astype(object).where(age <= 100, "invalid")
    meta["n_boxes"] = meta["n_boxes"].clip(upper=3).astype(int).astype(str).replace("3", "3+")
    return meta


def run_split_file(run: Path) -> str | None:
    """The split file a trained run used (results/<run>/config.yaml `data.split_file`); None for baselines."""
    cfg_path = run / "config.yaml"
    if not cfg_path.exists():
        return None
    cfg = yaml.safe_load(cfg_path.read_text())
    split_file = (cfg.get("data") or {}).get("split_file")
    if not (paths.ROOT / split_file if split_file else paths.SPLIT_FILE).is_file():
        raise FileNotFoundError(f"{run.name}: split file {split_file} is missing (temporary --smoke split?)")
    return split_file


def provenance(run: Path) -> dict[str, Any]:
    """Identity of the training run behind results/<run> (from meta.json); {} for runs without one (baselines)."""
    meta_path = run / "meta.json"
    if not meta_path.exists():
        return {}
    m = json.loads(meta_path.read_text())
    return {k: m.get(k) for k in ("start", "mlflow_run_id", "git_sha")}


def check_fresh(run: Path, mt: dict[str, Any], what: str) -> None:
    """Refuse metrics/predictions written for an earlier model trained under the same run name."""
    prov = provenance(run)
    if prov and mt.get("train_run") != prov:
        raise ValueError(f"{run.name}: {what} was written for another training run "
                         f"({mt.get('train_run')} != meta.json {prov}); re-run rsna.evaluate")


def split_ids(meta: pd.DataFrame, split: str, limit: int | None = None) -> list[str]:
    ids = meta.loc[meta["split"] == split, "patientId"].tolist()
    return ids[:limit] if limit else ids


def read_preds(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"patientId": str}) if path.exists() else pd.DataFrame(columns=PRED_COLS)


def val_threshold(run: Path) -> float:
    sweep = pd.read_csv(run / "threshold_sweep.csv")
    return float(sweep.loc[sweep["map"].idxmax(), "thr"])


def resolve_threshold(run: Path, threshold: str | float) -> tuple[float, str]:
    if str(threshold) == "from_val":
        return val_threshold(run), "from_val (argmax of results/<run>/threshold_sweep.csv)"
    return float(threshold), "manual"


def _prefix(split: str, limit: int | None) -> str:
    return f"{split}_lim{limit}" if limit else split


def predict_split(run: Path, ids: list[str], meta: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Predict `ids` with runs/<run>/best.pt; images come from the cache of the checkpoint's image_size."""
    from .decode import predict, to_frames
    from .model import load_checkpoint
    from .utils import get_device

    device = get_device()
    model, cfg = load_checkpoint(paths.RUNS / run.name / "best.pt", device)
    pos = meta.set_index("patientId").loc[ids, "idx"].to_numpy()
    images = np.load(paths.image_cache(cfg["data"]["image_size"]), mmap_mode="r")
    order = np.argsort(pos)  # sorted reads from the memmap, then back to `ids` order
    arr = np.empty((len(pos), *images.shape[1:]), np.uint8)
    arr[order] = images[pos[order]]
    dets, img_scores = predict(model, arr, cfg, device, cfg["train"].get("eval_batch_size", 64))
    return to_frames(ids, dets, img_scores)


def write_preds(pred: pd.DataFrame, img: pd.DataFrame, out: Path, prefix: str) -> None:
    """Write the tables (round_preds is idempotent: frames from to_frames / baselines are already rounded)."""
    round_preds(pred).to_csv(out / f"{prefix}_predictions.csv", index=False)
    img.to_csv(out / f"{prefix}_image_scores.csv", index=False, float_format=f"%.{IMAGE_SCORE_DECIMALS}f")


# ----------------------------------------------------------------------------- analysis

def _ci(per_image: pd.Series, n_boot: int, seed: int = 0) -> dict[str, float]:
    m, lo, hi = bootstrap_ci(per_image, n_boot=n_boot, seed=seed)
    return {"map": m, "ci_lo": lo, "ci_hi": hi}


def error_decomposition(per_image: pd.Series, target: pd.Series, has_pred: pd.Series) -> dict[str, Any]:
    """Exact split of the gap 1 - mAP into three additive parts (all over the scored-image count).

    mAP = sum(AP over positives) / (n_pos + n_fp_neg): every negative image with >=1 box adds a 0.
    loss_fp_neg = n_fp_neg / n_scored; loss_missed_pos = positives without any box / n_scored;
    loss_loc_pos = sum(1 - AP) over positives that have boxes / n_scored (wrong place/size, extra/missing boxes).
    """
    pos, neg = target == 1, target == 0
    n_fp = int((neg & has_pred).sum())
    n_pos = int(pos.sum())
    n_scored = n_pos + n_fp
    ap_pos = per_image[pos]
    d = max(n_scored, 1)
    return {
        "n_pos": n_pos, "n_neg": int(neg.sum()), "n_fp_neg_images": n_fp, "n_scored": n_scored,
        "fp_image_rate": n_fp / max(int(neg.sum()), 1),
        "pos_with_boxes_rate": float(has_pred[pos].mean()) if n_pos else float("nan"),
        "map_pos": float(ap_pos.mean()) if n_pos else float("nan"),
        "loss_fp_neg": n_fp / d,
        "loss_missed_pos": int((pos & ~has_pred).sum()) / d,
        "loss_loc_pos": float((1 - ap_pos[has_pred[pos]]).sum()) / d,
    }


def oracle_gating(gt: dict[str, np.ndarray], pred: dict, ids: list[str], target: pd.Series, thr: float) -> dict[str, Any]:
    """Upper bound for a perfect image-level classifier: keep boxes only on GT-positive images.

    Reported at the run's own threshold and at the best threshold of the gated predictions on THIS split
    (an oracle quantity by construction; never use it for model selection).
    """
    pos_ids = set(target.index[target == 1])
    gated = {k: v for k, v in pred.items() if k in pos_ids}
    sweep = threshold_sweep(gt, gated, ids)
    best = sweep.loc[sweep["map"].idxmax()]
    return {"map_at_run_thr": rsna_map(gt, gated, ids, score_threshold=thr),
            "best_thr": float(best["thr"]), "map_at_best_thr": float(best["map"])}


def evaluate_predictions(pred_df: pd.DataFrame, img_df: pd.DataFrame | None, ids: list[str], meta: pd.DataFrame,
                         thr: float, n_boot: int = 2000, slice_boot: int = 500,
                         gt: dict[str, np.ndarray] | None = None) -> tuple[dict[str, Any], pd.Series]:
    """All metrics of one prediction table on the image set `ids` at score threshold `thr`.

    `meta` needs patientId, target and the SLICES columns (see load_meta); `gt` defaults to data/processed/boxes.csv.
    """
    gt = load_gt(paths.BOXES, ids) if gt is None else gt
    pred = preds_from_df(pred_df)
    score, per_image = rsna_map(gt, pred, ids, score_threshold=thr, return_per_image=True)
    m = meta.set_index("patientId").loc[ids]
    target = m["target"]
    has_pred = pd.Series([i in pred and bool((pred[i][1] >= thr).any()) for i in ids], index=ids)  # >=1 box kept
    img_score = (img_df.set_index("patientId")["image_score"].reindex(ids).fillna(0.0)
                 if img_df is not None and len(img_df) else pd.Series(image_scores_from_preds(pred, ids), index=ids))
    image_lvl = image_level_metrics(target.to_numpy(), img_score.to_numpy())
    pos, neg = target == 1, target == 0
    out: dict[str, Any] = {
        "n_images": len(ids), "threshold": thr, **_ci(per_image, n_boot), "n_scored": int(per_image.notna().sum()),
        "image_roc_auc": image_lvl["roc_auc"], "image_pr_auc": image_lvl["pr_auc"],
        "sensitivity": float(has_pred[pos].mean()) if pos.any() else float("nan"),  # image has >=1 box at thr
        "specificity": float((~has_pred[neg]).mean()) if neg.any() else float("nan"),
        "matched_iou": matched_iou(gt, pred, ids, score_threshold=thr),
        "errors": error_decomposition(per_image, target, has_pred),
        "oracle_gating": oracle_gating(gt, pred, ids, target, thr),
        "slices": {},
    }
    assert np.isnan(score) or abs(score - out["map"]) < 1e-12
    for col in SLICES:
        rows = []
        order = SLICE_ORDER.get(col, sorted(m[col].astype(str).unique()))
        for val, g in sorted(m.groupby(col), key=lambda kv: order.index(str(kv[0])) if str(kv[0]) in order else 99):
            sid = g.index
            pi = per_image.loc[sid]
            e = error_decomposition(pi, g["target"], has_pred.loc[sid])
            rows.append({"slice": col, "value": str(val), "n": len(sid), "n_pos": e["n_pos"],
                         **_ci(pi, slice_boot), "n_scored": e["n_scored"], "map_pos": e["map_pos"],
                         "fp_image_rate": e["fp_image_rate"] if e["n_neg"] else float("nan"),
                         "sensitivity": e["pos_with_boxes_rate"]})
        out["slices"][col] = rows
    return out, per_image


# ----------------------------------------------------------------------------- reporting

def _f(x: Any, nd: int = 4) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return f"{x:.{nd}f}" if isinstance(x, float) else str(x)


def to_markdown(mt: dict[str, Any], title: str) -> str:
    e, o = mt["errors"], mt["oracle_gating"]
    lines = [f"### {title}", "",
             f"mAP **{_f(mt['map'])}** [{_f(mt['ci_lo'])}, {_f(mt['ci_hi'])}] (bootstrap 95% CI) at score thr "
             f"{mt['threshold']:.2f}; images {mt['n_images']}, scored {mt['n_scored']}", "",
             "| metric | value |", "|---|---|"]
    for k in ["image_roc_auc", "image_pr_auc", "sensitivity", "specificity", "matched_iou"]:
        lines.append(f"| {k} | {_f(mt[k])} |")
    lines += [f"| mAP on positives only | {_f(e['map_pos'])} |",
              f"| FP-image rate on negatives | {_f(e['fp_image_rate'])} ({e['n_fp_neg_images']}/{e['n_neg']}) |",
              f"| loss: FP on negatives | {_f(e['loss_fp_neg'])} |",
              f"| loss: missed positives (no box) | {_f(e['loss_missed_pos'])} |",
              f"| loss: localization on positives | {_f(e['loss_loc_pos'])} |",
              f"| oracle gating @run thr | {_f(o['map_at_run_thr'])} |",
              f"| oracle gating @best thr ({o['best_thr']:.2f}) | {_f(o['map_at_best_thr'])} |", "",
              "| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |", "|---|---|---|---|---|---|---|---|---|"]
    for rows in mt["slices"].values():
        for r in rows:
            lines.append(f"| {r['slice']} | {r['value']} | {r['n']} | {r['n_pos']} | {_f(r['map'])} | "
                         f"[{_f(r['ci_lo'], 3)}, {_f(r['ci_hi'], 3)}] | {_f(r['map_pos'])} | "
                         f"{_f(r['fp_image_rate'], 3)} | {_f(r['sensitivity'], 3)} |")
    return "\n".join(lines) + "\n"


def _jsonable(x: Any) -> Any:
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_jsonable(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if np.isnan(x) else round(float(x), 6)
    if isinstance(x, np.integer):
        return int(x)
    return x


def write_report(mt: dict[str, Any], out: Path, prefix: str, title: str) -> str:
    md = to_markdown(mt, title)
    (out / f"{prefix}_metrics.json").write_text(json.dumps(_jsonable(mt), indent=2, ensure_ascii=False))
    (out / f"{prefix}_metrics.md").write_text(md)
    return md


# ----------------------------------------------------------------------------- commands

def run_eval(run: Path, split: str, threshold: str | float = "from_val", limit: int | None = None,
             repredict: bool = False, n_boot: int = 2000) -> dict[str, Any]:
    meta = load_meta(run_split_file(run))
    thr, thr_src = resolve_threshold(run, threshold)
    prefix = _prefix(split, limit)
    ckpt = paths.RUNS / run.name / "best.pt"
    if repredict or (split == "test" and ckpt.exists()) or not (run / f"{split}_predictions.csv").exists():
        ids = split_ids(meta, split, limit)
        pred_df, img_df = predict_split(run, ids, meta)
        write_preds(pred_df, img_df, run, prefix)
    else:  # stored val predictions of the best epoch, on the image set they were made for
        img_df = pd.read_csv(run / f"{split}_image_scores.csv", dtype={"patientId": str}).iloc[:limit]
        ids = img_df["patientId"].tolist()
        pred_df = read_preds(run / f"{split}_predictions.csv")
    assert set(meta.set_index("patientId").loc[ids, "split"]) == {split}, f"ids outside split={split}"
    mt, _ = evaluate_predictions(pred_df, img_df, ids, meta, thr, n_boot=n_boot)
    mt = {"run": run.name, "split": split, "threshold_source": thr_src, "limit": limit, "train_run": provenance(run),
          "note": "val threshold chosen on val: selection-biased" if split == "val" else "", **mt}
    md = write_report(mt, run, prefix, f"{run.name} — {split}")
    print(md)
    print(f"-> {run / f'{prefix}_metrics.json'}")
    return mt


def per_image_scores(run: Path, split: str, ids: list[str] | None = None) -> tuple[pd.Series, float, list[str]]:
    if split != "val":  # val tables are written by train itself; other splits by run_eval (with provenance)
        mpath = run / f"{split}_metrics.json"
        check_fresh(run, json.loads(mpath.read_text()) if mpath.exists() else {}, f"{split}_predictions.csv")
    img = pd.read_csv(run / f"{split}_image_scores.csv", dtype={"patientId": str})
    ids = ids if ids is not None else img["patientId"].tolist()
    thr = val_threshold(run)
    gt = load_gt(paths.BOXES, ids)
    _, s = rsna_map(gt, preds_from_df(read_preds(run / f"{split}_predictions.csv")), ids, thr, return_per_image=True)
    return s, thr, ids


def compare(a: Path, b: Path, split: str, n_boot: int = 2000, out_dir: Path | None = None) -> dict[str, Any]:
    """Paired bootstrap of mAP(a) - mAP(b) on the images both runs were evaluated on; each run uses its val threshold."""
    ids_a = pd.read_csv(a / f"{split}_image_scores.csv", dtype={"patientId": str})["patientId"].tolist()
    ids_b = set(pd.read_csv(b / f"{split}_image_scores.csv", dtype={"patientId": str})["patientId"])
    ids = [i for i in ids_a if i in ids_b]
    if not ids:
        raise ValueError("no common images")
    sa, ta, _ = per_image_scores(a, split, ids)
    sb, tb, _ = per_image_scores(b, split, ids)
    res = {"a": a.name, "b": b.name, "split": split, "n_common": len(ids),
           "n_only_a": len(ids_a) - len(ids), "n_only_b": len(ids_b) - len(ids), "thr_a": ta, "thr_b": tb,
           "map_a": float(np.nanmean(sa)), "map_b": float(np.nanmean(sb)),
           **paired_bootstrap_diff(sa, sb, n_boot=n_boot)}
    md = (f"| A | B | split | n | mAP A | mAP B | A−B | 95% CI | P(A−B≤0) |\n|---|---|---|---|---|---|---|---|---|\n"
          f"| {a.name} (thr {ta:.2f}) | {b.name} (thr {tb:.2f}) | {split} | {len(ids)} | {_f(res['map_a'])} | "
          f"{_f(res['map_b'])} | {_f(res['diff'])} | [{_f(res['lo'])}, {_f(res['hi'])}] | {_f(res['p_diff_le_0'], 3)} |\n")
    if res["n_only_a"] or res["n_only_b"]:
        md += f"\nCompared on the {len(ids)} common images only (A-only {res['n_only_a']}, B-only {res['n_only_b']}).\n"
    out_dir = out_dir or paths.RESULTS / "comparisons"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{a.name}__vs__{b.name}__{split}"
    (out_dir / f"{stem}.json").write_text(json.dumps(_jsonable(res), indent=2))
    (out_dir / f"{stem}.md").write_text(md)
    print(md)
    print(f"-> {out_dir / stem}.json")
    return res


def summarize(runs: list[Path], split: str, out: Path | None = None) -> pd.DataFrame:
    """Mean ± std over seeds of the `<split>_metrics.json` written by run_eval."""
    keys = ["map", "ci_lo", "ci_hi", "threshold", "image_roc_auc", "sensitivity", "specificity", "matched_iou"]
    rows = []
    for r in runs:
        mt = json.loads((r / f"{split}_metrics.json").read_text())
        check_fresh(r, mt, f"{split}_metrics.json")
        rows.append({"run": r.name, **{k: mt[k] for k in keys}, "fp_image_rate": mt["errors"]["fp_image_rate"]})
    df = pd.DataFrame(rows)
    num = df.drop(columns="run")
    df = pd.concat([df, pd.DataFrame([{"run": "mean", **num.mean()}, {"run": "std", **num.std(ddof=1)}])])
    md = "\n".join(["| " + " | ".join(df.columns) + " |", "|" + "---|" * df.shape[1]]
                   + ["| " + " | ".join(_f(v) for v in row) + " |" for row in df.itertuples(index=False)])
    print(md)
    if out:
        out.mkdir(parents=True, exist_ok=True)
        df.to_csv(out / f"{split}_summary.csv", index=False, float_format="%.5f")
        (out / f"{split}_summary.md").write_text(md + "\n")
    return df


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv and argv[0] in ("compare", "summarize") else "eval"
    ap = argparse.ArgumentParser(prog=f"python -m rsna.evaluate {'' if cmd == 'eval' else cmd}", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", choices=["val", "test"], required=True)
    ap.add_argument("--n-boot", type=int, default=2000)
    if cmd == "eval":
        ap.add_argument("--run", type=Path, required=True)
        ap.add_argument("--threshold", default="from_val")
        ap.add_argument("--limit", type=int, help="smoke: first N images of the split; writes <split>_lim<N>_* files")
        ap.add_argument("--repredict", action="store_true", help="val: predict the full split from best.pt")
        a = ap.parse_args(argv)
        run_eval(a.run, a.split, a.threshold, a.limit, a.repredict, a.n_boot)
    elif cmd == "compare":
        ap.add_argument("--a", type=Path, required=True)
        ap.add_argument("--b", type=Path, required=True)
        ap.add_argument("--out", type=Path)
        a = ap.parse_args(argv[1:])
        compare(a.a, a.b, a.split, a.n_boot, a.out)
    else:
        ap.add_argument("--runs", type=Path, nargs="+", required=True)
        ap.add_argument("--out", type=Path)
        a = ap.parse_args(argv[1:])
        summarize(a.runs, a.split, a.out)


if __name__ == "__main__":
    main()
