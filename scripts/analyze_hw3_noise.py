"""HW3 §3.3 (R3): robustness of Full (tuned) to input perturbations at inference (no retraining), v1 VAL.

Checkpoints runs/full_s{0,1,2}/best.pt; every condition re-predicts the 4 002 val images after rsna.perturb (one
factor, several levels; the same perturbed images for all seeds). Metrics per seed and condition:
  mAP @ fixed thr   the seed's VAL-selected threshold and box_scale from HW2 (deployment view: nothing is re-tuned)
  mAP @ best thr    best threshold for THIS condition (oracle; the gap to the fixed-thr mAP = calibration shift)
  AUC (cls prob), FP-rate and sensitivity at the fixed threshold, median P(pneumonia) on negatives / positives.
Δ vs the clean condition on the same device: seed mean with a paired cluster bootstrap over NIH patients.
Per-condition predictions are cached in results/hw3/noise/cache/ (resumable) together with the device and the condition;
a cache entry is reused only when both match (a change of rsna.perturb itself does NOT invalidate it: delete the cache).
Device: RSNA_DEVICE (default cpu here; the committed cache was made on mps).
Outputs: results/hw3/noise/{noise.md, noise.csv}, reports/figures/hw3_noise.png.
"""
from __future__ import annotations

import json
import os
import time

os.environ.setdefault("RSNA_DEVICE", "cpu")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

from rsna import paths
from rsna.evaluate import load_meta
from rsna.hw3 import (Predictor, condition_table, md_table, paired_unit_diff, score_condition, val_images,
                      variant_spec)
from rsna.metric import load_gt
from rsna.perturb import perturb
from rsna.report import INK2, SLOTS, SURFACE, style

RUNS = ["full_s0", "full_s1", "full_s2"]
CONDITIONS = [("clean", None)] + [("noise", s) for s in (0.01, 0.02, 0.05, 0.10)] + \
             [("blur", s) for s in (0.5, 1.0, 2.0)] + [("lowres", r) for r in (128, 96, 64)] + \
             [("jpeg", q) for q in (50, 20, 10)] + [("contrast", c) for c in (0.7, 0.9, 1.1, 1.3)] + \
             [("gamma", g) for g in (0.7, 0.91, 1.1, 1.4)]
IN_TRAIN_RANGE = {("contrast", 0.9), ("contrast", 1.1), ("gamma", 0.91), ("gamma", 1.1)}  # train: c ∈ [0.9, 1.1], γ ∈ exp(±0.1)
OUT = paths.RESULTS / "hw3" / "noise"
CACHE = OUT / "cache"
FAMILY_RU = {"clean": "чистые", "noise": "гауссов шум σ", "blur": "размытие σ, px", "lowres": "разрешение, px",
             "jpeg": "JPEG quality", "contrast": "контраст ×", "gamma": "гамма"}


def key(fam: str, lvl) -> str:
    return fam if lvl is None else f"{fam}_{lvl}"


