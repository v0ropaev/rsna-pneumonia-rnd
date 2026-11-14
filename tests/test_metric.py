"""Tests for rsna.metric: hand-computed cases, edge cases and a naive reference cross-check."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rsna.metric import (
    IOU_THRESHOLDS, SCORE_THRESHOLDS, bootstrap_ci, image_level_metrics, image_precision,
    image_scores_from_preds, iou_xywh, load_gt, matched_iou, paired_bootstrap_diff,
    preds_from_df, rsna_map, threshold_sweep,
)

A = [0.0, 0.0, 10.0, 10.0]
NONE = np.zeros((0, 4))


def ap(gt, pred, scores=None):
    pred = np.asarray(pred, float).reshape(-1, 4)
    scores = np.ones(len(pred)) if scores is None else np.asarray(scores, float)
    return image_precision(np.asarray(gt, float).reshape(-1, 4), pred, scores)


# ------------------------------------------------------------------ naive reference

def naive_iou(a, b) -> float:
    ax2, ay2, bx2, by2 = a[0] + a[2], a[1] + a[3], b[0] + b[2], b[1] + b[3]
    iw = max(0.0, min(ax2, bx2) - max(a[0], b[0]))
    ih = max(0.0, min(ay2, by2) - max(a[1], b[1]))
    inter = iw * ih
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


def naive_image(gt, preds, scores, thresholds=(0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75)):
    gt = [list(map(float, g)) for g in gt]
    order = sorted(range(len(preds)), key=lambda i: -float(scores[i]))  # Python sort is stable
    preds = [list(map(float, preds[i])) for i in order]
    if not gt and not preds:
        return None
    total = 0.0
    for t in thresholds:
        used, tp = set(), 0
        for p in preds:
            best_j, best_iou = None, -1.0
            for j, g in enumerate(gt):
                if j in used:
                    continue
                v = naive_iou(p, g)
                if v > best_iou:
                    best_j, best_iou = j, v
            if best_j is not None and best_iou > t:
                used.add(best_j)
                tp += 1
        fp, fn = len(preds) - tp, len(gt) - tp
        total += tp / (tp + fp + fn)
    return total / len(thresholds)


def naive_map(gt, pred, ids, thr=0.0):
    vals = []
    for i in ids:
        boxes, scores = pred.get(i, (NONE, np.zeros(0)))
        keep = [k for k in range(len(scores)) if scores[k] >= thr]
        v = naive_image(gt.get(i, NONE), [boxes[k] for k in keep], [scores[k] for k in keep])
        if v is not None:
            vals.append(v)
    return sum(vals) / len(vals) if vals else float("nan")


def random_dataset(n: int, seed: int):
    """Random images: 0-3 GT boxes, preds = jittered GT copies + random FPs, random scores."""
    rng = np.random.default_rng(seed)
    gt, pred = {}, {}
    for i in range(n):
        iid = f"img{i:05d}"
        k = rng.choice([0, 0, 1, 2, 3])
        g = np.column_stack([rng.uniform(0, 700, (k, 2)), rng.uniform(40, 300, (k, 2))])
        gt[iid] = g
        boxes = []
        for b in g:
            for _ in range(rng.integers(0, 3)):
                noise = 0.0 if rng.random() < 0.3 else 1.0  # some exact copies -> perfect images
                j = b + noise * rng.normal(0, 1, 4) * np.r_[0.15 * b[2:], 0.2 * b[2:]]
                j[2:] = np.maximum(j[2:], 5)
                boxes.append(j)
        for _ in range(rng.integers(0, 3)):
            boxes.append(np.r_[rng.uniform(0, 700, 2), rng.uniform(40, 300, 2)])
        if boxes or rng.random() < 0.5:
            b = np.array(boxes).reshape(-1, 4)
            pred[iid] = (b, np.round(rng.random(len(b)), 2))  # rounding creates score ties
    return gt, pred, list(gt)


# ------------------------------------------------------------------ IoU

def test_iou_basic():
    m = iou_xywh(np.array([A, A]), np.array([A, [10, 0, 10, 10], [5, 0, 10, 10], [20, 20, 5, 5]]))
    assert m.shape == (2, 4)
    np.testing.assert_allclose(m[0], [1.0, 0.0, 50 / 150, 0.0])
    assert iou_xywh(NONE, np.array([A])).shape == (0, 1)
    assert iou_xywh(np.array([[0, 0, 0, 0]]), np.array([[0, 0, 0, 0]]))[0, 0] == 0.0


def test_thresholds_constant():
    np.testing.assert_array_equal(IOU_THRESHOLDS, [0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75])
    assert len(SCORE_THRESHOLDS) == 19 and SCORE_THRESHOLDS[0] == 0.05 and SCORE_THRESHOLDS[-1] == 0.95


# ------------------------------------------------------------------ edge cases

def test_empty_gt_empty_pred_excluded():
    assert ap(NONE, NONE) is None


def test_empty_gt_with_preds_scores_zero():
    assert ap(NONE, [A]) == 0.0
    assert ap(NONE, [A, A, [50, 50, 5, 5]]) == 0.0


def test_gt_without_preds_scores_zero():
    assert ap([A], NONE) == 0.0
    assert ap([A, [50, 50, 10, 10]], NONE) == 0.0


def test_perfect_match():
    assert ap([A], [A]) == 1.0
    assert ap([A, [50, 50, 10, 10]], [[50, 50, 10, 10], A]) == 1.0


def test_iou_exactly_at_threshold_is_not_a_hit():
    # IoU = 0.5 exactly: hit only for t in {0.40, 0.45} -> 2/8 (would be 3/8 with ">=")
    assert iou_xywh(np.array([[0, 0, 10, 5]]), np.array([A]))[0, 0] == 0.5
    assert ap([A], [[0, 0, 10, 5]]) == pytest.approx(2 / 8)
    # IoU = 0.75 exactly: hit for all but t=0.75 -> 7/8
    assert ap([A], [[0, 0, 10, 7.5]]) == pytest.approx(7 / 8)
    # IoU = 0.4 exactly: never a hit -> 1 FP + 1 FN at every t
    assert ap([A], [[0, 0, 10, 4]]) == 0.0
    # just above 0.4 -> hit at t=0.4 only: (1 + 7 * 0) / 8
    assert ap([A], [[0, 0, 10, 4.01]]) == pytest.approx(1 / 8)


def test_partial_iou_mixes_thresholds():
    # IoU = 0.6: hits at 0.40..0.55 (4 thresholds) -> TP=1; else FP=1, FN=1 -> 0
    assert ap([A], [[0, 0, 10, 6]]) == pytest.approx(4 / 8)


def test_multiple_gt_and_preds():
    far = [100, 100, 10, 10]
    # 2 GT, one perfect pred + one FP far away: TP=1 FP=1 FN=1 -> 1/3
    assert ap([A, [50, 50, 10, 10]], [A, far]) == pytest.approx(1 / 3)
    # duplicate prediction of the same GT: TP=1 FP=1 -> 1/2
    assert ap([A], [A, A]) == pytest.approx(1 / 2)
    # 3 GT, 2 perfect preds: TP=2 FN=1 -> 2/3
    assert ap([A, [50, 50, 10, 10], far], [A, far]) == pytest.approx(2 / 3)
    # a wide pred covering two GT matches only one of them. IoU with each GT = 100/200 = 0.5:
    # t in {0.40, 0.45}: TP=1 FN=1 -> 1/2; other t: FP=1 FN=2 -> 0
    two = [A, [10, 0, 10, 10]]
    assert ap(two, [[0, 0, 20, 10]]) == pytest.approx((2 * 0.5 + 6 * 0) / 8)


def test_confidence_order_changes_score():
    gt = [A, [10, 0, 10, 10]]  # A at x 0..10, B at x 10..20
    wide = [0, 0, 19, 10]       # IoU(A) = 100/190 = 0.526, IoU(B) = 90/200 = 0.45
    exact = A                   # IoU(A) = 1, IoU(B) = 0
    # wide first: it takes A (t<=0.5) -> exact is FP; for t>=0.55 wide misses, exact takes A.
    # Every t: TP=1 FP=1 FN=1 -> 1/3
    assert ap(gt, [wide, exact], [0.9, 0.1]) == pytest.approx(1 / 3)
    # exact first: takes A; wide then gets B only if 0.45 > t, i.e. t=0.40 -> 1; else 1/3
    assert ap(gt, [wide, exact], [0.1, 0.9]) == pytest.approx((1 + 7 / 3) / 8)


def test_permutation_invariance():
    gt, pred, ids = random_dataset(200, seed=1)
    rng = np.random.default_rng(7)
    for iid in ids:
        b, s = pred.get(iid, (NONE, np.zeros(0)))
        s = s + rng.random(len(s)) * 1e-6  # remove ties: order among equal scores is a convention
        pred[iid] = (b, s)
        p, q = rng.permutation(len(s)), rng.permutation(len(gt[iid]))
        ref, got = image_precision(gt[iid], b, s), image_precision(gt[iid][q], b[p], s[p])
        assert (ref is None and got is None) or got == pytest.approx(ref, abs=1e-12)
    base = rsna_map(gt, pred, ids)
    shuffled = [ids[i] for i in rng.permutation(len(ids))]
    assert rsna_map(gt, pred, shuffled) == pytest.approx(base, abs=1e-12)


def test_equal_scores_keep_input_order():
    gt = [A, [10, 0, 10, 10]]
    wide, exact = [0, 0, 19, 10], A
    assert ap(gt, [wide, exact], [0.5, 0.5]) == pytest.approx(1 / 3)
    assert ap(gt, [exact, wide], [0.5, 0.5]) == pytest.approx((1 + 7 / 3) / 8)


def test_scores_length_mismatch_raises():
    with pytest.raises(ValueError):
        image_precision(np.array([A]), np.array([A]), np.array([0.1, 0.2]))


# ------------------------------------------------------------------ rsna_map

def make_small():
    gt = {"pos": np.array([A]), "neg": NONE.copy(), "neg2": NONE.copy()}
    pred = {"pos": (np.array([A, [50, 50, 10, 10]]), np.array([0.9, 0.3])),
            "neg": (np.array([[5, 5, 5, 5]]), np.array([0.4])),
            "stranger": (np.array([A]), np.array([1.0]))}  # not in image_ids -> ignored
    return gt, pred, ["pos", "neg", "neg2"]


def test_rsna_map_exclusion_and_missing_preds():
    gt, pred, ids = make_small()
    m, per = rsna_map(gt, pred, ids, return_per_image=True)
    # pos: TP=1 FP=1 -> 0.5; neg: FP -> 0; neg2: no GT, missing from pred -> excluded
    assert per["pos"] == pytest.approx(0.5) and per["neg"] == 0.0 and np.isnan(per["neg2"])
    assert m == pytest.approx(0.25)
    assert list(per.index) == ids and per.index.name == "patientId"


def test_rsna_map_score_threshold_inclusive():
    gt, pred, ids = make_small()
    # thr 0.4: pos keeps only the 0.9 box -> 1.0; neg keeps 0.4 (>=) -> 0 -> mean 0.5
    assert rsna_map(gt, pred, ids, score_threshold=0.4) == pytest.approx(0.5)
    # thr 0.41: neg box dropped -> neg excluded -> mean over pos only = 1.0
    m, per = rsna_map(gt, pred, ids, score_threshold=0.41, return_per_image=True)
    assert m == pytest.approx(1.0) and np.isnan(per["neg"])
    # thr 0.95: pos has no preds -> 0, negatives excluded
    assert rsna_map(gt, pred, ids, score_threshold=0.95) == 0.0


def test_rsna_map_all_excluded_is_nan():
    assert np.isnan(rsna_map({"a": NONE}, {}, ["a"]))


def test_rsna_map_missing_gt_means_negative():
    assert rsna_map({}, {"a": (np.array([A]), np.array([0.5]))}, ["a"]) == 0.0


def test_rsna_map_rejects_duplicate_ids():
    with pytest.raises(ValueError):
        rsna_map({}, {}, ["a", "a"])


@pytest.mark.parametrize("thr", [0.0, 0.3, 0.55, 0.9])
def test_rsna_map_matches_naive_reference(thr):
    gt, pred, ids = random_dataset(300, seed=0)
    m, per = rsna_map(gt, pred, ids, score_threshold=thr, return_per_image=True)
    assert m == pytest.approx(naive_map(gt, pred, ids, thr), abs=1e-12)
    # per-image too, including the excluded set
    for iid in ids:
        b, s = pred.get(iid, (NONE, np.zeros(0)))
        k = s >= thr
        ref = naive_image(gt[iid], list(b[k]), list(s[k]))
        assert (np.isnan(per[iid]) and ref is None) or per[iid] == pytest.approx(ref, abs=1e-12)
    # sanity: the random set really exercises every regime
    assert 0 < m < 1 and per.isna().any() and (per == 0).any() and (per == 1).any()


# ------------------------------------------------------------------ threshold sweep

def test_threshold_sweep_matches_rsna_map():
    gt, pred, ids = random_dataset(300, seed=3)
    sw = threshold_sweep(gt, pred, ids)
    assert list(sw.columns[:2]) == ["thr", "map"] and len(sw) == 19
    for thr, m, n in sw[["thr", "map", "n_scored"]].itertuples(index=False):
        ref, per = rsna_map(gt, pred, ids, score_threshold=thr, return_per_image=True)
        assert m == pytest.approx(ref, abs=1e-12) and n == per.notna().sum()
    assert sw["map"].iloc[[0, 9]].tolist() == pytest.approx(
        [naive_map(gt, pred, ids, 0.05), naive_map(gt, pred, ids, 0.5)], abs=1e-12)


def test_threshold_sweep_edge_inputs():
    gt, pred, ids = make_small()
    sw = threshold_sweep(gt, pred, ids, thresholds=[0.4, 0.41, 0.95])
    assert sw["map"].tolist() == pytest.approx([0.5, 1.0, 0.0])
    empty = threshold_sweep({"a": NONE}, {}, ["a"], thresholds=[0.5])
    assert np.isnan(empty["map"].iloc[0]) and empty["n_scored"].iloc[0] == 0


# ------------------------------------------------------------------ bootstrap

def test_bootstrap_ci_sanity():
    rng = np.random.default_rng(0)
    x = pd.Series(np.r_[rng.random(1000), [np.nan] * 50])
    mean, lo, hi = bootstrap_ci(x, n_boot=2000, seed=0)
    assert mean == pytest.approx(x.mean()) and lo < mean < hi
    se = x.dropna().std() / np.sqrt(1000)
    assert (hi - lo) == pytest.approx(2 * 1.96 * se, rel=0.15)
    assert bootstrap_ci(x, n_boot=500, seed=1) == bootstrap_ci(x, n_boot=500, seed=1)
    assert bootstrap_ci(pd.Series([0.5] * 10)) == (0.5, 0.5, 0.5)
    assert all(np.isnan(bootstrap_ci(pd.Series([np.nan, np.nan]))))


def test_paired_bootstrap_sign_and_identity():
    rng = np.random.default_rng(0)
    ids = [f"i{k}" for k in range(500)]
    a = pd.Series(rng.random(500), index=ids)
    b = (a + 0.05 + rng.normal(0, 0.02, 500)).clip(0, 1)
    r = paired_bootstrap_diff(b, a, n_boot=1000)
    assert r["diff"] > 0 and r["lo"] > 0 and r["p_diff_le_0"] == 0.0
    r = paired_bootstrap_diff(a, b, n_boot=1000)
    assert r["diff"] < 0 and r["hi"] < 0 and r["p_diff_le_0"] == 1.0
    r = paired_bootstrap_diff(a, a, n_boot=200)
    assert r["diff"] == 0 and r["lo"] == 0 and r["hi"] == 0
    # pairing beats unpaired noise: a tiny consistent gain is still detected
    c = a + 1e-3
    assert paired_bootstrap_diff(c, a, n_boot=500)["lo"] > 0


def test_paired_bootstrap_exclusion_consistent_with_metric():
    gt = {"p": np.array([A]), "n": NONE}
    pa = {"p": (np.array([A]), np.array([0.9]))}                         # n excluded for A
    pb = {"p": (np.array([A]), np.array([0.9])), "n": (np.array([A]), np.array([0.9]))}
    ma, sa = rsna_map(gt, pa, ["p", "n"], return_per_image=True)
    mb, sb = rsna_map(gt, pb, ["p", "n"], return_per_image=True)
    assert (ma, mb) == (1.0, 0.5)
    r = paired_bootstrap_diff(sa, sb, n_boot=500)
    assert r["diff"] == pytest.approx(ma - mb) and r["n_images"] == 2
    assert (r["n_scored_a"], r["n_scored_b"]) == (1, 2)
    # index missing in one series == excluded there
    r2 = paired_bootstrap_diff(sa.drop("n"), sb, n_boot=500)
    assert r2["diff"] == pytest.approx(0.5) and r2["n_images"] == 2


# ------------------------------------------------------------------ IO helpers & extras

def test_load_gt_and_preds_from_df():
    boxes = pd.DataFrame({"patientId": ["a", "a", "b", "c"], "x": [0, 50, 1, np.nan],
                          "y": [0, 50, 1, np.nan], "width": [10, 10, 5, np.nan],
                          "height": [10, 10, 5, np.nan]})
    gt = load_gt(boxes, ["a", "c", "d"])
    assert set(gt) == {"a", "c", "d"} and gt["a"].shape == (2, 4)
    assert gt["c"].shape == (0, 4) and gt["d"].shape == (0, 4)
    df = pd.DataFrame({"patientId": ["b", "a", "b", "e"], "score": [0.2, 0.9, 0.8, np.nan],
                       "x": [1, 0, 2, 0], "y": [1, 0, 2, 0], "width": [3, 10, 3, 1],
                       "height": [3, 10, 3, 1]})
    pred = preds_from_df(df)
    assert set(pred) == {"a", "b"}
    np.testing.assert_array_equal(pred["b"][1], [0.2, 0.8])
    np.testing.assert_array_equal(pred["b"][0][1], [2, 2, 3, 3])
    assert rsna_map(gt, pred, ["a", "c", "d"]) == pytest.approx(0.5)  # a: 1 TP 1 FN
    assert preds_from_df(df.iloc[:0]) == {}


def test_load_gt_from_csv(tmp_path):
    p = tmp_path / "boxes.csv"
    pd.DataFrame({"patientId": ["a"], "x": [1.0], "y": [2.0], "width": [3.0], "height": [4.0]}).to_csv(p, index=False)
    np.testing.assert_array_equal(load_gt(p, ["a"])["a"], [[1, 2, 3, 4]])


def test_extra_metrics():
    pred = {"a": (np.array([A, A]), np.array([0.2, 0.7]))}
    np.testing.assert_array_equal(image_scores_from_preds(pred, ["a", "b"]), [0.7, 0.0])
    m = image_level_metrics(np.array([1, 1, 0, 0]), np.array([0.9, 0.4, 0.5, 0.1]), threshold=0.45)
    assert m["roc_auc"] == pytest.approx(0.75) and m["sensitivity"] == 0.5 and m["specificity"] == 0.5
    assert np.isnan(image_level_metrics(np.array([1, 1]), np.array([0.1, 0.2]))["roc_auc"])
    gt = {"a": np.array([A]), "b": np.array([A])}
    pred = {"a": (np.array([A]), np.array([0.9])), "b": (np.array([[0, 0, 10, 6]]), np.array([0.9]))}
    assert matched_iou(gt, pred, ["a", "b"]) == pytest.approx(0.8)
    assert matched_iou(gt, pred, ["a", "b"], iou_threshold=0.6) == pytest.approx(1.0)


def test_bootstrap_ci_resamples_all_ids_like_paired():
    """Excluded (NaN) images are resampled too and each replicate takes a nanmean (research_notes §1.5)."""
    rng = np.random.default_rng(3)
    x = np.r_[rng.random(300), [np.nan] * 200]
    mean, lo, hi = bootstrap_ci(pd.Series(x), n_boot=400, seed=7)
    r = np.random.default_rng(7).integers(0, len(x), (400, len(x)))
    ref = np.nanmean(x[r], axis=1)
    assert mean == pytest.approx(np.nanmean(x))
    assert (lo, hi) == pytest.approx(tuple(np.quantile(ref, [0.025, 0.975])), abs=1e-12)
    # paired bootstrap of a run against an all-zero run with identical exclusions == single-run CI
    s, z = pd.Series(x), pd.Series(np.where(np.isnan(x), np.nan, 0.0))
    p = paired_bootstrap_diff(s, z, n_boot=400, seed=7)
    assert (p["lo"], p["hi"]) == pytest.approx((lo, hi), abs=1e-12)


def test_rounded_predictions_survive_csv_round_trip(tmp_path):
    """round_preds frames score identically in memory and after write_preds -> read_csv (one mAP per run)."""
    from rsna.decode import to_frames
    from rsna.evaluate import read_preds, write_preds

    rng = np.random.default_rng(0)
    ids = [f"p{i}" for i in range(400)]
    gt = {i: rng.uniform(0, 600, (rng.integers(0, 3), 4)) for i in ids}
    dets = []
    for i in ids:
        k = rng.integers(0, 4)
        b = np.c_[rng.uniform(0, 600, (k, 2)), rng.uniform(20, 400, (k, 2))]
        if len(gt[i]) and k:
            b[0] = gt[i][0] + rng.normal(0, 3, 4)
        sc = rng.choice(np.r_[SCORE_THRESHOLDS - 2e-5, rng.uniform(0.01, 1, 20)], k).astype(np.float32)
        dets.append((b.astype(np.float32).astype(np.float64), sc.astype(np.float64)))
    pred, img = to_frames(ids, dets, rng.random(len(ids)).astype(np.float32).astype(np.float64))
    write_preds(pred, img, tmp_path, "val")
    disk = read_preds(tmp_path / "val_predictions.csv")
    disk_img = pd.read_csv(tmp_path / "val_image_scores.csv", dtype={"patientId": str})
    np.testing.assert_array_equal(disk[["score", "x", "y", "width", "height"]].to_numpy(),
                                  pred[["score", "x", "y", "width", "height"]].to_numpy())
    np.testing.assert_array_equal(disk_img["image_score"].to_numpy(), img["image_score"].to_numpy())
    pd.testing.assert_frame_equal(threshold_sweep(gt, preds_from_df(pred), ids),
                                  threshold_sweep(gt, preds_from_df(disk), ids))
