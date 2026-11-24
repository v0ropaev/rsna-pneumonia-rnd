"""HW3 helpers: per-image error tables of a set of seeds, seed-pooled group metrics with cluster-bootstrap CIs,
NIH finding labels, and the example gallery. Used by scripts/analyze_hw3_*.py (val only).

Group metrics are computed per seed and averaged over seeds; a CI resamples NIH patients ONCE per replicate for all
seeds (hw3.combo), so it reflects data noise of the val sample, not seed noise.
  mAP        RSNA mAP inside the group (negatives without a kept box are not scored, exactly as in the metric)
  map_pos    mean AP over the group's positives
  fp_rate    share of the group's negatives with >= 1 kept box
  sens       share of the group's positives with >= 1 kept box
  std_map    prevalence-standardized RSNA mAP: inside a group the metric is exactly
             mAP = n_pos*map_pos / (n_pos + n_neg*fp_rate) (a negative without a kept box is not scored, one with a box
             scores 0), so at a fixed reference share of positives pi (the whole val set's) it becomes
             pi*map_pos / (pi + (1-pi)*fp_rate): what the group's mAP would be if it had the average prevalence.
             Nonlinear, so the bootstrap recomputes it from map_pos and fp_rate in every replicate.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from sklearn.metrics import roc_auc_score

from . import paths
from .analysis import GT_COLOR, PRED_COLOR, SUB_COLOR, load_unit, per_image_table
from .evaluate import load_meta, patient_groups
from .metric import bootstrap_codes, iou_xywh, load_gt, preds_from_df
from .report import INK, INK2

NIH_JSON = paths.EXTERNAL / "pneumonia-challenge-dataset-mappings_2018.json"
PNEUMONIA_LIKE = ("Pneumonia", "Consolidation", "Infiltration")
AGE_GROUPS = [("<30", 0, 30), ("30–60", 30, 60), ("≥60", 60, 101)]
N_BOOT = 2000


# ----------------------------------------------------------------------------- data

def nih_labels(ids: list[str]) -> pd.Series:
    """patientId -> list of the NIH ChestX-ray14 finding labels of the source image (NLP-mined from reports)."""
    if not NIH_JSON.exists():
        raise FileNotFoundError(f"{NIH_JSON} missing: run scripts/download_data.sh (RSNA->NIH mapping)")
    df = pd.DataFrame(json.loads(NIH_JSON.read_text()))[["subset_img_id", "orig_labels"]]
    s = df.set_index("subset_img_id")["orig_labels"]
    missing = set(ids) - set(s.index)
    if missing:
        raise ValueError(f"{len(missing)} ids without NIH labels")
    return s.loc[ids]


def nih_group(labels: list[str]) -> str:
    if labels == ["No Finding"]:
        return "No Finding"
    if any(l in PNEUMONIA_LIKE for l in labels):
        return "pneumonia-like"
    return "other finding"


def age_group(age: pd.Series) -> pd.Series:
    out = pd.Series("invalid", index=age.index, dtype=object)
    for name, lo, hi in AGE_GROUPS:
        out[(age >= lo) & (age < hi)] = name
    return out


def size_cutoffs() -> tuple[float, float]:
    """Tertiles of sqrt(mean GT box area) over TRAIN positives (v1 split): fixed bins, not fit on val."""
    meta = load_meta()
    tr = set(meta.loc[(meta["split"] == "train") & (meta["target"] == 1), "patientId"])
    b = pd.read_csv(paths.BOXES)
    b = b[b["patientId"].isin(tr)]
    side = np.sqrt((b["width"] * b["height"]).groupby(b["patientId"]).mean())
    lo, hi = np.quantile(side, [1 / 3, 2 / 3])
    return float(lo), float(hi)


@dataclass
class Unit:
    run: str
    thr: float
    pred: dict          # patientId -> (boxes [k,4], scores [k]) as scored (box_scale + gating applied)
    img: pd.DataFrame   # val_image_scores (image_score, max_box_score = raw heatmap max, cls_prob)
    ids: list[str]
    tab: pd.DataFrame   # rsna.analysis.per_image_table + extras


def load_units(runs: list[str], variant: str | None = "tuned", split_file_ok: Callable[[Path], bool] | None = None
               ) -> list[Unit]:
    out = []
    for r in runs:
        run = paths.RESULTS / r
        pred_df, img, ids, thr, meta = load_unit(run, variant, "val")
        gt = load_gt(paths.BOXES, ids)
        pred = preds_from_df(pred_df)
        tab = per_image_table(pred, gt, ids, meta, thr)
        tab = add_extras(tab, pred, gt, img, thr)
        out.append(Unit(r, thr, pred, img.set_index("patientId").loc[ids], ids, tab))
    return out


def add_extras(tab: pd.DataFrame, pred: dict, gt: dict, img: pd.DataFrame, thr: float) -> pd.DataFrame:
    """n_gt, has_box, cls_prob, raw heatmap max, IoU of the best sub-threshold box, merged/split boxes."""
    img = img.set_index("patientId") if "patientId" in img.columns else img
    tab = tab.copy()
    tab["n_gt"] = [len(gt.get(i, ())) for i in tab.index]
    tab["has_box"] = tab["n_kept"] > 0
    for c in ("cls_prob", "max_box_score"):
        if c in img.columns:
            tab[c] = img[c].reindex(tab.index).to_numpy()
    sub_iou, merged, split = [], [], []
    for i in tab.index:
        b, s = pred.get(i, (np.zeros((0, 4)), np.zeros(0)))
        g = gt.get(i, np.zeros((0, 4)))
        keep = s >= thr
        if (~keep).any() and len(g):
            j = int(np.argmax(np.where(~keep, s, -1)))
            sub_iou.append(float(iou_xywh(b[j:j + 1], g).max()))
        else:
            sub_iou.append(np.nan)
        if keep.any() and len(g):
            iou = iou_xywh(b[keep], g)  # [kept, gt]
            merged.append(bool(((iou > 0.1).sum(1) >= 2).any()))   # one box overlaps >= 2 GT boxes
            split.append(bool(((iou > 0.1).sum(0) >= 2).any()))    # one GT box overlapped by >= 2 boxes
        else:
            merged.append(False)
            split.append(False)
    tab["sub_iou"], tab["merged"], tab["split_gt"] = sub_iou, merged, split
    return tab


def attach_meta(tab: pd.DataFrame, cut: tuple[float, float]) -> pd.DataFrame:
    """Slice columns: age group, NIH labels / group, GT size tertile (positives), view x cls."""
    meta = load_meta().set_index("patientId").loc[tab.index]
    t = tab.copy()
    t["age"] = meta["age"]
    t["age_group"] = age_group(meta["age"])
    t["nih_patient"] = meta["nih_patient"]
    labs = nih_labels(t.index.tolist())
    t["nih_labels"] = ["|".join(l) for l in labs]
    t["nih_group"] = [nih_group(l) for l in labs]
    b = pd.read_csv(paths.BOXES)
    b = b[b["patientId"].isin(set(t.index))]
    side = np.sqrt((b["width"] * b["height"]).groupby(b["patientId"]).mean())
    t["gt_side"] = side.reindex(t.index)
    t["size"] = np.select([t["gt_side"] < cut[0], t["gt_side"] < cut[1], t["gt_side"].notna()],
                          ["small", "medium", "large"], "–")
    return t


# ----------------------------------------------------------------------------- seed-pooled group metrics

PROPORTIONS = ("fp_rate", "sens")


def _arrays(tabs: list[pd.DataFrame], ids: pd.Index) -> dict[str, list[np.ndarray]]:
    out: dict[str, list[np.ndarray]] = {"ap": [], "pos": [], "has": [], "score": []}
    for t in tabs:
        t = t.loc[ids]
        out["ap"].append(t["ap"].to_numpy(np.float64))
        out["pos"].append(t["target"].to_numpy() == 1)
        out["has"].append(t["has_box"].to_numpy(np.float64))
        sc = t["cls_prob"] if "cls_prob" in t else t["max_score"]
        out["score"].append(sc.to_numpy(np.float64))
    return out


def components(arr: dict[str, list[np.ndarray]], mask: np.ndarray, metric: str, pi: float
               ) -> tuple[list[np.ndarray], Callable[[np.ndarray], np.ndarray]]:
    """(per-image value arrays with NaN = not counted, combine). Every array is reduced to its mean over the counted
    images (sum / count, as the metric itself averages); combine(means [n_comp, ...]) -> the seed-mean metric."""
    S = len(arr["ap"])
    nan = lambda v, m: np.where(m, v, np.nan)
    xs: list[np.ndarray] = []
    for s in range(S):
        ap, pos, has = arr["ap"][s], arr["pos"][s], arr["has"][s]
        if metric == "map":
            xs.append(nan(ap, mask))
        elif metric == "map_pos":
            xs.append(nan(ap, mask & pos))
        elif metric == "fp_rate":
            xs.append(nan(has, mask & ~pos))
        elif metric == "sens":
            xs.append(nan(has, mask & pos))
        elif metric == "std_map":
            xs += [nan(ap, mask & pos), nan(has, mask & ~pos)]
        else:
            raise ValueError(metric)
    if metric == "std_map":
        def combine(v: np.ndarray) -> np.ndarray:
            a, f = v[0::2], v[1::2]
            with np.errstate(invalid="ignore", divide="ignore"):
                return (pi * a / (pi + (1 - pi) * f)).mean(0)
    else:
        def combine(v: np.ndarray) -> np.ndarray:
            return v.mean(0)
    return xs, combine


def _boot_means(xs: list[np.ndarray], codes: np.ndarray, k: int, n_boot: int, seed: int
                ) -> tuple[np.ndarray, np.ndarray]:
    """(point means [m], replicate means [m, n_boot]) of every array; ONE cluster draw per replicate for all arrays."""
    sums = np.stack([np.bincount(codes, np.nan_to_num(x), k) for x in xs])
    cnts = np.stack([np.bincount(codes, (~np.isnan(x)).astype(np.float64), k) for x in xs])
    with np.errstate(invalid="ignore", divide="ignore"):
        point = sums.sum(1) / cnts.sum(1)
    rng = np.random.default_rng(seed)
    reps = []
    step = max(1, 4_000_000 // max(k * len(xs), 1))
    for i in range(0, n_boot, step):
        r = rng.integers(0, k, (min(step, n_boot - i), k))
        with np.errstate(invalid="ignore", divide="ignore"):
            reps.append(sums[:, r].sum(-1) / cnts[:, r].sum(-1))
    return point, np.concatenate(reps, axis=1)


def combo(terms: list[tuple[float, list[pd.DataFrame], np.ndarray, str]], n_boot: int = N_BOOT,
          pi: float | None = None, seed: int = 0) -> dict[str, float]:
    """sum_t coef_t * metric_t(tabs_t on mask_t) with a 95 % cluster-bootstrap CI (NIH patients; one draw per
    replicate shared by every term, seed and table, so differences and DiD are paired). All tables share the image
    order of terms[0]. A proportion with 0 (or all) events everywhere gets an exact one-sided bound instead of the
    degenerate [0, 0] percentile interval: 1 − 0.025^(1/n) with n = number of patients in the mask (conservative)."""
    ids = terms[0][1][0].index
    for _, tabs, _, _ in terms:
        assert all(t.index.equals(ids) for t in tabs), "tables must share the image order"
    codes, k = bootstrap_codes(ids, patient_groups())
    pi = float((terms[0][1][0]["target"] == 1).mean()) if pi is None else pi
    xs, slices, combs = [], [], []
    for _, tabs, mask, metric in terms:
        x, comb = components(_arrays(tabs, ids), np.asarray(mask, bool), metric, pi)
        slices.append(slice(len(xs), len(xs) + len(x)))
        xs += x
        combs.append(comb)
    point, reps = _boot_means(xs, codes, k, n_boot, seed)
    est = sum(c * float(comb(point[sl])) for (c, *_), sl, comb in zip(terms, slices, combs))
    b = sum(c * comb(reps[sl]) for (c, *_), sl, comb in zip(terms, slices, combs))
    out = {"est": float(est), "n": int(np.asarray(terms[0][2], bool).sum())}
    if np.isnan(est):
        return {**out, "lo": np.nan, "hi": np.nan, "p_le_0": np.nan}
    lo, hi = np.nanquantile(b, [0.025, 0.975])
    if len(terms) == 1 and terms[0][3] in PROPORTIONS and lo == hi and est in (0.0, 1.0):
        n_pat = len(set(codes[np.asarray(terms[0][2], bool)]))
        bound = 1 - 0.025 ** (1 / max(n_pat, 1))
        lo, hi = (0.0, bound) if est == 0.0 else (1 - bound, 1.0)
    return {**out, "lo": float(lo), "hi": float(hi), "p_le_0": float(np.nanmean(b <= 0))}


def masked_metric(tabs: list[pd.DataFrame], mask: np.ndarray, metric: str, n_boot: int = N_BOOT,
                  pi: float | None = None, seed: int = 0) -> dict[str, float]:
    """Seed-mean `metric` on the images in `mask` with a 95 % cluster-bootstrap CI."""
    return combo([(1.0, tabs, mask, metric)], n_boot, pi, seed)


def group_diff(tabs: list[pd.DataFrame], mask_a: np.ndarray, mask_b: np.ndarray, metric: str, n_boot: int = N_BOOT,
               pi: float | None = None, seed: int = 0) -> dict[str, float]:
    """metric(A) - metric(B) (seed means) with a 95 % cluster-bootstrap CI (patients resampled jointly)."""
    r = combo([(1.0, tabs, mask_a, metric), (-1.0, tabs, mask_b, metric)], n_boot, pi, seed)
    return {"diff": r["est"], "lo": r["lo"], "hi": r["hi"], "p_le_0": r["p_le_0"]}


def paired_unit_diff(tabs_a: list[pd.DataFrame], tabs_b: list[pd.DataFrame], mask: np.ndarray, metric: str,
                     n_boot: int = N_BOOT, pi: float | None = None, seed: int = 0) -> dict[str, float]:
    """metric of model set A minus model set B on the SAME images (mask), seed means; paired cluster bootstrap."""
    r = combo([(1.0, tabs_a, mask, metric), (-1.0, tabs_b, mask, metric)], n_boot, pi, seed)
    return {"diff": r["est"], "lo": r["lo"], "hi": r["hi"], "p_le_0": r["p_le_0"]}


def group_table(tabs: list[pd.DataFrame], by: str, order: list[str] | None = None, n_boot: int = N_BOOT,
                metrics: tuple[str, ...] = ("map", "map_pos", "fp_rate", "sens", "std_map"), pi: float | None = None,
                seed: int = 0) -> pd.DataFrame:
    """One row per value of column `by` (of tabs[0]): n, n_pos, seed-mean metrics with 95 % cluster-bootstrap CI."""
    t0 = tabs[0]
    pi = float((t0["target"] == 1).mean()) if pi is None else pi
    arr = _arrays(tabs, t0.index)
    vals = [v for v in (order or sorted(t0[by].astype(str).unique())) if (t0[by].astype(str) == v).any()]
    rows = []
    for v in vals:
        mask = (t0[by].astype(str) == v).to_numpy()
        pos = mask & (t0["target"] == 1).to_numpy()
        row: dict[str, Any] = {"slice": by, "value": v, "n": int(mask.sum()), "n_pos": int(pos.sum()),
                               "n_patients": int(t0.loc[mask, "nih_patient"].nunique()) if "nih_patient" in t0 else np.nan,
                               "prev": float(pos.sum() / max(mask.sum(), 1))}
        for m in metrics:
            r = masked_metric(tabs, mask, m, n_boot, pi, seed)
            row[m], row[f"{m}_lo"], row[f"{m}_hi"] = r["est"], r["lo"], r["hi"]
        aucs = []
        for s in range(len(tabs)):
            y, sc = arr["pos"][s][mask], arr["score"][s][mask]
            if 0 < y.sum() < len(y):
                aucs.append(roc_auc_score(y, sc))
        row["auc"] = float(np.mean(aucs)) if aucs else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- formatting

def fmt(x: Any, nd: int = 3) -> str:
    return "–" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{nd}f}"


def ci(row: pd.Series | dict, m: str, nd: int = 3) -> str:
    v = row[m]
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "–"
    return f"{v:.{nd}f} [{row[f'{m}_lo']:.{nd}f}, {row[f'{m}_hi']:.{nd}f}]"


def md_table(header: list[str], rows: list[list[Any]]) -> str:
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
                     + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


# ----------------------------------------------------------------------------- gallery

def gallery(rows: list[tuple[str, list[str]]], unit: Unit, gt: dict, title: str, path: Path, n_per_row: int = 5,
            caption: Callable[[str], str] | None = None, show_sub: bool = False) -> None:
    """Rows of examples on the 384 px cache: GT green, boxes >= thr red (score), best sub-threshold box orange dashed."""
    images = np.load(paths.image_cache(384), mmap_mode="r")
    tab = unit.tab
    fig, axs = plt.subplots(len(rows), n_per_row, figsize=(2.6 * n_per_row, 2.95 * len(rows) + 0.4), squeeze=False)
    k = 384 / paths.ORIG_SIZE
    for r, (name, ids) in enumerate(rows):
        for c in range(n_per_row):
            ax = axs[r, c]
            ax.set_xticks([]), ax.set_yticks([])
            ax.grid(False)
            if c >= len(ids):
                ax.axis("off")
                continue
            i = ids[c]
            t = tab.loc[i]
            ax.imshow(np.asarray(images[int(t["idx"])]), cmap="gray", vmin=0, vmax=255)
            for g in gt.get(i, np.zeros((0, 4))):
                ax.add_patch(Rectangle((g[0] * k, g[1] * k), g[2] * k, g[3] * k, fill=False, ec=GT_COLOR, lw=1.8))
            b, s = unit.pred.get(i, (np.zeros((0, 4)), np.zeros(0)))
            keep = s >= unit.thr
            for bb, ss in zip(b[keep], s[keep]):
                ax.add_patch(Rectangle((bb[0] * k, bb[1] * k), bb[2] * k, bb[3] * k, fill=False, ec=PRED_COLOR, lw=1.5))
                ax.text(bb[0] * k + 2, bb[1] * k + 2, f"{ss:.2f}", color=PRED_COLOR, fontsize=7, va="top",
                        bbox=dict(fc="black", alpha=0.55, pad=0.5, lw=0))
            if show_sub and (~keep).any():
                j = int(np.argmax(np.where(~keep, s, -1)))
                bb = b[j]
                ax.add_patch(Rectangle((bb[0] * k, bb[1] * k), bb[2] * k, bb[3] * k, fill=False, ec=SUB_COLOR, lw=1.3,
                                       ls="--"))
                ax.text(bb[0] * k + 2, (bb[1] + bb[3]) * k - 2, f"{s[j]:.2f}", color=SUB_COLOR, fontsize=7,
                        bbox=dict(fc="black", alpha=0.55, pad=0.5, lw=0))
            ax.set_title(caption(i) if caption else i[:8], fontsize=6.6, color=INK)
        axs[r, 0].set_ylabel(name, fontsize=8.5, color=INK)
    fig.suptitle(title, fontsize=9.5, color=INK)
    fig.text(0.5, 0.005, f"GT green · boxes with score ≥ thr {unit.thr:.2f} red" + (" · best box below thr orange dashed"
                                                                                  if show_sub else ""),
             ha="center", fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    fig.savefig(path, dpi=115)
    plt.close(fig)


# ----------------------------------------------------------------------------- inference on modified inputs

def val_images(ids: list[str], size: int = 256) -> np.ndarray:
    """uint8 [N, S, S] model-input images of `ids` (metadata order -> ids order)."""
    meta = load_meta().set_index("patientId")
    pos = meta.loc[ids, "idx"].to_numpy()
    cache = np.load(paths.image_cache(size), mmap_mode="r")
    order = np.argsort(pos)
    arr = np.empty((len(pos), *cache.shape[1:]), np.uint8)
    arr[order] = cache[pos[order]]
    return arr


class Predictor:
    """runs/<run>/best.pt on a device; predict(images) -> (RAW table, image table) as rsna.decode writes them."""

    def __init__(self, run: str, device=None) -> None:
        from .model import load_checkpoint
        from .utils import get_device

        self.device = device or get_device()
        self.model, self.cfg = load_checkpoint(paths.RUNS / run / "best.pt", self.device)
        self.run = run

    def predict(self, images: np.ndarray, ids: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
        from .decode import predict_frames

        _, img_df, raw_df = predict_frames(self.model, images, ids, self.cfg, self.device,
                                           self.cfg["train"].get("eval_batch_size", 64))
        return raw_df, img_df


def variant_spec(run: str, variant: str = "tuned") -> dict[str, Any]:
    """box_scale, score_mode and the VAL threshold of a post-hoc variant (as selected in HW2)."""
    from .evaluate import val_threshold

    d = paths.RESULTS / run / "posthoc" / variant
    v = json.loads((d / "variant.json").read_text())
    return {"box_scale": float(v["box_scale"]), "score_mode": v["score_mode"], "thr": val_threshold(d)}


def score_condition(raw_df: pd.DataFrame, img_df: pd.DataFrame, spec: dict[str, Any], gt: dict, ids: list[str],
                    target: np.ndarray) -> dict[str, Any]:
    """Metrics of one prediction set at the variant's FIXED val threshold and at the best threshold of THIS set."""
    from .metric import rsna_map, threshold_sweep
    from .posthoc import apply_posthoc

    pred_df = apply_posthoc(raw_df, img_df, spec["box_scale"], spec["score_mode"])
    pred = preds_from_df(pred_df)
    m, per = rsna_map(gt, pred, ids, score_threshold=spec["thr"], return_per_image=True)
    has = np.array([i in pred and bool((pred[i][1] >= spec["thr"]).any()) for i in ids])
    sw = threshold_sweep(gt, pred, ids)
    b = sw.loc[sw["map"].idxmax()]
    cls = img_df.set_index("patientId")["image_score"].reindex(ids).to_numpy()
    pos = target == 1
    return {"map": float(m), "map_best": float(b["map"]), "thr_best": float(b["thr"]),
            "auc": float(roc_auc_score(target, cls)), "fp_rate": float(has[~pos].mean()), "sens": float(has[pos].mean()),
            "ap": per.reindex(ids).to_numpy(np.float64), "has_box": has, "score": cls}


