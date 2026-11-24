"""HW3 §2.4 / RQ3 of HW1: does Full use the AP/PA projection as a shortcut? Inference only, v1 VAL, seeds 0/1/2.

1. Class-controlled view bias on the clean val: within ONE RSNA class (Normal: nothing to find by definition; Not Normal)
   compare the model's image score and FP-rate between AP and PA. AUC(view | score) inside a class = how well the score
   alone tells AP from PA there (0.5 = no view information).
2. Masking test (pre-registered in README §8 / reports/HW3_plan.md): pixels outside a lung-field rectangle derived
   from TRAIN GT boxes are replaced by the image median. Shortcut via the masked cues is SUPPORTED if masking lowers the
   FP-rate on AP negatives (paired CI of Δ < 0), leaves PA nearly unchanged and shrinks the AP/PA ratio.
   Two fields: "frame" = per-edge 0.5 / 99.5 % quantiles of the box edges (the plan's field; it cuts only the outer
   frame and leaves the PORTABLE text / L-R markers visible on most AP images, so a null result cannot refute a text
   shortcut) and "tight" = 5 / 95 % quantiles (added after the code review, NOT pre-registered: it removes most text and
   markers in a visual check, but also clips part of the lung field, so PA and the positives are the controls).
   Postural cues inside the field (heart size, clavicles, scapulae) cannot be masked: a limitation of the test.
Clean predictions are reused from results/hw3/noise/cache when present (same device); masked ones are cached in
results/hw3/shortcut/cache. Outputs: results/hw3/shortcut/shortcut.md, reports/figures/hw3_shortcut.png.
"""
from __future__ import annotations

import json
import os

os.environ.setdefault("RSNA_DEVICE", "cpu")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from matplotlib.patches import Rectangle
from sklearn.metrics import roc_auc_score

from rsna import paths
from rsna.evaluate import load_meta
from rsna.hw3 import (Predictor, condition_table, md_table, paired_unit_diff, score_condition, val_images,
                      variant_spec, masked_metric, group_diff)
from rsna.metric import load_gt
from rsna.perturb import lung_field, perturb
from rsna.report import INK, INK2, SLOTS, SURFACE, style

RUNS = ["full_s0", "full_s1", "full_s2"]
OUT = paths.RESULTS / "hw3" / "shortcut"
NOISE_CACHE = paths.RESULTS / "hw3" / "noise" / "cache"
CLS = {"Normal": "Normal", "No Lung Opacity / Not Normal": "Not Normal"}


FIELDS = {"frame": 0.005, "tight": 0.05}  # per-edge quantile q of TRAIN GT box edges


def cached(run: str, name: str, cond: list, fn) -> dict:
    """Predictions of one condition; a cache entry is reused only if it was made for the same condition and device."""
    dev = os.environ.get("RSNA_DEVICE")
    for f in (NOISE_CACHE / f"{run}__{name}.npz", OUT / "cache" / f"{run}__{name}.npz"):
        if f.exists():
            z = np.load(f, allow_pickle=False)
            summ = json.loads(str(z["summary"]))
            if summ.get("device") == dev and summ.get("condition") == cond:
                return {**summ, "ap": z["ap"], "has_box": z["has_box"], "score": z["score"]}
    out = fn()
    f = OUT / "cache" / f"{run}__{name}.npz"
    f.parent.mkdir(parents=True, exist_ok=True)
    summ = {k: v for k, v in out.items() if k not in ("ap", "has_box", "score")} | {"device": dev, "condition": cond}
    np.savez_compressed(f, ap=out["ap"], has_box=out["has_box"], score=out["score"], summary=json.dumps(summ))
    return out


