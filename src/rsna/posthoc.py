"""Post-hoc decode variants as exact offline transforms of stored prediction tables (no re-inference).

apply_posthoc(pred_df, img_df, box_scale, score_mode) re-scores boxes from `raw_score` (`score` for tables
without it, i.e. models without a cls head) and scales w,h around the box center with the same clipping as
rsna.decode; applied to a RAW table it reproduces the online decode table for the same settings exactly.

CLI (VAL only; TEST is touched solely by `rsna.evaluate --split test [--variant <name>]`):
  python -m rsna.posthoc tune --run results/<run> [--grid 0.80:1.30:0.025] [--score-mode keep|heatmap|heatmap_x_cls]
      for each box_scale: threshold sweep on val, best (thr, mAP); pick the max val mAP, tie -> closer to 1.0.
      The grid is two-sided (I3 is tested in both directions); a selection on the grid edge is flagged.
      box_scale.json also holds a 2-fold cross-fitted gain (select (box_scale, thr) on one random patient-disjoint
      half of the val images, score the other half against box_scale 1.0 at its own half-selected thr): an estimate of the I3 effect
      that is not inflated by the selection, unlike val_map - val_map_box_scale_1 (>= 0 by construction).
      -> results/<run>/posthoc/box_scale_tuning.csv, box_scale.json, box_scale.png
         (suffix _<mode> when --score-mode differs from the run's configured decode.score_mode)
  python -m rsna.posthoc variant --run results/<run> --name <name> --box-scale <float|tuned> --score-mode <mode>
      -> results/<run>/posthoc/<name>/variant.json, val_predictions.csv, val_image_scores.csv, threshold_sweep.csv,
         val_metrics.json/.md (same metrics as rsna.evaluate). `compare`/`summarize` address it as results/<run>:<name>.
      Re-defining an existing variant deletes its test_* files and the comparisons that involve it (they belong to
      the old definition; re-run `rsna.evaluate --split test --variant <name>` / `compare`).
`keep` = the run's configured score_mode (the `score` column as stored).
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .metric import BOX_COLS, PRED_DECIMALS, round_preds
from .paths import ORIG_SIZE

RAW_COL = "raw_score"
SCORE_MODES = ("keep", "heatmap", "heatmap_x_cls")
DEFAULT_GRID = "0.80:1.30:0.025"  # two-sided: I3 ("boxes are too large") may fail either way
NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def apply_posthoc(pred_df: pd.DataFrame, img_df: pd.DataFrame | None, box_scale: float = 1.0,
                  score_mode: str = "keep", min_score: float = 0.01, round_output: bool = True) -> pd.DataFrame:
    """Offline box_scale + score_mode on a prediction table (pure; row order kept).

    raw := `raw_score` (or `score` for tables without it). score_mode: keep (score as stored), heatmap (raw),
    heatmap_x_cls (raw * img_df.cls_prob). Rows with raw < min_score are dropped (a no-op on decode tables,
    whose min_score filter is on the raw score as well). box_scale scales w,h around the center and clips to
    [0, ORIG_SIZE] exactly as rsna.decode; box_scale == 1.0 leaves the boxes untouched.
    """
    if score_mode not in SCORE_MODES:
        raise ValueError(f"unknown score_mode {score_mode!r}, expected one of {SCORE_MODES}")
    if not box_scale > 0:
        raise ValueError(f"box_scale must be > 0, got {box_scale}")
    df = pred_df.reset_index(drop=True).copy()
    has_raw = RAW_COL in df.columns
    has_cls = img_df is not None and "cls_prob" in img_df.columns
    if score_mode != "keep" and has_cls and not has_raw:
        raise ValueError("table has cls_prob but no raw_score: its `score` may be gated, cannot re-score")
    raw = df[RAW_COL] if has_raw else df["score"]
    if score_mode == "heatmap":
        df["score"] = raw
    elif score_mode == "heatmap_x_cls":
        if not has_cls:
            raise ValueError("score_mode heatmap_x_cls needs img_df.cls_prob (a model with cls_head)")
        cls = df["patientId"].map(img_df.set_index("patientId")["cls_prob"])
        if cls.isna().any():
            raise ValueError(f"{int(cls.isna().sum())} boxes of images without cls_prob")
        df["score"] = raw * cls
    df = df[(raw >= min_score).to_numpy()].copy()
    if box_scale != 1.0:
        xy, wh = df[BOX_COLS[:2]].to_numpy(np.float64), df[BOX_COLS[2:]].to_numpy(np.float64)
        ctr = xy + wh / 2
        lo = np.clip(ctr - wh * box_scale / 2, 0, ORIG_SIZE)
        hi = np.clip(ctr + wh * box_scale / 2, 0, ORIG_SIZE)
        df[BOX_COLS] = np.c_[lo, hi - lo]
    df = df[["patientId", "score", *BOX_COLS] + ([RAW_COL] if has_raw else [])].reset_index(drop=True)
    if round_output:
        df = round_preds(df)
        if has_raw:
            df[RAW_COL] = df[RAW_COL].round(PRED_DECIMALS["score"])
    return df


# ----------------------------------------------------------------------------- run helpers

def run_config(run: Path) -> dict[str, Any]:
    import yaml

    p = run / "config.yaml"
    return (yaml.safe_load(p.read_text()) or {}) if p.exists() else {}


def configured_mode(run: Path) -> str:
    cfg = run_config(run)
    return (cfg.get("decode") or {}).get("score_mode", "heatmap") if cfg else "keep"


def resolve_mode(run: Path, score_mode: str) -> str:
    if score_mode not in SCORE_MODES:
        raise ValueError(f"unknown score_mode {score_mode!r}")
    return configured_mode(run) if score_mode == "keep" else score_mode


def stored_mode(run: Path, score_mode: str) -> str:
    """Mode to apply to the run's STORED (configured) table: `keep` when it already has `score_mode` scores."""
    return "keep" if score_mode == configured_mode(run) else score_mode


