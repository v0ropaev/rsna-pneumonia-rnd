"""RSNA Pneumonia Detection metric: the single source of truth for the score.

Definition (Kaggle evaluation page, verbatim copy of the page in [2]; the page itself [1]
is rendered by JavaScript and could not be fetched directly):

* IoU thresholds t in (0.40, 0.45, ..., 0.75). "At a threshold of 0.5, a predicted object
  is considered a 'hit' if its intersection over union with a ground truth object is
  *greater than* 0.5" -> strict ``iou > t``.
* Per threshold: precision_t = TP / (TP + FP + FN). Image score = mean over the 8 thresholds.
  Final score = mean of image scores over the evaluated images.
* "Bounding boxes will be evaluated in order of their confidence levels ... boxes with higher
  confidence will be checked first for matches", so matching is greedy over predictions
  sorted by confidence (descending).
* "If there are no ground truth objects at all for a given image, ANY number of predictions
  (false positives) will result in the image receiving a score of zero, and being included
  in the mean average precision."

Rules that the official text leaves open, and the choices made here:

* Empty GT AND empty predictions: TP+FP+FN = 0, so precision is undefined. The note above
  ("... *and being included*") implies such images are otherwise NOT included, and the
  widely used community reference kernel [3] returns ``None`` for them. Here they are
  EXCLUDED from the mean (``image_precision`` -> None, per-image value NaN). This interpretation
  has not been confirmed by a host statement that we could access.
* Matching: each prediction (by descending confidence) takes the still-unmatched GT box with
  the highest IoU, if that IoU > t; otherwise it is a FP. Ties: equal scores keep input order
  (stable sort), equal IoUs pick the lowest GT index. Note that [3] differs: it loops over GT
  first, uses ``>=`` and takes the first (not the best) unmatched prediction; we follow the
  official text instead. Greedy-by-confidence is not an optimal assignment, so ordering
  can change the score (see tests).
* IoU uses continuous xywh boxes (area = w * h, no +1 pixel convention), as in [3].
* Floating point: IoU and thresholds are plain float64; an IoU that is mathematically equal
  to t and computed exactly (e.g. 50/100 vs 0.5) is NOT a hit.

[1] https://www.kaggle.com/competitions/rsna-pneumonia-detection-challenge/overview/evaluation
[2] https://github.com/mlnn/kaggle-top11perc-rsna-pneumonia-detection-challenge (README)
[3] https://www.kaggle.com/code/chenyc15/mean-average-precision-metric (``map_iou``)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

IOU_THRESHOLDS: np.ndarray = np.round(np.arange(0.40, 0.751, 0.05), 2)
SCORE_THRESHOLDS: np.ndarray = np.round(np.arange(0.05, 0.96, 0.05), 2)
BOX_COLS = ["x", "y", "width", "height"]

Boxes = np.ndarray
Preds = dict[str, tuple[np.ndarray, np.ndarray]]


def _boxes(a: np.ndarray) -> np.ndarray:
    return np.asarray(a, dtype=np.float64).reshape(-1, 4)


def iou_xywh(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Pairwise IoU of xywh boxes, shape [len(a), len(b)]."""
    a, b = _boxes(a), _boxes(b)
    ax1, ay1, ax2, ay2 = a[:, 0:1], a[:, 1:2], a[:, 0:1] + a[:, 2:3], a[:, 1:2] + a[:, 3:4]
    bx1, by1, bx2, by2 = b[:, 0], b[:, 1], b[:, 0] + b[:, 2], b[:, 1] + b[:, 3]
    iw = np.clip(np.minimum(ax2, bx2) - np.maximum(ax1, bx1), 0.0, None)
    ih = np.clip(np.minimum(ay2, by2) - np.maximum(ay1, by1), 0.0, None)
    inter = iw * ih
    union = (a[:, 2] * a[:, 3])[:, None] + (b[:, 2] * b[:, 3])[None, :] - inter
    return np.divide(inter, union, out=np.zeros_like(inter), where=union > 0)