def main() -> None:
    torch.set_num_threads(int(os.environ.get("HW3_THREADS", "6")))
    OUT.mkdir(parents=True, exist_ok=True)
    meta = load_meta()
    tr = set(meta.loc[meta["split"] == "train", "patientId"])
    boxes = pd.read_csv(paths.BOXES)
    trb = boxes[boxes["patientId"].isin(tr)][["x", "y", "width", "height"]].to_numpy()
    fields = {k: lung_field(trb, q) for k, q in FIELDS.items()}
    inside = lambda b, f: ((b[:, 0] >= f[0]) & (b[:, 1] >= f[1]) & (b[:, 0] + b[:, 2] <= f[2]) & (b[:, 1] + b[:, 3] <= f[3]))
    cover = {k: float(inside(trb, f).mean()) for k, f in fields.items()}
    v = meta[meta["split"] == "val"]
    ids = v["patientId"].tolist()
    m = v.set_index("patientId").loc[ids]
    target = m["target"].to_numpy()
    gt = load_gt(paths.BOXES, ids)
    clean_imgs = val_images(ids)
    masked = {k: perturb(clean_imgs, "mask", f) for k, f in fields.items()}
    conds = ["clean"] + list(fields)
    res = {}
    for r in RUNS:
        spec = variant_spec(r)
        pr = {}
        def run_on(imgs):
            pr.setdefault("p", Predictor(r))
            raw_df, img_df = pr["p"].predict(imgs, ids)
            return score_condition(raw_df, img_df, spec, gt, ids, target)
        res[(r, "clean")] = cached(r, "clean", ["clean", None], lambda: run_on(clean_imgs))
        for k, f in fields.items():
            res[(r, k)] = cached(r, f"mask_{k}", ["mask", [round(v, 1) for v in f]], lambda: run_on(masked[k]))
        print(f"[shortcut] {r}: " + ", ".join(f"{c} mAP {res[(r, c)]['map']:.4f}" for c in conds), flush=True)
    tabs = {c: [condition_table(res[(r, c)], ids, target) for r in RUNS] for c in conds}
    for c in tabs:
        for t in tabs[c]:
            t["view"] = m["view"].to_numpy()
            t["cls"] = m["cls"].to_numpy()
            t["nih_patient"] = m["nih_patient"].to_numpy()
    view, cls = m["view"].to_numpy(), m["cls"].to_numpy()
    neg = target == 0

    # 1. class-controlled view bias (clean)
    bias_rows = []
    for c, short in CLS.items():
        for cond in conds:
            aucs, meds = [], []
            for t in tabs[cond]:
                sel = (t["cls"] == c).to_numpy()
                aucs.append(roc_auc_score(t.loc[sel, "view"] == "AP", t.loc[sel, "cls_prob"]))
                meds.append([float(t.loc[sel & (view == vv), "cls_prob"].median()) for vv in ("AP", "PA")])
            fa = masked_metric(tabs[cond], neg & (cls == c) & (view == "AP"), "fp_rate")
            fp = masked_metric(tabs[cond], neg & (cls == c) & (view == "PA"), "fp_rate")
            bias_rows.append({"cls": short, "cond": cond, "n_ap": int((neg & (cls == c) & (view == "AP")).sum()),
                              "n_pa": int((neg & (cls == c) & (view == "PA")).sum()), "auc_view": float(np.mean(aucs)),
                              "med_ap": float(np.mean([x[0] for x in meds])), "med_pa": float(np.mean([x[1] for x in meds])),
                              "fp_ap": fa, "fp_pa": fp,
                              "ratio": fa["est"] / fp["est"] if fp["est"] > 0 else np.nan})
    # 2. masking deltas, per view x class (negatives: FP-rate; positives: sensitivity, mAP pos)
    delta_rows = []
    fmtd = lambda d: f"{d['diff']:+.3f} [{d['lo']:+.3f}, {d['hi']:+.3f}]"
    for vv in ("AP", "PA"):
        for c, short in CLS.items():
            msk = neg & (cls == c) & (view == vv)
            delta_rows.append([f"{short} · {vv}", "FP-rate", int(msk.sum())]
                              + [fmtd(paired_unit_diff(tabs[k], tabs["clean"], msk, "fp_rate")) for k in fields])
        for metric, lab in (("sens", "sensitivity"), ("map_pos", "mAP pos")):
            msk = (target == 1) & (view == vv)
            delta_rows.append([f"Opacity · {vv}", lab, int(msk.sum())]
                              + [fmtd(paired_unit_diff(tabs[k], tabs["clean"], msk, metric)) for k in fields])
    d_map = {k: paired_unit_diff(tabs[k], tabs["clean"], np.ones(len(ids), bool), "map") for k in fields}
    # difference-in-differences: does masking lower the AP FP-rate more than the PA one (inside Not Normal)?
    from rsna.hw3 import combo
    nnm = neg & (cls == "No Lung Opacity / Not Normal")
    did = {k: combo([(1.0, tabs[k], nnm & (view == "AP"), "fp_rate"), (-1.0, tabs["clean"], nnm & (view == "AP"), "fp_rate"),
                     (-1.0, tabs[k], nnm & (view == "PA"), "fp_rate"), (1.0, tabs["clean"], nnm & (view == "PA"), "fp_rate")])
           for k in fields}
    nn = {r["cond"]: r for r in bias_rows if r["cls"] == "Not Normal"}
    md = ["# HW3 §2.4 / RQ3: shortcut по проекции AP/PA (Full tuned, v1 val, inference)", "",
          f"_Генерируется `scripts/analyze_hw3_shortcut.py`; сиды 0/1/2, порог и box_scale из HW2, устройство "
          f"{os.environ.get('RSNA_DEVICE')}. Поля (по краям train GT-боксов, px из 1024; доля train-боксов целиком внутри): "
          + "; ".join(f"{k} (q {FIELDS[k]}): x {f[0]:.0f}–{f[2]:.0f}, y {f[1]:.0f}–{f[3]:.0f}, {100 * cover[k]:.1f} %"
                      for k, f in fields.items()) + "._", "",
          "## 1. Смещение по проекции внутри одного класса (чистые и маскированные снимки)", "",
          "AUC(view | P) — насколько cls-вероятность P(пневмония) сама по себе отличает AP от PA внутри класса (0.5 = не отличает).", "",
          md_table(["класс негативов", "вход", "n AP / PA", "AUC(view | P)", "медиана P: AP / PA",
                    "FP-rate AP [CI]", "FP-rate PA [CI]", "AP / PA"],
                   [[r["cls"], r["cond"], f"{r['n_ap']} / {r['n_pa']}", f"{r['auc_view']:.3f}", f"{r['med_ap']:.3f} / {r['med_pa']:.3f}",
                     f"{r['fp_ap']['est']:.3f} [{r['fp_ap']['lo']:.3f}, {r['fp_ap']['hi']:.3f}]",
                     f"{r['fp_pa']['est']:.3f} [{r['fp_pa']['lo']:.3f}, {r['fp_pa']['hi']:.3f}]", f"{r['ratio']:.1f}"]
                    for r in bias_rows]), "",
          "## 2. Маскирование вне поля: Δ = маска − чистые (парный кластерный бутстрап)", "",
          md_table(["группа", "метрика", "n"] + [f"Δ маска {k} [95 % CI]" for k in fields], delta_rows), "",
          *[f"- маска {k}: общий mAP Δ {d_map[k]['diff']:+.4f} [{d_map[k]['lo']:+.4f}, {d_map[k]['hi']:+.4f}]; отношение FP-rate "
            f"AP/PA внутри Not Normal {nn['clean']['ratio']:.1f} → {nn[k]['ratio']:.1f}; DiD (Δ FP-rate AP − Δ FP-rate PA, "
            f"Not Normal) {did[k]['est']:+.3f} [{did[k]['lo']:+.3f}, {did[k]['hi']:+.3f}]" for k in fields], ""]
    (OUT / "shortcut.md").write_text("\n".join(md))
    json.dump({"fields": fields, "cover_train": cover}, open(OUT / "shortcut_meta.json", "w"), indent=2)
    print("\n".join(md))
    fig(tabs, view, cls, neg, clean_imgs, masked, m, fields, bias_rows)


