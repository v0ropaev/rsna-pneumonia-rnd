"""HW2 mechanism checks (reports/HW2.md §7): what gating and augmentation change, measured at matched operating points.

The val-optimal threshold differs between units, so FP-image rate and sensitivity at each unit's own threshold mix
the effect of a change with a move along the ROC curve. Here every comparison is threshold-free or at a matched FP
rate, always on the same images and paired by patient:

1. image AUC of the max box score (the score that decides whether an image gets any box) and sensitivity at the
   FP-image rate of the other side (ROC interpolation), with a paired patient-bootstrap CI of ΔAUC:
   gating = run (gated) vs its post-hoc no_gating variant (same checkpoint);
   augmentation = b_aug_s vs baseline_s and full_s vs b_cls_s (same seed);
2. train detection loss (hm + w·wh + w·off, epoch mean on the batches as trained, i.e. augmented for aug runs) at the
   selected epoch and at the last epoch, from history.csv;
3. PA / AP slices: paired patient-bootstrap Δ mAP of gated vs no_gating on the PA and AP images of val, AUC of the
   max box score within the view (gated / no_gating) and the mean head probability P of positives / negatives.
The gated side of every gating contrast is the unit whose box_scale equals that of the no_gating variant (as trained,
or the tuned variant when both were tuned to the same scale), so the contrast changes the score only.
Sensitivity at a given FP rate is read off the ROC as a hard threshold would give it (lowest TPR on a vertical ROC
segment), the same convention as the units' own sensitivity at their threshold. Missing runs are skipped.

Writes results/hw2_summary/mechanism.md and mechanism.json. VAL only (test plays no role in the mechanism analysis).
Run: PYTHONPATH=src .venv/bin/python scripts/analyze_hw2_mechanism.py [--n-boot 2000]
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve

from rsna import paths
from rsna.evaluate import load_meta, patient_groups
from rsna.metric import bootstrap_codes, load_gt, paired_bootstrap_diff
from rsna.report import Unit, evaluate_unit, load_run

GATED = ["b_cls_s0", "b_cls_s1", "full_s0", "full_s1", "full_s2"]
AUG_PAIRS = [("b_aug_s0", "baseline_s0"), ("b_aug_s1", "baseline_s1"), ("full_s0", "b_cls_s0"), ("full_s1", "b_cls_s1")]


def unit(run: str, variant: str = "") -> Unit:
    r = load_run(paths.RESULTS / run)
    return Unit(r, variant, r.dir / "posthoc" / variant if variant else r.dir)


def max_box_score(u: Unit, ids: list[str]) -> pd.Series:
    p = pd.read_csv(u.dir / "val_predictions.csv", dtype={"patientId": str})
    return p.groupby("patientId")["score"].max().reindex(ids).fillna(0.0)


def tpr_at_fpr(y: np.ndarray, s: np.ndarray, fpr0: float) -> float:
    """TPR at FPR fpr0; on a vertical ROC segment the lowest TPR (= a hard threshold at that score)."""
    fpr, tpr, _ = roc_curve(y, s, drop_intermediate=False)
    f, first = np.unique(fpr, return_index=True)
    return float(np.interp(fpr0, f, tpr[first]))


def have(run: str) -> bool:
    return (paths.RESULTS / run / "meta.json").exists()


def gated_unit(run: str) -> Unit:
    """The gated unit with the same box_scale as the run's no_gating variant (score_mode is the only difference)."""
    ng = json.loads((paths.RESULTS / run / "posthoc/no_gating/variant.json").read_text())
    tv = paths.RESULTS / run / "posthoc/tuned/variant.json"
    if float(ng.get("box_scale", 1.0)) != 1.0 and tv.exists() and \
            float(json.loads(tv.read_text()).get("box_scale", 1.0)) == float(ng["box_scale"]):
        return unit(run, "tuned")
    return unit(run)


def auc_diff_boot(y: np.ndarray, a: np.ndarray, b: np.ndarray, codes: np.ndarray, k: int, n_boot: int,
                  seed: int = 0) -> tuple[float, float, float]:
    """Paired cluster bootstrap of AUC(a) − AUC(b): patients resampled with all their images, one draw for both."""
    rng = np.random.default_rng(seed)
    members = [np.flatnonzero(codes == c) for c in range(k)]
    d = []
    for _ in range(n_boot):
        idx = np.concatenate([members[c] for c in rng.integers(0, k, k)])
        yy = y[idx]
        if yy.min() == yy.max():
            continue
        d.append(roc_auc_score(yy, a[idx]) - roc_auc_score(yy, b[idx]))
    lo, hi = np.quantile(d, [0.025, 0.975])
    return float(roc_auc_score(y, a) - roc_auc_score(y, b)), float(lo), float(hi)