def main() -> None:
    torch.set_num_threads(int(os.environ.get("HW3_THREADS", "6")))
    CACHE.mkdir(parents=True, exist_ok=True)
    meta = load_meta()
    ids = meta.loc[meta["split"] == "val", "patientId"].tolist()
    target = meta.set_index("patientId").loc[ids, "target"].to_numpy()
    gt = load_gt(paths.BOXES, ids)
    clean = val_images(ids)
    specs = {r: variant_spec(r) for r in RUNS}
    res: dict[tuple[str, str], dict] = {}
    for r in RUNS:
        pr = None
        for fam, lvl in CONDITIONS:
            k = key(fam, lvl)
            f = CACHE / f"{r}__{k}.npz"
            if f.exists():
                z = np.load(f, allow_pickle=False)
                summ = json.loads(str(z["summary"]))
                if summ.get("device") == os.environ["RSNA_DEVICE"] and summ.get("condition") == [fam, lvl]:
                    res[(r, k)] = {**summ, "ap": z["ap"], "has_box": z["has_box"], "score": z["score"]}
                    continue
            pr = pr or Predictor(r)
            t0 = time.time()
            imgs = perturb(clean, fam, lvl, seed=0)
            raw_df, img_df = pr.predict(imgs, ids)
            out = score_condition(raw_df, img_df, specs[r], gt, ids, target)
            summ = {k2: v for k2, v in out.items() if k2 not in ("ap", "has_box", "score")}
            summ |= {"device": os.environ["RSNA_DEVICE"], "condition": [fam, lvl]}
            np.savez_compressed(f, ap=out["ap"], has_box=out["has_box"], score=out["score"], summary=json.dumps(summ))
            res[(r, k)] = out
            print(f"[noise] {r} {k}: mAP {out['map']:.4f} (best {out['map_best']:.4f} @ {out['thr_best']:.2f}) "
                  f"AUC {out['auc']:.4f} FP {out['fp_rate']:.3f} sens {out['sens']:.3f}  [{time.time() - t0:.0f} s, {pr.device}]",
                  flush=True)

    # stored HW2 val metrics vs the clean re-prediction on this device (sanity: same checkpoints, same decode)
    stored = {r: json.loads((paths.RESULTS / r / "posthoc" / "tuned" / "val_metrics.json").read_text())["map"] for r in RUNS}
    tabs = {k: [condition_table(res[(r, k)], ids, target) for r in RUNS] for k in {key(f, l) for f, l in CONDITIONS}}
    rows, md_rows = [], []
    allm = np.ones(len(ids), bool)
    for fam, lvl in CONDITIONS:
        k = key(fam, lvl)
        per = [res[(r, k)] for r in RUNS]
        row = {"family": fam, "level": lvl, "in_train_range": (fam, lvl) in IN_TRAIN_RANGE}
        for p in per:  # image-level P(pneumonia) (the cls head; AUC uses it): median on negatives / positives
            p["p_neg"] = float(np.median(p["score"][target == 0]))
            p["p_pos"] = float(np.median(p["score"][target == 1]))
        for m in ("map", "map_best", "auc", "fp_rate", "sens", "thr_best", "p_neg", "p_pos"):
            row[m] = float(np.mean([p[m] for p in per]))
            row[f"{m}_sd"] = float(np.std([p[m] for p in per], ddof=1))
        if fam != "clean":
            d = paired_unit_diff(tabs[k], tabs["clean"], allm, "map")
            row.update({"d_map": d["diff"], "d_map_lo": d["lo"], "d_map_hi": d["hi"]})
            row["d_map_best"] = row["map_best"] - rows[0]["map_best"]
            row["d_auc"] = row["auc"] - rows[0]["auc"]
        rows.append(row)
        ci = "–" if fam == "clean" else f"{row['d_map']:+.4f} [{row['d_map_lo']:+.4f}, {row['d_map_hi']:+.4f}]"
        md_rows.append([FAMILY_RU[fam], "–" if lvl is None else f"{lvl}" + (" (в диапазоне обучения)" if row["in_train_range"] else ""),
                        f"{row['map']:.4f} ± {row['map_sd']:.4f}", ci,
                        f"{row['map_best']:.4f}" + ("" if fam == "clean" else f" ({row['d_map_best']:+.4f})"),
                        f"{row['thr_best']:.2f}", f"{row['auc']:.4f}" + ("" if fam == "clean" else f" ({row['d_auc']:+.4f})"),
                        f"{row['fp_rate']:.3f}", f"{row['sens']:.3f}", f"{row['p_neg']:.3f} / {row['p_pos']:.3f}"])
    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "noise.csv", index=False, float_format="%.5f")
    md = ["# HW3 §3.3: устойчивость Full (tuned) к искажениям входа (inference, v1 val)", "",
          f"_Генерируется `scripts/analyze_hw3_noise.py`; чекпойнты {', '.join(RUNS)}, устройство "
          f"{os.environ.get('RSNA_DEVICE')}. Искажение применяется к входу модели (256 px, uint8), одно и то же для всех "
          "сидов. Среднее ± std по сидам; Δ — парный кластерный бутстрап по NIH-пациентам против чистой val того же "
          "прогона. Фиксированный порог — порог сида, выбранный на чистой val в HW2._", "",
          "Проверка воспроизведения: mAP чистой val, сохранённый в HW2 (MPS) / пересчитанный здесь: "
          + ", ".join(f"{r} {stored[r]:.4f} / {res[(r, 'clean')]['map']:.4f}" for r in RUNS) + ".", "",
          md_table(["искажение", "уровень", "mAP @ фикс. порог", "Δ mAP [95 % CI]", "mAP @ лучший порог (Δ)",
                    "лучший порог", "AUC (Δ)", "FP-rate", "sens", "медиана P(пневмония): нег. / поз."], md_rows), "",
          "FP-rate и sens — по боксам при фиксированном пороге; P(пневмония) — выход image-level головы (по нему AUC), "
          "медиана по снимкам, среднее по сидам.", ""]
    (OUT / "noise.md").write_text("\n".join(md))
    print("\n".join(md))
    fig(df)


