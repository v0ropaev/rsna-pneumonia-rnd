"""Error analysis of one run (or post-hoc variant) on one split, for the HW1/HW2 READMEs.

CLI: python -m rsna.analysis --run results/<run> [--split val|test] [--variant NAME] [--out reports/figures/<prefix>]
                             [--threshold from_val|<float>] [--n-per-row 6]
--run may be any path (e.g. a run of another checkout, read only); outputs go to --out (default
reports/figures/<run>[_<variant>]_<split>). --variant NAME reads results/<run>/posthoc/NAME/ (rsna.posthoc layout).
Only the given split's images / labels are read; test only with an explicit --split test. The score threshold is
the VAL one (argmax of the unit's threshold_sweep.csv) unless --threshold is a number.

Outputs (<prefix>_*): summary.md (error decomposition, per-slice table with each slice's share of the total gap,
box-size statistics, offline box_scale sweep [val only], calibration), fp_negatives.png, missed.png,
localization.png, good.png (galleries on the 384 px cache: GT green, kept predictions red with score, best
sub-threshold box orange dashed), scores.png, box_sizes.png, calibration.png.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

from . import paths
from .evaluate import SLICE_ORDER, SLICES, error_decomposition, load_meta, read_preds, run_split_file
from .metric import image_level_metrics, iou_xywh, load_gt, preds_from_df, rsna_map, threshold_sweep
from .report import INK, INK2, SLOTS, SURFACE, style

CLS_NAMES = ["Normal", "No Lung Opacity / Not Normal", "Lung Opacity"]
CLS_SHORT = {"Normal": "Normal", "No Lung Opacity / Not Normal": "Not Normal", "Lung Opacity": "Opacity"}
GT_COLOR, PRED_COLOR, SUB_COLOR = "#00b300", "#ff3b3b", "#ffa31a"  # on dark x-ray pixels
SCALES = np.round(np.r_[np.arange(0.70, 1.101, 0.05), 0.875], 3)
MATCH_IOU = 0.1  # loose matching for box-size statistics (a strict 0.4 would hide boxes that are much too large)


# ----------------------------------------------------------------------------- loading

def unit_dir(run: Path, variant: str | None) -> Path:
    if not variant:
        return run
    p = Path(variant)
    return p if p.is_dir() and (p / "variant.json").exists() else run / "posthoc" / variant


def load_unit(run: Path, variant: str | None, split: str, threshold: str | float = "from_val"
              ) -> tuple[pd.DataFrame, pd.DataFrame, list[str], float, pd.DataFrame]:
    """(pred table, image table, image ids, score threshold, split metadata indexed by patientId)."""
    d = unit_dir(run, variant)
    img = pd.read_csv(d / f"{split}_image_scores.csv", dtype={"patientId": str})
    ids = img["patientId"].tolist()
    pred = read_preds(d / f"{split}_predictions.csv")
    meta = load_meta(run_split_file(run))
    meta = meta[meta["split"] == split].set_index("patientId")  # never look at other splits
    if not set(ids) <= set(meta.index):
        raise ValueError(f"{d}: {split}_image_scores.csv has ids outside split={split}")
    if str(threshold) == "from_val":
        sweep_path = d / "threshold_sweep.csv"
        if not sweep_path.exists():
            raise FileNotFoundError(f"{sweep_path} missing (the VAL sweep); pass --threshold <float>")
        sw = pd.read_csv(sweep_path)
        thr = float(sw.loc[sw["map"].idxmax(), "thr"])
    else:
        thr = float(threshold)
    return pred, img, ids, thr, meta.loc[ids]


# ----------------------------------------------------------------------------- per-image table

def greedy_pairs(pred_boxes: np.ndarray, scores: np.ndarray, gt: np.ndarray, min_iou: float = MATCH_IOU
                 ) -> list[tuple[int, int, float]]:
    """Greedy by confidence: each prediction takes the free GT with the highest IoU if > min_iou -> (p, g, iou)."""
    if len(pred_boxes) == 0 or len(gt) == 0:
        return []
    order = np.argsort(-scores, kind="stable")
    iou = iou_xywh(pred_boxes[order], gt)
    free = np.ones(len(gt), bool)
    out = []
    for k, p in enumerate(order):
        cand = np.where(free, iou[k], -1.0)
        j = int(cand.argmax())
        if cand[j] > min_iou:
            free[j] = False
            out.append((int(p), j, float(cand[j])))
    return out


def per_image_table(pred: dict[str, tuple[np.ndarray, np.ndarray]], gt: dict[str, np.ndarray], ids: list[str],
                    meta: pd.DataFrame, thr: float) -> pd.DataFrame:
    """One row per image: AP at thr, kept boxes, best IoU, scores, GT size and an error category.

    category: tn (negative, no kept box) | fp_neg (negative with >=1 kept box) | missed (positive, no kept box)
              | loc_zero (positive with kept boxes, AP = 0) | partial (0 < AP < 1) | perfect (AP = 1).
    """
    _, ap = rsna_map(gt, pred, ids, score_threshold=thr, return_per_image=True)
    rows = []
    for i in ids:
        b, s = pred.get(i, (np.zeros((0, 4)), np.zeros(0)))
        keep = s >= thr
        g = gt.get(i, np.zeros((0, 4)))
        best_iou = float(iou_xywh(b[keep], g).max()) if keep.any() and len(g) else 0.0
        rows.append({"patientId": i, "n_kept": int(keep.sum()), "max_score": float(s.max()) if len(s) else 0.0,
                     "max_kept": float(s[keep].max()) if keep.any() else 0.0,
                     "max_sub": float(s[~keep].max()) if (~keep).any() else 0.0,
                     "best_iou": best_iou, "gt_area": float((g[:, 2] * g[:, 3]).sum()) if len(g) else 0.0})
    df = pd.DataFrame(rows).set_index("patientId")
    df["ap"] = ap
    df = df.join(meta[[c for c in ["target", "cls", "view", "sex", "age_bucket", "n_boxes", "idx"] if c in meta]])
    pos, has = df["target"] == 1, df["n_kept"] > 0
    cat = np.select([~pos & ~has, ~pos & has, pos & ~has, pos & (df["ap"] == 0), pos & (df["ap"] < 1)],
                    ["tn", "fp_neg", "missed", "loc_zero", "partial"], "perfect")
    df["category"] = cat
    return df


# ----------------------------------------------------------------------------- tables

def decomposition(df: pd.DataFrame) -> dict[str, Any]:
    """evaluate.error_decomposition + the localization loss split into AP=0 vs partial images."""
    e = error_decomposition(df["ap"], df["target"], df["n_kept"] > 0)
    d = max(e["n_scored"], 1)
    pos = df["target"] == 1
    e["map"] = float(df["ap"].mean()) if df["ap"].notna().any() else float("nan")
    e["loss_loc_zero"] = float((1 - df.loc[pos & (df["category"] == "loc_zero"), "ap"]).sum()) / d
    e["loss_loc_partial"] = float((1 - df.loc[pos & df["category"].isin(["partial", "perfect"]), "ap"]).sum()) / d
    e["counts"] = df["category"].value_counts().to_dict()
    return e


def decomposition_md(e: dict[str, Any]) -> str:
    gap = 1 - e["map"]
    c = e["counts"]
    rows = [("FP на негативах (≥1 бокс на снимке без GT)", c.get("fp_neg", 0), e["loss_fp_neg"]),
            ("пропущенные позитивы (ни одного бокса)", c.get("missed", 0), e["loss_missed_pos"]),
            ("локализация: боксы есть, AP = 0", c.get("loc_zero", 0), e["loss_loc_zero"]),
            ("локализация: 0 < AP < 1 (неточные/лишние/недостающие боксы)", c.get("partial", 0), e["loss_loc_partial"])]
    lines = [f"mAP {e['map']:.4f} на {e['n_scored']} учитываемых снимках (позитивов {e['n_pos']}, негативов "
             f"{e['n_neg']}, из них с FP {e['n_fp_neg_images']}); разрыв 1 − mAP = {gap:.4f}:", "",
             "| источник потерь | снимков | потеря mAP | доля разрыва |", "|---|---|---|---|"]
    lines += [f"| {n} | {k} | {v:.4f} | {v / gap:.1%} |" if gap > 0 else f"| {n} | {k} | {v:.4f} | – |"
              for n, k, v in rows]
    lines.append(f"| сумма (= 1 − mAP) | | {sum(v for *_, v in rows):.4f} | |")
    loc = e["loss_loc_zero"] + e["loss_loc_partial"]
    lines += ["", f"Локализация всего (AP = 0 + 0 < AP < 1): {loc:.4f}"
              + (f" = {loc / gap:.1%} разрыва." if gap > 0 else ".")]
    return "\n".join(lines)


def slice_table(df: pd.DataFrame) -> pd.DataFrame:
    """Per slice value: mAP, mAP on positives, FP-image rate, sensitivity and the share of the TOTAL gap.

    gap_points = (FP-negative images + missed positives + sum(1 - AP) over positives with boxes) / total n_scored,
    so for every slice column the values add up to the overall 1 - mAP.
    """
    n_scored_total = max(int(((df["target"] == 1) | (df["n_kept"] > 0)).sum()), 1)
    rows = []
    for col in SLICES:
        if col not in df:
            continue
        order = SLICE_ORDER.get(col, sorted(df[col].astype(str).unique()))
        for val, g in sorted(df.groupby(df[col].astype(str)), key=lambda kv: order.index(kv[0]) if kv[0] in order else 99):
            e = error_decomposition(g["ap"], g["target"], g["n_kept"] > 0)
            pos = g["target"] == 1
            lost = e["n_fp_neg_images"] + float((1 - g.loc[pos, "ap"]).sum())
            rows.append({"slice": col, "value": val, "n": len(g), "n_pos": e["n_pos"],
                         "map": float(g["ap"].mean()) if g["ap"].notna().any() else np.nan, "map_pos": e["map_pos"],
                         "fp_image_rate": e["fp_image_rate"] if e["n_neg"] else np.nan,
                         "sensitivity": e["pos_with_boxes_rate"], "gap_points": lost / n_scored_total})
    return pd.DataFrame(rows)


def _f(x: Any, nd: int = 4) -> str:
    return "–" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{nd}f}"


def slice_md(t: pd.DataFrame, gap: float) -> str:
    lines = ["| slice | value | n | n_pos | mAP | mAP pos | FP-img rate | sens | потеря mAP | доля разрыва |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    lines += [f"| {r.slice} | {r.value} | {r.n} | {r.n_pos} | {_f(r.map)} | {_f(r.map_pos)} | {_f(r.fp_image_rate, 3)} "
              f"| {_f(r.sensitivity, 3)} | {r.gap_points:.4f} | {r.gap_points / gap:.1%} |" for r in t.itertuples()]
    return "\n".join(lines)


# ----------------------------------------------------------------------------- box sizes & box_scale

def box_pairs(pred: dict, gt: dict, ids: list[str], thr: float, min_iou: float = MATCH_IOU) -> pd.DataFrame:
    rows = []
    for i in ids:
        g = gt.get(i, np.zeros((0, 4)))
        if not len(g) or i not in pred:
            continue
        b, s = pred[i]
        keep = s >= thr
        b, s = b[keep], s[keep]
        for p, j, iou in greedy_pairs(b, s, g, min_iou):
            rows.append({"patientId": i, "score": s[p], "iou": iou, "pw": b[p, 2], "ph": b[p, 3], "gw": g[j, 2],
                         "gh": g[j, 3]})
    df = pd.DataFrame(rows, columns=["patientId", "score", "iou", "pw", "ph", "gw", "gh"])
    df["rw"], df["rh"] = df["pw"] / df["gw"], df["ph"] / df["gh"]
    df["r_side"] = np.sqrt(df["rw"] * df["rh"])  # sqrt of the area ratio
    return df


def size_stats(pairs: pd.DataFrame) -> dict[str, Any]:
    out = {"n_pairs": len(pairs)}
    for name, sub in (("iou>0.1", pairs), ("iou>0.4", pairs[pairs["iou"] > 0.4])):
        out[name] = {"n": len(sub), **{f"median_{k}": float(sub[k].median()) if len(sub) else np.nan
                                       for k in ("rw", "rh", "r_side")},
                     "frac_larger": float((sub["r_side"] > 1).mean()) if len(sub) else np.nan}
    return out


def scale_boxes(pred: dict, s: float) -> dict:
    """box_scale on stored (already clipped) boxes, identical to rsna.decode / rsna.posthoc up to 0.1 px rounding."""
    out = {}
    for i, (b, sc) in pred.items():
        ctr = b[:, :2] + b[:, 2:] / 2
        lo = np.clip(ctr - b[:, 2:] * s / 2, 0, paths.ORIG_SIZE)
        hi = np.clip(ctr + b[:, 2:] * s / 2, 0, paths.ORIG_SIZE)
        out[i] = (np.c_[lo, hi - lo], sc)
    return out


def scale_sweep(pred: dict, gt: dict, ids: list[str], thr: float, scales: np.ndarray = SCALES) -> pd.DataFrame:
    rows = []
    for s in sorted(scales):
        p = pred if s == 1.0 else scale_boxes(pred, s)
        sw = threshold_sweep(gt, p, ids)
        b = sw.loc[sw["map"].idxmax()]
        rows.append({"box_scale": s, "map_at_thr": rsna_map(gt, p, ids, score_threshold=thr),
                     "best_thr": float(b["thr"]), "map_best_thr": float(b["map"])})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- calibration

def calibration(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> tuple[pd.DataFrame, float, float]:
    """Equal-width reliability bins: (table, ECE, Brier). Meaningful as probability only for a cls head."""
    bins = np.clip((p * n_bins).astype(int), 0, n_bins - 1)
    t = pd.DataFrame({"bin": bins, "p": p, "y": y}).groupby("bin").agg(n=("y", "size"), mean_p=("p", "mean"),
                                                                     frac_pos=("y", "mean")).reset_index()
    ece = float((t["n"] / len(p) * (t["mean_p"] - t["frac_pos"]).abs()).sum())
    return t, ece, float(np.mean((p - y) ** 2))


# ----------------------------------------------------------------------------- figures

def _tile(ax, img: np.ndarray, gt: np.ndarray, boxes: np.ndarray, scores: np.ndarray, thr: float, title: str,
          show_sub: bool = False) -> None:
    k = img.shape[0] / paths.ORIG_SIZE
    ax.imshow(img, cmap="gray", vmin=0, vmax=255)
    for g in gt:
        ax.add_patch(Rectangle((g[0] * k, g[1] * k), g[2] * k, g[3] * k, fill=False, ec=GT_COLOR, lw=1.6))
    keep = scores >= thr
    for b, s in zip(boxes[keep], scores[keep]):
        ax.add_patch(Rectangle((b[0] * k, b[1] * k), b[2] * k, b[3] * k, fill=False, ec=PRED_COLOR, lw=1.4))
        ax.text(b[0] * k + 2, b[1] * k + 2, f"{s:.3f}", color=PRED_COLOR, fontsize=6.5, va="top",
                bbox=dict(fc="black", alpha=0.5, pad=0.5, lw=0))
    if show_sub and (~keep).any():
        j = int(np.argmax(np.where(~keep, scores, -1)))
        b = boxes[j]
        ax.add_patch(Rectangle((b[0] * k, b[1] * k), b[2] * k, b[3] * k, fill=False, ec=SUB_COLOR, lw=1.2, ls="--"))
        ax.text(b[0] * k + 2, (b[1] + b[3]) * k - 2, f"{scores[j]:.3f}", color=SUB_COLOR, fontsize=6.5,
                bbox=dict(fc="black", alpha=0.5, pad=0.5, lw=0))
    ax.set_title(title, fontsize=7, color=INK)
    ax.set_xticks([]), ax.set_yticks([])
    ax.grid(False)


def gallery(rows: list[tuple[str, list[str]]], tab: pd.DataFrame, pred: dict, gt: dict, images: np.ndarray,
            thr: float, title: str, path: Path, n_per_row: int, show_sub: bool = False) -> None:
    rows = [(n, ids[:n_per_row]) for n, ids in rows]
    fig, axs = plt.subplots(len(rows), n_per_row, figsize=(2.15 * n_per_row, 2.35 * len(rows) + 0.5), squeeze=False)
    for r, (name, ids) in enumerate(rows):
        for c in range(n_per_row):
            ax = axs[r, c]
            if c >= len(ids):
                ax.axis("off")
                continue
            i = ids[c]
            t = tab.loc[i]
            b, s = pred.get(i, (np.zeros((0, 4)), np.zeros(0)))
            ap = "–" if np.isnan(t["ap"]) else f"{t['ap']:.2f}"
            _tile(ax, np.asarray(images[int(t["idx"])]), gt.get(i, np.zeros((0, 4))), b, s, thr,
                  f"{i[:8]} {CLS_SHORT.get(t['cls'], t['cls'])} {t['view']}\nAP {ap} max {t['max_score']:.3f}", show_sub)
        axs[r, 0].set_ylabel(name, fontsize=8, color=INK)
        if not ids:
            axs[r, 0].text(0.5, 0.5, f"{name}: нет снимков", transform=axs[r, 0].transAxes, ha="center")
    fig.suptitle(f"{title}   (GT green, prediction ≥ thr {thr:.2f} red" + (", best sub-thr orange dashed)" if show_sub
                                                                          else ")"), fontsize=9, color=INK)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def _hist(ax, values: dict[str, np.ndarray], colors: list[str], bins: np.ndarray, ls: list[str] | None = None) -> None:
    for k, ((name, v), col) in enumerate(zip(values.items(), colors)):
        if len(v):
            ax.hist(v, bins=bins, weights=np.full(len(v), 1 / len(v)), histtype="step", lw=1.8, color=col,
                    ls=(ls or ["-"] * 9)[k], label=f"{name} (n={len(v)})")
    ax.set_ylim(3e-4, 1.5)


def fig_scores(tab: pd.DataFrame, img: pd.DataFrame, thr: float, path: Path) -> None:
    has_cls = "cls_prob" in img.columns
    fig, axs = plt.subplots(1, 3 if has_cls else 2, figsize=(14 if has_cls else 10, 3.6))
    bins = np.linspace(0, 1, 41)
    for a in axs:
        a.set_yscale("log")
    _hist(axs[0], {CLS_SHORT[c]: tab.loc[tab["cls"] == c, "max_score"].to_numpy() for c in CLS_NAMES}, SLOTS[:3], bins)
    axs[0].set(title="Max box score per image by class", xlabel="max stored box score (0 if none)",
               ylabel="fraction of images (log)")
    vt = {f"{v} {'pos' if t else 'neg'}": tab.loc[(tab["view"] == v) & (tab["target"] == t), "max_score"].to_numpy()
          for v in ("AP", "PA") for t in (1, 0)}
    _hist(axs[1], vt, [SLOTS[0], SLOTS[0], SLOTS[1], SLOTS[1]], bins, ls=["-", "--", "-", "--"])
    axs[1].set(title="Max box score by view (solid = positive, dashed = negative)", xlabel="max stored box score")
    for a in axs[:2]:
        a.axvline(thr, color=INK, lw=1, ls=":")
        a.text(thr + 0.01, 0.97, f"thr {thr:.2f}", transform=a.get_xaxis_transform(), fontsize=7, va="top")
    if has_cls:
        cp = img.set_index("patientId")["cls_prob"].reindex(tab.index)
        _hist(axs[2], {CLS_SHORT[c]: cp[tab["cls"] == c].to_numpy() for c in CLS_NAMES}, SLOTS[:3], bins)
        axs[2].set(title="cls-head probability by class", xlabel="sigmoid(cls)")
    for a in axs:
        a.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def fig_box_sizes(pairs: pd.DataFrame, sweep: pd.DataFrame | None, thr: float, path: Path) -> None:
    n = 3 if sweep is not None else 2
    fig, axs = plt.subplots(1, n, figsize=(4.6 * n, 4))
    lim = float(np.nanmax(pairs[["pw", "ph", "gw", "gh"]].to_numpy())) * 1.05 if len(pairs) else 1024
    axs[0].scatter(pairs["gw"], pairs["pw"], s=7, alpha=0.45, color=SLOTS[0], label="width", lw=0)
    axs[0].scatter(pairs["gh"], pairs["ph"], s=7, alpha=0.45, color=SLOTS[1], label="height", lw=0)
    axs[0].plot([0, lim], [0, lim], color=INK, lw=1)
    axs[0].set(xlim=(0, lim), ylim=(0, lim), xlabel="GT size, px (1024 grid)", ylabel="predicted size, px",
               title=f"Matched pairs (greedy, IoU > {MATCH_IOU}), n={len(pairs)}")
    axs[0].legend(fontsize=8)
    bins = np.linspace(-1.5, 1.5, 49)
    lr = np.log2(pairs["r_side"].clip(lower=1e-3))
    axs[1].hist(lr, bins=bins, color=SLOTS[0], alpha=0.85, label=f"IoU > {MATCH_IOU}")
    axs[1].hist(lr[pairs["iou"] > 0.4], bins=bins, histtype="step", lw=1.8, color=INK, label="IoU > 0.4")
    axs[1].axvline(0, color=INK2, lw=1)
    if len(pairs):
        med = float(np.median(pairs["r_side"]))
        axs[1].axvline(np.log2(med), color=SLOTS[1], lw=2, ls="--")
        axs[1].text(np.log2(med) + 0.03, 0.97, f"median ×{med:.3f}", transform=axs[1].get_xaxis_transform(),
                    fontsize=8, va="top")
    axs[1].set(xlabel="log2 sqrt(pred area / GT area)  (> 0: predicted box larger)", ylabel="pairs",
               title="Size ratio of matched pairs")
    axs[1].legend(fontsize=8)
    if sweep is not None:
        axs[2].plot(sweep["box_scale"], sweep["map_best_thr"], marker="o", ms=4, color=SLOTS[0], label="best thr per scale")
        axs[2].plot(sweep["box_scale"], sweep["map_at_thr"], marker="s", ms=4, color=SLOTS[1], label=f"fixed thr {thr:.2f}")
        axs[2].axvline(1.0, color=INK2, lw=1, ls="--")
        axs[2].set(xlabel="box_scale (offline, on stored boxes)", ylabel="RSNA mAP",
                   title="Offline box_scale sweep (this split; selection-biased)")
        axs[2].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def fig_calibration(t: pd.DataFrame, ece: float, brier: float, auc: float, what: str, path: Path) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.8), gridspec_kw={"width_ratios": [1.2, 1]})
    axs[0].plot([0, 1], [0, 1], color=INK2, lw=1, ls="--")
    axs[0].plot(t["mean_p"], t["frac_pos"], marker="o", color=SLOTS[0])
    for r in t.itertuples():
        axs[0].annotate(str(r.n), (r.mean_p, r.frac_pos), xytext=(4, -9), textcoords="offset points", fontsize=6.5,
                        color=INK2)
    axs[0].set(xlim=(0, 1), ylim=(0, 1), xlabel=f"mean {what} in bin", ylabel="fraction of positive images",
               title=f"Reliability: ECE {ece:.3f}, Brier {brier:.3f}, ROC-AUC {auc:.3f}")
    axs[1].bar(t["mean_p"], t["n"], width=0.08, color=SLOTS[0])
    axs[1].set(xlim=(0, 1), yscale="log", ylim=(0.8, max(t["n"].max() * 1.5, 2)), xlabel=what, ylabel="images", title="Images per bin (n annotated left)")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


# ----------------------------------------------------------------------------- main

def analyze(run: Path, split: str = "val", variant: str | None = None, out: Path | None = None,
            threshold: str | float = "from_val", n_per_row: int = 6) -> dict[str, Any]:
    run = run.resolve()
    pred_df, img, ids, thr, meta = load_unit(run, variant, split, threshold)
    out = out or paths.FIGURES / f"{run.name}{'_' + Path(variant).name if variant else ''}_{split}"
    out.parent.mkdir(parents=True, exist_ok=True)
    gt = load_gt(paths.BOXES, ids)  # labels of this split's images only
    pred = preds_from_df(pred_df)
    tab = per_image_table(pred, gt, ids, meta, thr)
    dec = decomposition(tab)
    slices = slice_table(tab)
    gap = 1 - dec["map"]
    assert abs(slices.groupby("slice")["gap_points"].sum() - gap).max() < 1e-9, "slice gaps must add up to 1 - mAP"

    pairs = box_pairs(pred, gt, ids, thr)
    sizes = size_stats(pairs)
    sweep = scale_sweep(pred, gt, ids, thr) if split == "val" else None
    score = img.set_index("patientId")["image_score"].reindex(ids).fillna(0).to_numpy()
    y = tab["target"].to_numpy()
    il = image_level_metrics(y, score)
    cal, ece, brier = calibration(y, np.clip(score, 0, 1))
    has_cls = "cls_prob" in img.columns

    style()
    files = {k: Path(f"{out}_{k}.png") for k in ("fp_negatives", "missed", "localization", "good", "scores",
                                                  "box_sizes", "calibration")}
    images = np.load(paths.image_cache(384), mmap_mode="r")
    by = lambda m, col, asc=False: tab[m].sort_values(col, ascending=asc, kind="stable").index.tolist()
    fp = tab["category"] == "fp_neg"
    gallery([(f"FP: {CLS_SHORT[c]}", by(fp & (tab["cls"] == c), "max_kept")) for c in CLS_NAMES[:2]], tab, pred, gt,
            images, thr, f"{run.name} {split}: highest-confidence FP on negative images", files["fp_negatives"], n_per_row)
    miss = by(tab["category"] == "missed", "gt_area")
    gallery([("missed: largest GT", miss[:n_per_row]), ("missed: next", miss[n_per_row:])], tab, pred, gt, images, thr,
            f"{run.name} {split}: positives without any box ≥ thr, by GT area", files["missed"], n_per_row, show_sub=True)
    loc = tab[(tab["category"] == "loc_zero") & (tab["best_iou"] > 0)].sort_values("max_kept", ascending=False).index.tolist()
    gallery([("overlap ≤ 0.4", loc[:n_per_row]), ("overlap ≤ 0.4", loc[n_per_row:])], tab, pred, gt, images, thr,
            f"{run.name} {split}: boxes overlap GT but IoU ≤ 0.4 (AP = 0), by score", files["localization"], n_per_row)
    good = tab[tab["target"] == 1].sort_values(["ap", "max_kept"], ascending=False).index.tolist()
    gallery([("best AP", good[:n_per_row]), ("best AP", good[n_per_row:])], tab, pred, gt, images, thr,
            f"{run.name} {split}: best cases", files["good"], n_per_row)
    fig_scores(tab, img, thr, files["scores"])
    fig_box_sizes(pairs, sweep, thr, files["box_sizes"])
    fig_calibration(cal, ece, brier, il["roc_auc"], "cls probability" if has_cls else "image score (max heatmap)",
                    files["calibration"])

    s04 = sizes["iou>0.4"]
    s01 = sizes["iou>0.1"]
    name = run.name + (f" / {Path(variant).name}" if variant else "")
    md = [f"## Анализ ошибок: {name}, {split}", "",
          f"Порог score {thr:.2f} ({'из VAL-свипа' if str(threshold) == 'from_val' else 'задан вручную'}); "
          f"снимков {len(ids)}. Image-level по image_score прогона ({'cls prob' if has_cls else 'max heatmap'}): "
          f"ROC-AUC {il['roc_auc']:.3f}, PR-AUC {il['pr_auc']:.3f}.", "",
          "### Декомпозиция ошибки", "", decomposition_md(dec), "",
          "### Срезы (доля разрыва: вклад среза в общий 1 − mAP; внутри каждого среза сумма = 100 %)", "",
          slice_md(slices, gap), "",
          "### Размеры боксов (гипотеза I3: размер боксов смещён; исходно — «велики»)", "",
          f"Пары предсказание–GT (жадно по score, IoU > {MATCH_IOU}): {s01['n']}; медиана pred/GT: ширина "
          f"×{s01['median_rw']:.3f}, высота ×{s01['median_rh']:.3f}, сторона (√площади) ×{s01['median_r_side']:.3f}; "
          f"предсказание больше GT в {s01['frac_larger']:.0%} пар. Только IoU > 0.4: n={s04['n']}, сторона "
          f"×{_f(s04['median_r_side'], 3)}, больше в {_f(s04['frac_larger'] * 100 if s04['n'] else np.nan, 0)} % пар."]
    if sweep is not None:
        b = sweep.loc[sweep["map_best_thr"].idxmax()]
        one = sweep.loc[sweep["box_scale"] == 1.0].iloc[0]
        md += ["", f"Офлайн-свип box_scale на этом же split (смещённая оценка, только диагностика): лучший "
                   f"×{b['box_scale']:.3f} → mAP {b['map_best_thr']:.4f} (thr {b['best_thr']:.2f}) против "
                   f"{one['map_best_thr']:.4f} при ×1.0.", "",
               "| box_scale | mAP @thr " + f"{thr:.2f}" + " | best thr | mAP @best thr |", "|---|---|---|---|"]
        md += [f"| {r.box_scale:.3f} | {r.map_at_thr:.4f} | {r.best_thr:.2f} | {r.map_best_thr:.4f} |"
               for r in sweep.itertuples()]
    md += ["", "### Калибровка image score", "",
           f"Score: {'вероятность cls-головы' if has_cls else 'max heatmap (не вероятность по построению)'}; "
           f"ECE {ece:.3f} (10 равных бинов), Brier {brier:.3f}."
           + (" Это image_score прогона: post-hoc вариант его не меняет (у no_gating он тот же, что у Full)."
              if variant else ""), "", "### Файлы", "",
           *(f"- `{p}`" for p in files.values()), f"- `{out}_summary.md`", ""]
    text = "\n".join(md)
    Path(f"{out}_summary.md").write_text(text)
    print(text)
    return {"threshold": thr, "decomposition": dec, "slices": slices, "sizes": sizes, "box_scale_sweep": sweep,
            "calibration": {"ece": ece, "brier": brier, **il}, "files": files, "table": tab}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--split", choices=["val", "test"], default="val")
    ap.add_argument("--variant", help="post-hoc variant name (results/<run>/posthoc/<name>) or its directory")
    ap.add_argument("--out", type=Path, help="output prefix, e.g. reports/figures/hw1_baseline_s0")
    ap.add_argument("--threshold", default="from_val")
    ap.add_argument("--n-per-row", type=int, default=6)
    a = ap.parse_args(argv)
    analyze(a.run, a.split, a.variant, a.out, a.threshold, a.n_per_row)


if __name__ == "__main__":
    main()
