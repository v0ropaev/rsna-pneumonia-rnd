"""Trivial reference baselines (no learning from pixels). CLI: python -m rsna.baselines [--split val|test] [--limit N]

* empty          — no boxes anywhere: every positive scores 0, every negative is excluded -> mAP 0 by construction.
* prior_boxes    — k-means (k=2, Euclidean on xywh) of TRAIN positive boxes; both prior boxes on every image with a
                   constant score. Measures what "a box over each lung" gets without looking at the image.
* prior_boxes_ap — the same boxes only on AP-view images (AP is ~4x more often positive than PA in train):
                   a metadata shortcut, not a legitimate model; shows how much a trivial image-level rule buys.

Constant scores make the score-threshold sweep degenerate (keep all / keep none), so the threshold is still taken
from the VAL sweep for uniformity. Each variant is a run directory under results/baseline_trivial/<variant>/ with
the standard prediction tables, so `rsna.evaluate compare` works on it. Test is evaluated only with --split test.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from . import paths
from .evaluate import _jsonable, _prefix, evaluate_predictions, load_meta, split_ids, to_markdown, write_preds
from .metric import BOX_COLS, load_gt, preds_from_df, round_preds, threshold_sweep

OUT = paths.RESULTS / "baseline_trivial"
SCORE = 0.5
VARIANTS = ["empty", "prior_boxes", "prior_boxes_ap"]


def fit_priors(meta: pd.DataFrame, k: int = 2, seed: int = 0) -> np.ndarray:
    """k prior boxes (xywh, original px) = k-means centroids of TRAIN positive boxes, sorted left to right."""
    train_ids = set(meta.loc[meta["split"] == "train", "patientId"])
    boxes = pd.read_csv(paths.BOXES, dtype={"patientId": str})
    x = boxes.loc[boxes["patientId"].isin(train_ids), BOX_COLS].to_numpy(np.float64)
    c = KMeans(n_clusters=k, n_init=10, random_state=seed).fit(x).cluster_centers_
    return c[np.argsort(c[:, 0])]


def make_predictions(variant: str, ids: list[str], meta: pd.DataFrame, priors: np.ndarray
                     ) -> tuple[pd.DataFrame, pd.DataFrame]:
    m = meta.set_index("patientId").loc[ids]
    on = {"empty": np.zeros(len(ids), bool), "prior_boxes": np.ones(len(ids), bool),
          "prior_boxes_ap": (m["view"] == "AP").to_numpy()}[variant]
    rows = [(pid, SCORE, *b) for pid, flag in zip(ids, on) if flag for b in priors]
    pred = round_preds(pd.DataFrame(rows, columns=["patientId", "score", *BOX_COLS]))  # score == stored CSV
    return pred, pd.DataFrame({"patientId": ids, "image_score": np.where(on, SCORE, 0.0)})


def run(split: str = "val", limit: int | None = None, n_boot: int = 2000) -> pd.DataFrame:
    meta = load_meta()
    priors = fit_priors(meta)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "priors.json").write_text(json.dumps({"fit_on": "train positive boxes", "k": len(priors), "score": SCORE,
                                                 "priors_xywh": np.round(priors, 1).tolist()}, indent=2))
    ids = split_ids(meta, split, limit)
    prefix = _prefix(split, limit)
    rows, md = [], [f"## Trivial baselines — {split} ({len(ids)} images)", "",
                    f"Prior boxes (k-means k=2 on train positives, xywh px): {np.round(priors, 1).tolist()}", ""]
    for v in VARIANTS:
        out = OUT / v
        out.mkdir(exist_ok=True)
        pred_df, img_df = make_predictions(v, ids, meta, priors)
        write_preds(pred_df, img_df, out, prefix)
        if split == "val":
            sweep = threshold_sweep(load_gt(paths.BOXES, ids), preds_from_df(pred_df), ids)
            if not limit:
                sweep.to_csv(out / "threshold_sweep.csv", index=False, float_format="%.5f")
        else:
            sweep = pd.read_csv(out / "threshold_sweep.csv")  # threshold always from VAL
        thr = float(sweep.loc[sweep["map"].idxmax(), "thr"])
        mt, _ = evaluate_predictions(pred_df, img_df, ids, meta, thr, n_boot=n_boot)
        mt = {"run": f"baseline_trivial/{v}", "split": split, "limit": limit, **mt}
        (out / f"{prefix}_metrics.json").write_text(json.dumps(_jsonable(mt), indent=2, ensure_ascii=False))
        (out / f"{prefix}_metrics.md").write_text(to_markdown(mt, f"{v} — {split}"))
        e = mt["errors"]
        rows.append({"variant": v, "thr": thr, "map": mt["map"], "ci_lo": mt["ci_lo"], "ci_hi": mt["ci_hi"],
                     "n_scored": mt["n_scored"], "map_pos": e["map_pos"], "fp_image_rate": e["fp_image_rate"],
                     "image_auc": mt["image_roc_auc"], "matched_iou": mt["matched_iou"],
                     "oracle_gating": mt["oracle_gating"]["map_at_run_thr"]})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / f"{prefix}_summary.csv", index=False, float_format="%.5f")
    md += ["| variant | thr | mAP | 95% CI | scored | mAP pos | FP-img rate | img AUC | matched IoU | oracle gating |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    md += [f"| {r.variant} | {r.thr:.2f} | {r.map:.4f} | [{r.ci_lo:.4f}, {r.ci_hi:.4f}] | {r.n_scored} | "
           f"{r.map_pos:.4f} | {r.fp_image_rate:.3f} | {r.image_auc:.3f} | {r.matched_iou:.3f} | {r.oracle_gating:.4f} |"
           for r in df.itertuples()]
    text = "\n".join(md).replace("nan", "–") + "\n"
    (OUT / f"{prefix}_summary.md").write_text(text)
    print(text)
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", choices=["val", "test"], default="val")
    ap.add_argument("--limit", type=int, help="smoke: first N images; writes <split>_lim<N>_* files")
    ap.add_argument("--n-boot", type=int, default=2000)
    a = ap.parse_args()
    run(a.split, a.limit, a.n_boot)


if __name__ == "__main__":
    main()