def fig(df: pd.DataFrame) -> None:
    style()
    fams = [("noise", "Gaussian noise σ (0–1 intensity)", False), ("blur", "Gaussian blur σ, px (256 px input)", False),
            ("lowres", "effective resolution, px", True), ("jpeg", "JPEG quality", True),
            ("contrast", "contrast factor", False), ("gamma", "gamma", False)]
    clean = df[df["family"] == "clean"].iloc[0]
    fig, axs = plt.subplots(2, 3, figsize=(13.5, 7.2), sharey=True)
    for ax, (fam, xl, rev) in zip(axs.ravel(), fams):
        d = df[df["family"] == fam]
        ref = 256 if fam == "lowres" else 100 if fam == "jpeg" else 1.0 if fam in ("contrast", "gamma") else 0.0
        x = np.r_[ref, d["level"].astype(float)]
        order = np.argsort(x)
        x = x[order]
        for m, lab, col, ls in [("map", "mAP @ fixed val thr", SLOTS[0], "-"), ("map_best", "mAP @ best thr (oracle)", SLOTS[1], "--")]:
            ax.plot(x, np.r_[clean[m], d[m]][order], ls=ls, marker="o", ms=5, color=col, label=lab)
        yl = np.r_[clean["map"], clean["map"] + d["d_map_lo"]][order]
        yh = np.r_[clean["map"], clean["map"] + d["d_map_hi"]][order]
        ax.fill_between(x, yl, yh, color=SLOTS[0], alpha=0.15, lw=0)
        if fam in ("contrast", "gamma"):
            lo, hi = (0.9, 1.1) if fam == "contrast" else (np.exp(-0.1), np.exp(0.1))
            ax.axvspan(lo, hi, color=SLOTS[2], alpha=0.12, lw=0)
            ax.text((lo + hi) / 2, 0.02, "train aug\nrange", ha="center", fontsize=7, color=INK2,
                    transform=ax.get_xaxis_transform())
        if rev:
            ax.invert_xaxis()
        ax.set_xlabel(xl)
        ax.set_title(fam)
    for ax in axs[:, 0]:
        ax.set_ylabel("val RSNA mAP (seed mean)")
    axs[0, 0].legend(fontsize=8, loc="lower left")
    axs[0, 0].set_ylim(0, max(0.26, float(df["map_best"].max()) + 0.01))
    fig.suptitle("Full (tuned): val mAP under input perturbations (band = 95 % CI of Δ vs clean, fixed threshold)", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(paths.FIGURES / "hw3_noise.png", dpi=130, facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    main()