def main_settings(run: Path) -> tuple[float, str]:
    """(box_scale, score_mode) of the run's own decode config ("keep" for runs without a config)."""
    d = run_config(run).get("decode") or {}
    return float(d.get("box_scale", 1.0)), resolve_mode(run, "keep")


def check_source(run: Path, pred_df: pd.DataFrame, score_mode: str, raw_table: bool = False) -> None:
    """A table can be re-transformed only if its boxes are unscaled and its raw score is recoverable."""
    cfg = run_config(run)
    if not raw_table and float((cfg.get("decode") or {}).get("box_scale", 1.0)) != 1.0:
        raise ValueError(f"{run.name}: stored tables use decode.box_scale != 1.0; post-hoc needs unscaled boxes")
    if (cfg.get("model") or {}).get("cls_head") and RAW_COL not in pred_df.columns and score_mode != configured_mode(run):
        raise ValueError(f"{run.name}: cls-head table without raw_score (written before raw scores were stored); "
                         f"score_mode {score_mode} cannot be recovered offline")


def posthoc_dir(run: Path) -> Path:
    return run / "posthoc"


def variant_dir(run: Path, name: str) -> Path:
    if not NAME_RE.match(name):
        raise ValueError(f"variant name {name!r} must match {NAME_RE.pattern}")
    return posthoc_dir(run) / name


def read_variant(run: Path, name: str) -> dict[str, Any]:
    p = variant_dir(run, name) / "variant.json"
    if not p.exists():
        raise FileNotFoundError(f"{p} missing: create it with `python -m rsna.posthoc variant --run {run} --name {name} ...`")
    return json.loads(p.read_text())


def tuning_stem(run: Path, score_mode: str) -> str:
    """box_scale for the run's configured score_mode, box_scale_<mode> otherwise."""
    return "box_scale" if score_mode == configured_mode(run) else f"box_scale_{score_mode}"