def condition_table(res: dict[str, Any], ids: list[str], target: np.ndarray) -> pd.DataFrame:
    """Minimal per-image table for the seed-pooled bootstrap helpers (group_table / paired_unit_diff)."""
    return pd.DataFrame({"ap": res["ap"], "target": target, "has_box": res["has_box"], "cls_prob": res["score"]},
                        index=pd.Index(ids, name="patientId"))


def localization_counterfactuals(unit: Unit, gt: dict) -> dict[str, float]:
    """mAP gains on the positives with >= 1 kept box if
      no_far        kept boxes that touch no GT box (max IoU <= 0.1) were removed,
      no_dup        kept boxes that touch a GT box but were not matched (greedy by score, IoU > 0.1: a GT box already
                    taken by a higher-scored box, i.e. duplicates) were removed,
      exact_extent  every matched box had exactly its GT box's extent (score and order unchanged),
      all           the three together.
    Gains are sum(ΔAP) / scored images (the metric's denominator), so they are on the scale of the localization loss.
    Also: images with a far box, number of duplicate boxes, GT boxes that no kept box touches (max IoU <= 0.1)."""
    from .analysis import greedy_pairs
    from .metric import image_precision

    t = unit.tab
    n_scored = int(((t["target"] == 1) | t["has_box"]).sum())
    gains = {"no_far": 0.0, "no_dup": 0.0, "exact_extent": 0.0, "all": 0.0}
    n_far_img = n_dup = n_untouched_gt = 0
    for i in t.index[(t["target"] == 1) & t["has_box"]]:
        b, s = unit.pred[i]
        keep = s >= unit.thr
        b, s = b[keep], s[keep]
        g = gt[i]
        iou = iou_xywh(b, g)
        far = iou.max(1) <= 0.1
        pairs = greedy_pairs(b, s, g, 0.1)
        matched = np.zeros(len(b), bool)
        matched[[p for p, _, _ in pairs]] = True
        dup = ~far & ~matched
        n_far_img += int(far.any())
        n_dup += int(dup.sum())
        n_untouched_gt += int((iou.max(0) <= 0.1).sum())
        exact = b.copy()
        for p, j, _ in pairs:
            exact[p] = g[j]
        ap0 = image_precision(g, b, s) or 0.0
        cf = {"no_far": (b[~far], s[~far]), "no_dup": (b[~dup], s[~dup]), "exact_extent": (exact, s),
              "all": (exact[matched], s[matched])}
        for k, (bb, ss) in cf.items():
            ap = image_precision(g, bb, ss) if len(bb) else 0.0
            gains[k] += (ap or 0.0) - ap0
    out = {k: v / n_scored for k, v in gains.items()}
    out.update({"n_images_with_far_box": n_far_img, "n_duplicate_boxes": n_dup, "n_gt_untouched": n_untouched_gt})
    return out