def _greedy(iou: np.ndarray, thresholds: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Greedy matching of predictions (rows, already in confidence order) to GT (columns).

    Vectorized over IoU thresholds. Returns (hit [P, T] bool, matched IoU [P, T], 0 if no hit).
    """
    n_pred, n_gt = iou.shape
    n_t = len(thresholds)
    hit = np.zeros((n_pred, n_t), dtype=bool)
    miou = np.zeros((n_pred, n_t))
    if n_pred == 0 or n_gt == 0:
        return hit, miou
    free = np.ones((n_t, n_gt), dtype=bool)
    rows = np.arange(n_t)
    for p in range(n_pred):
        cand = np.where(free, iou[p][None, :], -1.0)
        j = cand.argmax(axis=1)
        best = cand[rows, j]
        h = best > thresholds
        hit[p], miou[p] = h, np.where(h, best, 0.0)
        free[rows[h], j[h]] = False
    return hit, miou


def _prefix_scores(n_gt: int, hit: np.ndarray) -> np.ndarray:
    """Image score when only the top-k predictions are kept, k = 0..P (NaN == excluded).

    Greedy matching is sequential, so matching the top-k predictions is exactly the first
    k steps of matching all of them: one pass gives the score for every score threshold.
    """
    n_pred, n_t = hit.shape
    tp = np.zeros((n_pred + 1, n_t))
    tp[1:] = np.cumsum(hit, axis=0)
    denom = np.arange(n_pred + 1)[:, None] + n_gt - tp  # TP + FP + FN
    prec = np.divide(tp, denom, out=np.full_like(tp, np.nan), where=denom > 0)
    return prec.mean(axis=1)


def _sorted_case(gt: np.ndarray, boxes: np.ndarray, scores: np.ndarray,
                 thresholds: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Sorted scores (desc) and prefix scores [P+1] for one image."""
    gt, boxes = _boxes(gt), _boxes(boxes)
    scores = np.asarray(scores, dtype=np.float64).reshape(-1)
    if len(scores) != len(boxes):
        raise ValueError(f"{len(boxes)} boxes but {len(scores)} scores")
    order = np.argsort(-scores, kind="stable")
    hit, _ = _greedy(iou_xywh(boxes[order], gt), thresholds)
    return scores[order], _prefix_scores(len(gt), hit)


def image_precision(gt: np.ndarray, pred: np.ndarray, scores: np.ndarray,
                    thresholds: np.ndarray = IOU_THRESHOLDS) -> float | None:
    """Kaggle per-image score; None when the image has neither GT nor predictions (excluded)."""
    _, prefix = _sorted_case(gt, pred, scores, np.asarray(thresholds, dtype=np.float64))
    return None if np.isnan(prefix[-1]) else float(prefix[-1])


def _check_ids(image_ids: list[str]) -> list[str]:
    image_ids = list(image_ids)
    if len(set(image_ids)) != len(image_ids):
        raise ValueError("image_ids contains duplicates")
    return image_ids


_NO_BOXES = np.zeros((0, 4))
_NO_SCORES = np.zeros(0)


def _get(gt: dict[str, np.ndarray], pred: Preds, iid: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    boxes, scores = pred.get(iid, (_NO_BOXES, _NO_SCORES))
    return gt.get(iid, _NO_BOXES), _boxes(boxes), np.asarray(scores, dtype=np.float64).reshape(-1)


def _nanmean(x: np.ndarray) -> float:
    x = x[~np.isnan(x)]
    return float(x.mean()) if len(x) else float("nan")


def rsna_map(gt: dict[str, np.ndarray], pred: Preds, image_ids: list[str],
             score_threshold: float = 0.0, return_per_image: bool = False):
    """Kaggle mAP over ``image_ids`` keeping predictions with score >= score_threshold.

    Images missing from ``pred`` have no predictions; images missing from ``gt`` have no GT.
    Returns the mean (NaN if every image is excluded), or (mean, per-image Series with NaN
    for excluded images, indexed by patientId) when ``return_per_image``.
    """
    image_ids = _check_ids(image_ids)
    vals = np.empty(len(image_ids))
    for i, iid in enumerate(image_ids):
        g, b, s = _get(gt, pred, iid)
        keep = s >= score_threshold
        ap = image_precision(g, b[keep], s[keep])
        vals[i] = np.nan if ap is None else ap
    score = _nanmean(vals)
    if return_per_image:
        return score, pd.Series(vals, index=pd.Index(image_ids, name="patientId"), name="ap")
    return score


def threshold_sweep(gt: dict[str, np.ndarray], pred: Preds, image_ids: list[str],
                    thresholds: np.ndarray = SCORE_THRESHOLDS) -> pd.DataFrame:
    """mAP for each score threshold (keep score >= thr). Columns: thr, map, n_scored.

    Matching runs once per image; every threshold only selects a prefix of the sorted list.
    """
    image_ids = _check_ids(image_ids)
    thr = np.asarray(thresholds, dtype=np.float64).reshape(-1)
    cases = [_sorted_case(*_get(gt, pred, iid), IOU_THRESHOLDS) for iid in image_ids]
    n_max = max((len(s) for s, _ in cases), default=0)
    s_pad = np.full((len(cases), n_max), -np.inf)
    c_pad = np.full((len(cases), n_max + 1), np.nan)
    for i, (s, c) in enumerate(cases):
        s_pad[i, : len(s)], c_pad[i, : len(c)] = s, c
    k = (s_pad[None, :, :] >= thr[:, None, None]).sum(axis=2)  # [T, N] kept predictions
    vals = c_pad[np.arange(len(cases))[None, :], k]  # [T, N]
    n_scored = (~np.isnan(vals)).sum(axis=1)
    maps = [_nanmean(v) for v in vals]
    return pd.DataFrame({"thr": thr, "map": maps, "n_scored": n_scored})


def bootstrap_codes(index: pd.Index, groups: pd.Series | None) -> tuple[np.ndarray, int]:
    """Resampling unit per image: codes 0..k-1 (image i belongs to cluster codes[i]) and k.

    groups=None: every image is its own unit (plain image bootstrap). Otherwise `groups` maps image id ->
    cluster label (here: NIH patient, because images of one patient are correlated and the split is grouped
    by it); every image in `index` must have a label.
    """
    if groups is None:
        return np.arange(len(index)), len(index)
    g = groups.reindex(index)
    if g.isna().any():
        raise ValueError(f"{int(g.isna().sum())} of {len(index)} images have no bootstrap group")
    codes, uniq = pd.factorize(g, sort=False)
    return codes.astype(np.int64), len(uniq)


def bootstrap_ratio_replicates(terms: list[tuple[float, np.ndarray]], codes: np.ndarray, k: int,
                               n_boot: int, seed: int = 0) -> np.ndarray:
    """Replicates of sum_t coef_t * nanmean(x_t) under a (cluster) bootstrap.

    terms: (coef, per-image values with NaN = excluded image), all aligned with `codes`. Each replicate draws
    k clusters with replacement, ONE draw shared by all terms (pairing), and computes every term as
    sum(values) / sum(scored indicator) over the drawn clusters: exactly how the metric averages, with the
    scored-image denominator varying across replicates. Replicates with an empty denominator are NaN.
    With one cluster per image this is the plain image bootstrap (identical draws for the same seed).
    """
    sums = []
    for c, x in terms:
        ok = ~np.isnan(x)
        sums.append((c, np.bincount(codes, np.where(ok, x, 0.0), k), np.bincount(codes, ok.astype(np.float64), k)))
    rng = np.random.default_rng(seed)
    out = []
    for m in _chunks(n_boot, k):
        r = rng.integers(0, k, (m, k))
        stat = np.zeros(m)
        with np.errstate(invalid="ignore", divide="ignore"):
            for c, s, n in sums:
                stat += c * s[r].sum(1) / n[r].sum(1)
        out.append(stat)
    return np.concatenate(out) if out else np.zeros(0)


def bootstrap_ci(per_image: pd.Series, n_boot: int = 2000, seed: int = 0,
                 alpha: float = 0.05, groups: pd.Series | None = None) -> tuple[float, float, float]:
    """(mean, lo, hi): percentile bootstrap CI of the mAP.

    Same scheme as ``paired_bootstrap_diff``: resample ALL evaluated images (excluded ones are
    NaN) and take the nanmean in each replicate, so the scored-image denominator varies as it
    does for the real metric. To first order this equals resampling scored images only.
    `groups` (image id -> NIH patient) switches to a cluster bootstrap: whole patients are resampled.
    Replicates with no scored image are dropped.
    """
    x = np.asarray(per_image, dtype=np.float64)
    ok = ~np.isnan(x)
    if not ok.any():
        return float("nan"), float("nan"), float("nan")
    codes, k = bootstrap_codes(per_image.index, groups)
    b = bootstrap_ratio_replicates([(1.0, x)], codes, k, n_boot, seed)
    lo, hi = np.quantile(b[~np.isnan(b)], [alpha / 2, 1 - alpha / 2])
    return float(x[ok].mean()), float(lo), float(hi)


def _chunks(n_boot: int, n: int, budget: int = 4_000_000) -> list[int]:
    step = max(1, budget // max(n, 1))
    return [min(step, n_boot - i) for i in range(0, n_boot, step)]


def paired_bootstrap_diff(per_image_a: pd.Series, per_image_b: pd.Series, n_boot: int = 2000,
                          seed: int = 0, alpha: float = 0.05, groups: pd.Series | None = None) -> dict:
    """Paired bootstrap of mAP(a) - mAP(b) on the same images.

    Exclusion handling: both series are aligned on the UNION of their indices (missing ==
    excluded/NaN). Each bootstrap replicate resamples images from that union and computes
    each model's mean over its own scored images in the replicate, i.e. exactly how the
    metric itself is computed. So an image excluded for A (no GT, A predicted nothing) but
    scored 0 for B (B predicted a FP) is kept and penalizes B, as in the real score.
    `groups` (image id -> NIH patient) resamples whole patients instead of images.
    The point estimate equals rsna_map(a) - rsna_map(b).
    """
    idx = per_image_a.index.union(per_image_b.index)
    a = per_image_a.reindex(idx).to_numpy(np.float64)
    b = per_image_b.reindex(idx).to_numpy(np.float64)
    ma, mb = ~np.isnan(a), ~np.isnan(b)
    codes, k = bootstrap_codes(idx, groups)
    d = bootstrap_ratio_replicates([(1.0, a), (-1.0, b)], codes, k, n_boot, seed)
    d = d[~np.isnan(d)]
    lo, hi = np.quantile(d, [alpha / 2, 1 - alpha / 2]) if len(d) else (np.nan, np.nan)
    return {"diff": _nanmean(a) - _nanmean(b), "lo": float(lo), "hi": float(hi),
            "p_diff_le_0": float((d <= 0).mean()) if len(d) else float("nan"),
            "n_images": len(idx), "n_scored_a": int(ma.sum()), "n_scored_b": int(mb.sum()),
            "n_boot": len(d), "bootstrap_unit": "image" if groups is None else "group", "n_units": k}


# ----------------------------------------------------------------------------- IO helpers

def load_gt(boxes_csv: str | Path | pd.DataFrame, image_ids: list[str]) -> dict[str, np.ndarray]:
    """GT boxes [k, 4] xywh for every id in image_ids (empty [0, 4] for negatives).

    Rows with NaN boxes (raw stage_2_train_labels negatives) are ignored.
    """
    df = boxes_csv if isinstance(boxes_csv, pd.DataFrame) else pd.read_csv(boxes_csv)
    df = df[df["patientId"].isin(set(image_ids))].dropna(subset=BOX_COLS)
    out = {iid: np.zeros((0, 4)) for iid in image_ids}
    for pid, (boxes, _) in _group(df, with_scores=False).items():
        out[pid] = boxes
    return out


PRED_DECIMALS = {"score": 4, "x": 1, "y": 1, "width": 1, "height": 1}
IMAGE_SCORE_DECIMALS = 5


def round_preds(df: pd.DataFrame) -> pd.DataFrame:
    """Storage precision of prediction tables (score 4 dp, boxes 0.1 px).

    Applied once where predictions are created, BEFORE any metric, so in-memory scores and the
    CSV round trip are identical (every code path gives the same mAP).
    """
    return df.round(PRED_DECIMALS)


def preds_from_df(df: pd.DataFrame) -> Preds:
    """Prediction table (patientId, score, x, y, width, height) -> {id: (boxes [k,4], scores [k])}.

    Rows with NaN score/box (e.g. a placeholder row for an image without boxes) are dropped.
    """
    return _group(df.dropna(subset=["score", *BOX_COLS]), with_scores=True)


def _group(df: pd.DataFrame, with_scores: bool) -> Preds:
    if len(df) == 0:
        return {}
    pid = df["patientId"].astype(str).to_numpy()
    order = np.argsort(pid, kind="stable")
    uniq, starts = np.unique(pid[order], return_index=True)
    boxes = np.split(df[BOX_COLS].to_numpy(np.float64)[order], starts[1:])
    scores = (np.split(df["score"].to_numpy(np.float64)[order], starts[1:]) if with_scores
              else [np.ones(len(b)) for b in boxes])
    return {u: (b, s) for u, b, s in zip(uniq, boxes, scores)}


# ------------------------------------------------------------------------- extra metrics

def image_scores_from_preds(pred: Preds, image_ids: list[str]) -> np.ndarray:
    """Image-level score = max box score (0 for images without predictions)."""
    return np.array([float(np.max(pred[i][1])) if i in pred and len(pred[i][1]) else 0.0
                     for i in image_ids])


def image_level_metrics(y_true: np.ndarray, y_score: np.ndarray,
                        threshold: float | None = None) -> dict[str, float]:
    """ROC-AUC, PR-AUC (average precision) and, given a threshold (score >= thr is positive),
    sensitivity / specificity / positive rate."""
    from sklearn.metrics import average_precision_score, roc_auc_score

    y = np.asarray(y_true).astype(int)
    s = np.asarray(y_score, dtype=np.float64)
    two = len(np.unique(y)) == 2
    out = {"roc_auc": float(roc_auc_score(y, s)) if two else float("nan"),
           "pr_auc": float(average_precision_score(y, s)) if two else float("nan")}
    if threshold is not None:
        p = s >= threshold
        out["sensitivity"] = float(p[y == 1].mean()) if (y == 1).any() else float("nan")
        out["specificity"] = float((~p[y == 0]).mean()) if (y == 0).any() else float("nan")
        out["positive_rate"] = float(p.mean()) if len(p) else float("nan")
    return out


def matched_iou(gt: dict[str, np.ndarray], pred: Preds, image_ids: list[str],
                score_threshold: float = 0.0, iou_threshold: float = 0.4) -> float:
    """Mean IoU of TP pairs under the competition matching at a single IoU threshold."""
    t = np.array([iou_threshold], dtype=np.float64)
    vals: list[np.ndarray] = []
    for iid in _check_ids(image_ids):
        g, b, s = _get(gt, pred, iid)
        keep = s >= score_threshold
        b, s = b[keep], s[keep]
        hit, miou = _greedy(iou_xywh(b[np.argsort(-s, kind="stable")], g), t)
        vals.append(miou[hit])
    v = np.concatenate(vals) if vals else np.zeros(0)
    return float(v.mean()) if len(v) else float("nan")