def fig(tabs, view, cls, neg, clean_imgs, masked, m, fields, bias_rows) -> None:
    style()
    fig = plt.figure(figsize=(15, 4.4))
    gs = fig.add_gridspec(1, 5, width_ratios=[1.5, 1.15, 0.55, 0.55, 0.55])
    ax = fig.add_subplot(gs[0])
    groups = [(c, vv) for c in CLS for vv in ("AP", "PA")]
    x = np.arange(len(groups))
    conds = [("clean", SLOTS[0], "clean"), ("frame", SLOTS[2], "mask: frame (pre-registered)"),
             ("tight", SLOTS[1], "mask: tight (post hoc)")]
    w = 0.26
    for j, (cond, col, lab) in enumerate(conds):
        r = [masked_metric(tabs[cond], neg & (cls == c) & (view == vv), "fp_rate") for c, vv in groups]
        e, lo, hi = (np.array([q[k] for q in r]) for k in ("est", "lo", "hi"))
        ax.bar(x + (j - 1) * w, e, width=w * 0.95, color=col, label=lab)
        ax.errorbar(x + (j - 1) * w, e, yerr=[e - lo, hi - e], fmt="none", ecolor=INK, lw=1, capsize=2)
    ax.set_xticks(x, [f"{CLS[c]}\n{vv}" for c, vv in groups])
    ax.set_ylabel("FP-image rate (seed mean, 95 % CI)")
    ax.set_title("FP on negatives by class × view")
    ax.legend(fontsize=7.5)
    ax.grid(axis="x", visible=False)
    ax = fig.add_subplot(gs[1])
    bins = np.linspace(0, 1, 26)
    t0 = tabs["clean"][0]
    for vv, col in (("AP", SLOTS[1]), ("PA", SLOTS[0])):
        for c, ls, lw in (("Normal", "-", 2), ("No Lung Opacity / Not Normal", "--", 1.6)):
            sel = (t0["cls"] == c).to_numpy() & (view == vv)
            ax.hist(t0.loc[sel, "cls_prob"], bins=bins, histtype="step", lw=lw, ls=ls, color=col, density=True,
                    label=f"{CLS[c]} · {vv} (n={sel.sum()})")
    ax.set_yscale("log")
    ax.set_xlabel("cls probability (seed 0, clean)")
    ax.set_ylabel("density (log)")
    ax.set_title("Score of negatives by class and view")
    ax.legend(fontsize=7)
    ex = m.reset_index()
    i = int(np.flatnonzero(((ex["view"] == "AP") & (ex["cls"] == "No Lung Opacity / Not Normal")).to_numpy())[3])
    k = 256 / paths.ORIG_SIZE
    for j, (img, title, f) in enumerate([(clean_imgs[i], "AP example: clean", None), (masked["frame"][i], "mask: frame", fields["frame"]),
                                         (masked["tight"][i], "mask: tight", fields["tight"])]):
        ax = fig.add_subplot(gs[2 + j])
        ax.imshow(img, cmap="gray", vmin=0, vmax=255)
        if f is not None:
            ax.add_patch(Rectangle((f[0] * k, f[1] * k), (f[2] - f[0]) * k, (f[3] - f[1]) * k, fill=False, ec=SLOTS[2],
                                   lw=1.2, ls="--"))
        ax.set_title(title, fontsize=9)
        ax.set_xticks([]), ax.set_yticks([])
        ax.grid(False)
    fig.tight_layout()
    fig.savefig(paths.FIGURES / "hw3_shortcut.png", dpi=130, facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    main()