def parse_grid(spec: str) -> np.ndarray:
    """'lo:hi:step' (inclusive) -> sorted grid; 1.0 (no scaling) is always a candidate."""
    lo, hi, step = (float(v) for v in spec.split(":"))
    if not (0 < lo <= hi and step > 0):
        raise ValueError(f"bad grid {spec!r}")
    g = np.round(np.arange(lo, hi + step / 2, step), 6)
    return np.unique(np.r_[g, 1.0])


def load_val(run: Path) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """The run's stored VAL tables (best epoch) and the image set they cover."""
    from .evaluate import read_preds

    img = pd.read_csv(run / "val_image_scores.csv", dtype={"patientId": str})
    return read_preds(run / "val_predictions.csv"), img, img["patientId"].tolist()


def select_box_scale(table: pd.DataFrame) -> pd.Series:
    """Max val mAP; ties (within 1e-12) -> box_scale closest to 1.0, then the smaller one."""
    best = table["map"].max()
    cand = table[table["map"] >= best - 1e-12]
    return cand.loc[(cand["box_scale"] - 1.0).abs().sort_values(kind="stable").index[0]]


def val_halves(ids: list[str], seed: int = 0, groups: pd.Series | None = None) -> list[list[str]]:
    """Two disjoint random halves of the val image set (fixed seed) for the cross-fitted box_scale estimate.

    With `groups` (image id -> NIH patient) the halves split patients, not images, so no patient is on both sides.
    """
    rng = np.random.default_rng(seed)
    if groups is None:
        perm = rng.permutation(len(ids))
        return [[ids[k] for k in sorted(perm[: len(ids) // 2])], [ids[k] for k in sorted(perm[len(ids) // 2:])]]
    g = groups.reindex(ids)
    g = g.fillna(pd.Series(ids, index=g.index)).to_numpy()
    uniq = pd.unique(g)
    first = set(uniq[rng.permutation(len(uniq))[: len(uniq) // 2]])
    return [[i for i, gi in zip(ids, g) if gi in first], [i for i, gi in zip(ids, g) if gi not in first]]


def crossfit_gain(half_sweeps: dict[float, list[pd.DataFrame]]) -> dict[str, Any]:
    """2-fold cross-fit: select (box_scale, thr) on half a (as tune does), score half b; baseline = box_scale 1.0
    at its own half-a threshold. Returns the mean held-out gain over both directions + per-fold details."""
    folds = []
    for a, b in ((0, 1), (1, 0)):
        tab = pd.DataFrame([{"box_scale": s, "thr": float(sw[a].loc[sw[a]["map"].idxmax(), "thr"]),
                             "map": float(sw[a]["map"].max())} for s, sw in half_sweeps.items()])
        sel = select_box_scale(tab)
        thr1 = float(tab.loc[tab["box_scale"] == 1.0, "thr"].item())
        held = lambda s, t: float(half_sweeps[s][b].loc[np.isclose(half_sweeps[s][b]["thr"], t), "map"].item())
        folds.append({"select_on": a, "box_scale": float(sel["box_scale"]), "thr": float(sel["thr"]),
                      "heldout_map": held(float(sel["box_scale"]), float(sel["thr"])), "heldout_map_box_scale_1": held(1.0, thr1)})
    gains = [f["heldout_map"] - f["heldout_map_box_scale_1"] for f in folds]
    return {"crossfit_gain": float(np.mean(gains)), "crossfit_folds": folds}


# ----------------------------------------------------------------------------- commands

def tune(run: Path, grid: str = DEFAULT_GRID, score_mode: str = "keep") -> dict[str, Any]:
    from . import paths
    from .evaluate import _jsonable, patient_groups, provenance
    from .metric import load_gt, preds_from_df, threshold_sweep

    mode = resolve_mode(run, score_mode)
    pred, img, ids = load_val(run)
    check_source(run, pred, mode)
    gt = load_gt(paths.BOXES, ids)
    rows, sweeps, half_sweeps = [], {}, {}
    halves = val_halves(ids, groups=patient_groups())  # patient-disjoint halves
    grid_vals = parse_grid(grid)
    for s in grid_vals:
        p = preds_from_df(apply_posthoc(pred, img, float(s), stored_mode(run, mode)))
        sweep = threshold_sweep(gt, p, ids)
        b = sweep.loc[sweep["map"].idxmax()]
        sweeps[float(s)] = sweep
        half_sweeps[float(s)] = [threshold_sweep(gt, p, h) for h in halves]
        rows.append({"box_scale": float(s), "thr": float(b["thr"]), "map": float(b["map"]), "n_scored": int(b["n_scored"])})
    table = pd.DataFrame(rows)
    base_thr = float(table.loc[table["box_scale"] == 1.0, "thr"].item())
    table["map_at_base_thr"] = [float(sweeps[s].loc[np.isclose(sweeps[s]["thr"], base_thr), "map"].item())
                                for s in table["box_scale"]]
    sel = select_box_scale(table)
    base = table.loc[table["box_scale"] == 1.0].iloc[0]
    edge = float(sel["box_scale"]) in (float(grid_vals.min()), float(grid_vals.max()))  # optimum may lie outside
    out = posthoc_dir(run)
    out.mkdir(parents=True, exist_ok=True)
    stem = tuning_stem(run, mode)
    table.to_csv(out / f"{stem}_tuning.csv", index=False, float_format="%.5f")
    res = {"run": run.name, "split": "val", "score_mode": mode, "grid": grid, "n_images": len(ids),
           "box_scale": float(sel["box_scale"]), "thr": float(sel["thr"]), "val_map": float(sel["map"]),
           "val_map_box_scale_1": float(base["map"]), "thr_box_scale_1": float(base["thr"]),
           "selection": "argmax val mAP over box_scale (each at its own best val threshold); tie -> closest to 1.0",
           "at_grid_edge": edge, **crossfit_gain(half_sweeps),
           "note": "selected on val: val_map - val_map_box_scale_1 is >= 0 by construction; crossfit_gain (select on "
                   "one val half, score the other) is the selection-free val estimate of the box_scale effect",
           "train_run": provenance(run), "created": datetime.now().isoformat(timespec="seconds")}
    (out / f"{stem}.json").write_text(json.dumps(_jsonable(res), indent=2, ensure_ascii=False))
    plot_tuning(table, res, out / f"{stem}.png")
    print(table.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print(f"-> box_scale {res['box_scale']} (thr {res['thr']:.2f}, val mAP {res['val_map']:.4f} vs "
          f"{res['val_map_box_scale_1']:.4f} at 1.0); cross-fitted gain {res['crossfit_gain']:+.4f} -> {out / stem}.json")
    if edge:
        print(f"WARNING: selected box_scale {res['box_scale']} is on the grid edge ({grid}): widen --grid")
    return res


def plot_tuning(table: pd.DataFrame, res: dict[str, Any], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ink, muted, blue = "#0b0b0b", "#52514e", "#2a78d6"
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    ax.plot(table["box_scale"], table["map"], color=blue, lw=2, marker="o", ms=5)
    ax.plot([res["box_scale"]], [res["val_map"]], ls="none", marker="o", ms=10, mfc="none", mec=ink, mew=1.5)
    ax.axvline(1.0, color=muted, lw=1, ls="--")
    ax.set(xlabel="box_scale (w, h around center)", ylabel="val RSNA mAP (best thr per scale)",
           title=f"{res['run']} — box_scale on val ({res['score_mode']})\n"
                 f"selected {res['box_scale']:.3f}: {res['val_map']:.4f} @ thr {res['thr']:.2f}  "
                 f"(1.0: {res['val_map_box_scale_1']:.4f} @ thr {res['thr_box_scale_1']:.2f})")
    ax.title.set_fontsize(10)
    ax.grid(alpha=0.25, lw=0.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def make_variant(run: Path, name: str, box_scale: str | float, score_mode: str, n_boot: int = 2000) -> dict[str, Any]:
    """Define a post-hoc variant on VAL (box_scale fixed or tuned on val; threshold = argmax of its val sweep)."""
    from . import paths
    from .evaluate import _jsonable, provenance, run_variant
    from .metric import load_gt, preds_from_df, threshold_sweep

    mode = resolve_mode(run, score_mode)
    if str(box_scale) == "tuned":
        tpath = posthoc_dir(run) / f"{tuning_stem(run, mode)}.json"
        if not tpath.exists():
            raise FileNotFoundError(f"{tpath} missing: run `python -m rsna.posthoc tune --run {run} --score-mode {mode}`")
        tuned = json.loads(tpath.read_text())
        if tuned["score_mode"] != mode or tuned.get("train_run") != provenance(run):
            raise ValueError(f"{tpath} was tuned for another score_mode / training run; re-run tune")
        bs, src = float(tuned["box_scale"]), f"tuned on val ({tpath.name})"
    else:
        bs, src = float(box_scale), "manual"
    pred, img, ids = load_val(run)
    check_source(run, pred, mode)
    df = apply_posthoc(pred, img, bs, stored_mode(run, mode))
    sweep = threshold_sweep(load_gt(paths.BOXES, ids), preds_from_df(df), ids)
    vdir = variant_dir(run, name)
    vdir.mkdir(parents=True, exist_ok=True)
    drop_stale(run, name)
    sweep.to_csv(vdir / "threshold_sweep.csv", index=False, float_format="%.5f")
    spec = {"run": run.name, "name": name, "box_scale": bs, "box_scale_source": src, "score_mode": mode,
            "val_thr": float(sweep.loc[sweep["map"].idxmax(), "thr"]), "source": "val_predictions.csv (best epoch)",
            "train_run": provenance(run), "created": datetime.now().isoformat(timespec="seconds")}
    (vdir / "variant.json").write_text(json.dumps(_jsonable(spec), indent=2, ensure_ascii=False))
    return run_variant(run, name, "val", n_boot=n_boot)


def drop_stale(run: Path, name: str) -> list[Path]:
    """Delete artifacts of an earlier definition of variant `name`: its test_* files (made with the old box_scale /
    threshold) and <results>/comparisons/* (next to the run dir, where rsna.evaluate compare writes) that involve
    run:name. Their freshness check only covers the training run, not the variant definition."""
    vdir, tag, cdir = variant_dir(run, name), f"{run.name}@{name}", run.parent / "comparisons"
    stale = [p for p in vdir.glob("test*") if p.is_file()]
    if cdir.is_dir():
        stale += [p for p in cdir.iterdir() if p.is_file() and (p.name.startswith(tag + "__") or f"__vs__{tag}__" in p.name)]
    for p in stale:
        p.unlink()
        print(f"[posthoc] removed stale {p} (variant {name} re-defined)")
    return stale


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m rsna.posthoc", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tune", help="tune box_scale on val")
    t.add_argument("--run", type=Path, required=True)
    t.add_argument("--grid", default=DEFAULT_GRID)
    t.add_argument("--score-mode", default="keep", choices=SCORE_MODES)
    v = sub.add_parser("variant", help="define + evaluate a post-hoc variant on val")
    v.add_argument("--run", type=Path, required=True)
    v.add_argument("--name", required=True)
    v.add_argument("--box-scale", default="1.0", help="float or 'tuned'")
    v.add_argument("--score-mode", default="keep", choices=SCORE_MODES)
    v.add_argument("--split", default="val", choices=["val"], help="variants are defined on val only")
    v.add_argument("--n-boot", type=int, default=2000)
    a = ap.parse_args(argv)
    if a.cmd == "tune":
        tune(a.run, a.grid, a.score_mode)
    else:
        make_variant(a.run, a.name, a.box_scale, a.score_mode, a.n_boot)


if __name__ == "__main__":
    main()