def operating(ev) -> tuple[float, float, float]:
    return ev.thr, ev.metrics["fp_image_rate"], ev.metrics["sensitivity"]


def compare_scores(a: Unit, b: Unit, ids, y, codes, k, gt, target, n_boot) -> dict:
    sa, sb = max_box_score(a, ids).to_numpy(), max_box_score(b, ids).to_numpy()
    ea, eb = evaluate_unit(a, gt, target), evaluate_unit(b, gt, target)
    (ta, fa, sena), (tb, fb, senb) = operating(ea), operating(eb)
    d, lo, hi = auc_diff_boot(y, sa, sb, codes, k, n_boot)
    return {"a": a.key, "b": b.key, "auc_a": float(roc_auc_score(y, sa)), "auc_b": float(roc_auc_score(y, sb)),
            "d_auc": d, "d_auc_lo": lo, "d_auc_hi": hi,
            "thr_a": ta, "fp_a": fa, "sens_a": sena, "thr_b": tb, "fp_b": fb, "sens_b": senb,
            "sens_b_at_fp_a": tpr_at_fpr(y, sb, fa), "sens_a_at_fp_b": tpr_at_fpr(y, sa, fb)}


def det_loss(run: str) -> dict:
    r = load_run(paths.RESULTS / run)
    h = pd.read_csv(r.dir / "history.csv")
    w = float((r.cfg.get("loss") or {}).get("cls_weight", 1.0))
    det = h["loss"] - w * h["loss_cls"] if "loss_cls" in h else h["loss"]
    best = int(h.loc[h["val_map"].idxmax(), "epoch"])
    return {"run": run, "best_epoch": best, "det_loss_best": float(det[h["epoch"] == best].iloc[0]),
            "det_loss_last": float(det.iloc[-1]), "val_map_best": float(h["val_map"].max()),
            "val_map_last": float(h["val_map"].iloc[-1])}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-boot", type=int, default=2000)
    a = ap.parse_args()
    meta = load_meta()
    val = meta[meta["split"] == "val"].set_index("patientId")
    ids = val.index.tolist()
    y = val["target"].to_numpy()
    groups = patient_groups(meta)
    codes, k = bootstrap_codes(pd.Index(ids), groups)
    gt = load_gt(paths.BOXES, ids)
    target = meta.set_index("patientId")["target"]

    gated = [r for r in GATED if have(r) and (paths.RESULTS / r / "posthoc/no_gating/val_predictions.csv").exists()]
    pairs = [(x, z) for x, z in AUG_PAIRS if have(x) and have(z)]
    loss_runs = [r for r in ["baseline_s0", "baseline_s1", "baseline_s2", "b_cls_s0", "b_cls_s1", "b_aug_s0",
                             "b_aug_s1", "full_s0", "full_s1", "full_s2"] if have(r)]
    skipped = sorted((set(GATED) | {x for p in AUG_PAIRS for x in p}) - set(gated) - {x for p in pairs for x in p})
    if skipped:
        print(f"mechanism: skipping missing runs/variants: {skipped}")
    gating = [compare_scores(gated_unit(r), unit(r, "no_gating"), ids, y, codes, k, gt, target, a.n_boot)
              for r in gated]
    aug = [compare_scores(unit(x), unit(z), ids, y, codes, k, gt, target, a.n_boot) for x, z in pairs]
    losses = [det_loss(r) for r in loss_runs]
    views = []
    for r in gated:
        ug, un = gated_unit(r), unit(r, "no_gating")
        eg, en = evaluate_unit(ug, gt, target), evaluate_unit(un, gt, target)
        sg, sn = max_box_score(ug, ids), max_box_score(un, ids)
        p = pd.read_csv(paths.RESULTS / r / "val_image_scores.csv", dtype={"patientId": str}).set_index("patientId")
        for v in ["PA", "AP"]:
            vid = val.index[val["view"] == v]
            yv = val.loc[vid, "target"]
            d = paired_bootstrap_diff(eg.per_image.reindex(vid), en.per_image.reindex(vid), n_boot=a.n_boot,
                                      groups=groups)
            views.append({"run": ug.key, "view": v, "n": len(vid), "n_pos": int(yv.sum()),
                          "map_gated": float(eg.per_image.reindex(vid).mean()),
                          "map_no_gating": float(en.per_image.reindex(vid).mean()), "diff": d["diff"],
                          "lo": d["lo"], "hi": d["hi"],
                          "auc_gated": float(roc_auc_score(yv, sg.reindex(vid))),
                          "auc_no_gating": float(roc_auc_score(yv, sn.reindex(vid))),
                          "p_pos": float(p.loc[yv.index[yv == 1], "cls_prob"].mean()),
                          "p_neg": float(p.loc[yv.index[yv == 0], "cls_prob"].mean())})

    f = lambda x, n=3: f"{x:.{n}f}"
    md = ["# HW2: проверки механизма (val)", "",
          "_Генерируется `scripts/analyze_hw2_mechanism.py`. Все сравнения на одних и тех же 4 002 снимках val; CI — "
          f"парный бутстрап по NIH-пациентам ({a.n_boot} ресэмплов). «max-box» — максимальный score бокса снимка, "
          "он решает, есть ли у снимка бокс выше порога (sensitivity = TPR, FP-image rate = FPR этого score)._", "",
          "## 1. Гейтинг: тот же чекпойнт с гейтингом (A) и без (B)", "",
          "| run | AUC max-box A | B | ΔAUC [95% CI] | порог A / B | FP-rate A / B | sens A / B (свои пороги) | "
          "sens B при FP-rate A | sens A при FP-rate B | Δsens при FP-rate A / B |", "|---|---|---|---|---|---|---|---|---|---|"]
    md += [f"| {g['a']} | {f(g['auc_a'])} | {f(g['auc_b'])} | {g['d_auc']:+.4f} [{g['d_auc_lo']:+.4f}, {g['d_auc_hi']:+.4f}] | "
           f"{g['thr_a']:.2f} / {g['thr_b']:.2f} | {f(g['fp_a'])} / {f(g['fp_b'])} | {f(g['sens_a'])} / {f(g['sens_b'])} | "
           f"{f(g['sens_b_at_fp_a'])} | {f(g['sens_a_at_fp_b'])} | {g['sens_a'] - g['sens_b_at_fp_a']:+.3f} / "
           f"{g['sens_a_at_fp_b'] - g['sens_b']:+.3f} |" for g in gating]
    md += ["", "## 2. Аугментации: A = с аугментациями, B = тот же конфиг и seed без них", "",
           "| A | B | AUC max-box A | B | ΔAUC [95% CI] | порог A / B | FP-rate A / B | sens A / B (свои пороги) | "
           "sens B при FP-rate A | sens A при FP-rate B | Δsens при FP-rate A / B |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    md += [f"| {g['a']} | {g['b']} | {f(g['auc_a'])} | {f(g['auc_b'])} | {g['d_auc']:+.4f} [{g['d_auc_lo']:+.4f}, "
           f"{g['d_auc_hi']:+.4f}] | {g['thr_a']:.2f} / {g['thr_b']:.2f} | {f(g['fp_a'])} / {f(g['fp_b'])} | "
           f"{f(g['sens_a'])} / {f(g['sens_b'])} | {f(g['sens_b_at_fp_a'])} | {f(g['sens_a_at_fp_b'])} | "
           f"{g['sens_a'] - g['sens_b_at_fp_a']:+.3f} / {g['sens_a_at_fp_b'] - g['sens_b']:+.3f} |" for g in aug]
    md += ["", "## 3. Train detection loss (на батчах как в обучении: у аугментированных прогонов — аугментированных)", "",
           "| run | лучшая эпоха | det loss на лучшей эпохе | det loss на 6-й | val mAP лучшей / 6-й эпохи |",
           "|---|---|---|---|---|"]
    md += [f"| {l['run']} | {l['best_epoch']} | {f(l['det_loss_best'])} | {f(l['det_loss_last'])} | "
           f"{f(l['val_map_best'], 4)} / {f(l['val_map_last'], 4)} |" for l in losses]
    md += ["", "## 4. Гейтинг по проекциям: Δ mAP = с гейтингом − без (тот же чекпойнт)", "",
           "| run | view | n (позитивов) | mAP с гейтингом | без | Δ [95% CI] | AUC max-box внутри view: с гейтингом / без | "
           "средний P головы: позитивы / негативы |", "|---|---|---|---|---|---|---|---|"]
    md += [f"| {v['run']} | {v['view']} | {v['n']} ({v['n_pos']}) | {f(v['map_gated'], 4)} | {f(v['map_no_gating'], 4)} | "
           f"{v['diff']:+.4f} [{v['lo']:+.4f}, {v['hi']:+.4f}] | {f(v['auc_gated'])} / {f(v['auc_no_gating'])} | "
           f"{f(v['p_pos'], 2)} / {f(v['p_neg'], 2)} |" for v in views]
    out = paths.RESULTS / "hw2_summary"
    out.mkdir(parents=True, exist_ok=True)
    (out / "mechanism.md").write_text("\n".join(md) + "\n")
    (out / "mechanism.json").write_text(json.dumps({"gating": gating, "augmentation": aug, "det_loss": losses,
                                                    "views": views}, indent=1))
    print("\n".join(md))
    print(f"-> {out / 'mechanism.md'}")


if __name__ == "__main__":
    main()
