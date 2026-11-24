"""HW3 §3.1 (R1, train size) and §3.2 (R2, re-split) of the chosen solution (Full, configs/hw2/full.yaml unchanged).

R1: hw3_frac{50,20,10}_s{0,1} vs full_s{0,1} (100 %), all on the SAME v1 val images; Δ vs 100 % is seed-matched and
    pooled over the seeds with a paired cluster bootstrap (NIH patients). Per fraction: mAP of the primary variant
    `tuned` (box_scale tuned on val, as in HW2) and as trained, AUC, FP-rate, sensitivity, the 1 − mAP decomposition.
R2: hw3_resplit{1,2,3}_s0 (non-test pool re-cut with the v1 protocol) vs full_s0 on split_v1; every run on its OWN val.
    The spread of val mAP over the 4 splits is compared with the spread expected from val sampling + training noise:
    sqrt(SE_boot^2 + sd_seed^2) (SE_boot from full_s0's cluster-bootstrap CI, sd_seed of Full s0-s2 on v1);
    chi-square test of the variance ratio (3 df).
Missing runs are skipped (partial results are fine). Val only.
Outputs: results/hw3/robustness.md, robustness.csv, reports/figures/hw3_robustness.png.
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd
from scipy.stats import chi2
from sklearn.metrics import roc_auc_score

from rsna import paths
from rsna.analysis import decomposition
from rsna.hw3 import load_units, masked_metric, md_table, paired_unit_diff
from rsna.report import INK, INK2, SLOTS, SURFACE, style

OUT = paths.RESULTS / "hw3"
FRACS = [100, 50, 20, 10]
SEEDS = [0, 1]


def done(run: str, variant: str = "tuned") -> bool:
    return (paths.RESULTS / run / "posthoc" / variant / "val_metrics.json").exists()


def frac_run(p: int, s: int) -> str:
    return f"full_s{s}" if p == 100 else f"hw3_frac{p}_s{s}"


def unit_summary(u) -> dict:
    t = u.tab
    d = decomposition(t)
    pos = t["target"] == 1
    meta = json.loads((paths.RESULTS / u.run / "meta.json").read_text())
    raw = json.loads((paths.RESULTS / u.run / "val_metrics.json").read_text())
    var = json.loads((paths.RESULTS / u.run / "posthoc" / "tuned" / "variant.json").read_text())
    return {"run": u.run, "map": d["map"], "map_as_trained": raw["map"], "auc": roc_auc_score(t["target"], t["cls_prob"]),
            "fp_rate": float(t.loc[~pos, "has_box"].mean()), "sens": float(t.loc[pos, "has_box"].mean()),
            "map_pos": float(t.loc[pos, "ap"].mean()), "loss_fp": d["loss_fp_neg"], "loss_missed": d["loss_missed_pos"],
            "loss_loc": d["loss_loc_zero"] + d["loss_loc_partial"], "thr": u.thr, "box_scale": var["box_scale"],
            "best_epoch": meta["best_epoch"], "n_train": meta["n_train"], "n_val": meta["n_val"],
            "train_min": meta["train_min"], "total_steps": meta["total_steps"]}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    md = ["# HW3 §3.1–3.2: устойчивость к размеру train и к разбиению (Full, тот же конфиг)", "",
          "_Генерируется `scripts/analyze_hw3_robustness.py`. Основная метрика — val mAP варианта `tuned` (как в HW2: "
          "`box_scale` и порог выбраны на val самого прогона); в скобках — как обучен (box_scale 1.0). CI — кластерный "
          "бутстрап по NIH-пациентам._", ""]
    rows = []
    # ------------------------------------------------------------------ R1
    have = {(p, s): frac_run(p, s) for p in FRACS for s in SEEDS if done(frac_run(p, s))}
    units = {k: u for k, u in zip(have, load_units(list(have.values())))} if have else {}
    r1 = []
    for (p, s), u in units.items():
        su = unit_summary(u)
        r1.append({"check": "R1", "frac": p, "seed": s, **su})
    r1 = pd.DataFrame(r1)
    md += ["## R1. Размер обучающей выборки (val = v1 val, 4 002 снимка; вложенные подвыборки train по пациентам)", ""]
    if len(r1):
        r1rows = []
        for p in FRACS:
            g = r1[r1["frac"] == p]
            if not len(g):
                continue
            seeds = sorted(g["seed"])
            ref = [s for s in seeds if (100, s) in units]
            if p != 100 and ref:
                d = paired_unit_diff([units[(p, s)].tab for s in ref], [units[(100, s)].tab for s in ref],
                                     np.ones(len(units[(100, ref[0])].tab), bool), "map")
                dtxt = f"{d['diff']:+.4f} [{d['lo']:+.4f}, {d['hi']:+.4f}]"
                rows.append({"check": "R1", "cond": f"{p}%", "d_map": d["diff"], "d_lo": d["lo"], "d_hi": d["hi"]})
            else:
                dtxt = "–"
            r1rows.append([f"{p} %", f"{int(g['n_train'].mean())}", ",".join(map(str, seeds)),
                           " / ".join(f"{v:.4f}" for v in g["map"]) + f" (ср. {g['map'].mean():.4f})",
                           f"{g['map_as_trained'].mean():.4f}", dtxt, f"{g['auc'].mean():.4f}", f"{g['fp_rate'].mean():.3f}",
                           f"{g['sens'].mean():.3f}", f"{g['map_pos'].mean():.3f}",
                           f"{g['loss_fp'].mean():.3f} / {g['loss_missed'].mean():.3f} / {g['loss_loc'].mean():.3f}",
                           " / ".join(str(int(e)) for e in g["best_epoch"]), f"{int(g['total_steps'].mean())}"])
        md += [md_table(["train", "снимков", "сиды", "mAP по сидам (tuned)", "mAP как обучен", "Δ к 100 % [95 % CI]",
                         "AUC", "FP-rate", "sens", "mAP pos", "потери FP / пропуски / локализация", "лучшая эпоха",
                         "шагов"], r1rows), "",
               "Δ — парно по сиду (frac s0 против full_s0, s1 против s1) на одних и тех же снимках val, среднее по сидам.", ""]
        m = r1.groupby("frac")["map"].mean()
        if len(m) >= 3:
            x = np.log2(r1.groupby("frac")["n_train"].mean())
            k = np.polyfit(x, m.loc[x.index], 1)
            md += [f"Линейная аппроксимация mAP по log2(числа снимков) на {len(m)} точках: {k[0]:+.4f} mAP на удвоение train "
                   "(описательно; экстраполяция за 100 % — гипотеза, не проверено).", ""]
    else:
        md += ["_Нет завершённых прогонов._", ""]

    # ------------------------------------------------------------------ R2
    r2_runs = [r for r in ["full_s0", "hw3_resplit1_s0", "hw3_resplit2_s0", "hw3_resplit3_s0"] if done(r)]
    r2 = []
    us = load_units(r2_runs) if r2_runs else []
    for u in us:
        ci = masked_metric([u.tab], np.ones(len(u.tab), bool), "map")
        su = unit_summary(u)
        t = u.tab
        r2.append({"check": "R2", "split": "v1" if u.run == "full_s0" else u.run.replace("hw3_", "").replace("_s0", ""),
                   **su, "map_lo": ci["lo"], "map_hi": ci["hi"], "pos_share": float((t["target"] == 1).mean()),
                   "ap_share": float((t["view"] == "AP").mean())})
    r2 = pd.DataFrame(r2)
    md += ["## R2. Другое разбиение (тот же протокол; test не меняется; сид 0; каждый прогон — на своей val)", ""]
    if len(r2):
        seed_sd = float(pd.read_csv(paths.RESULTS / "experiments_summary.csv").set_index("config").loc["full", "val_map_std"])
        v1 = r2[r2["split"] == "v1"]
        se_boot = float((v1["map_hi"].iloc[0] - v1["map_lo"].iloc[0]) / (2 * 1.96)) if len(v1) else np.nan
        expected = float(np.sqrt(se_boot ** 2 + seed_sd ** 2))
        md += [md_table(["разбиение", "val: снимков / доля поз. / доля AP", "mAP tuned [95 % CI]", "как обучен", "AUC",
                         "FP-rate", "sens", "лучшая эпоха", "порог", "box_scale"],
                        [[r.split, f"{r.n_val} / {100 * r.pos_share:.1f} % / {100 * r.ap_share:.1f} %",
                          f"{r.map:.4f} [{r.map_lo:.4f}, {r.map_hi:.4f}]", f"{r.map_as_trained:.4f}", f"{r.auc:.4f}",
                          f"{r.fp_rate:.3f}", f"{r.sens:.3f}", r.best_epoch, f"{r.thr:.2f}", r.box_scale]
                         for r in r2.itertuples()]), ""]
        if len(r2) >= 2:
            sd = float(r2["map"].std(ddof=1))
            n = len(r2)
            stat = (n - 1) * sd ** 2 / expected ** 2
            p_hi = float(chi2.sf(stat, n - 1))
            verdict = "больше" if sd > 2 * expected else "не больше"
            md += [f"Разброс val mAP по {n} разбиениям: std {sd:.4f} (размах {r2['map'].min():.4f}–{r2['map'].max():.4f}). "
                   f"Ожидаемый от выборки val и шума обучения: √(SE²_бутстрап + sd²_сид) = √({se_boot:.4f}² + {seed_sd:.4f}²) "
                   f"= {expected:.4f}. Критерий плана: разброс {verdict} 2 × ожидаемого ({2 * expected:.4f}). "
                   f"Отношение дисперсий {sd ** 2 / expected ** 2:.2f}; χ²({n - 1}) = {stat:.2f}, p(больше ожидаемого) = {p_hi:.2f}.", "",
                   "Оговорки: (1) SE_бутстрап посчитан нестратифицированным бутстрапом, а val новых разбиений "
                   "стратифицированы по классу, числу боксов, проекции и полу, поэтому ожидаемый разброс — оценка сверху и "
                   "тест консервативен; (2) val разных разбиений пересекаются (≈ 24 % снимков общие с v1), точки не вполне "
                   "независимы; (3) на 4 точках std сам по себе неточен.", ""]
            rows.append({"check": "R2", "cond": "std over splits", "d_map": sd, "d_lo": np.nan, "d_hi": np.nan,
                         "expected_sd": expected})
    else:
        md += ["_Нет завершённых прогонов._", ""]
    pd.concat([r1, r2], ignore_index=True).to_csv(OUT / "robustness.csv", index=False, float_format="%.5f")
    (OUT / "robustness.md").write_text("\n".join(md))
    print("\n".join(md))
    if len(r1) or len(r2):
        fig(r1, r2)


def fig(r1: pd.DataFrame, r2: pd.DataFrame) -> None:
    style()
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.4), gridspec_kw={"width_ratios": [1.2, 1, 1]})
    ax = axs[0]
    if len(r1):
        for s, mk in zip(SEEDS, ("o", "s")):
            g = r1[r1["seed"] == s].sort_values("n_train")
            ax.scatter(g["n_train"], g["map"], color=SLOTS[0], marker=mk, s=30, zorder=3, label=f"seed {s}", alpha=0.8)
        mm = r1.groupby("frac").agg(n=("n_train", "mean"), map=("map", "mean"), auc=("auc", "mean")).sort_values("n")
        ax.plot(mm["n"], mm["map"], color=SLOTS[0], lw=2, label="mean (tuned)")
        mt = r1.groupby("frac").agg(n=("n_train", "mean"), m=("map_as_trained", "mean")).sort_values("n")
        ax.plot(mt["n"], mt["m"], color=INK2, lw=1.2, ls="--", label="mean (as trained)")
        for r in mm.itertuples():
            ax.annotate(f"{r.Index}%\n{r.map:.3f}", (r.n, r.map), xytext=(0, 9), textcoords="offset points",
                        ha="center", fontsize=7.5, color=INK)
        ax.set_xscale("log")
        lo, hi = float(r1["map"].min()), float(r1["map"].max())
        ax.set_ylim(lo - 0.006, hi + 0.012)  # room for the labels above the points
        ax.set_xlim(float(r1["n_train"].min()) / 1.25, float(r1["n_train"].max()) * 1.25)
        ns = sorted(set(int(v) for v in mm["n"]))
        ax.set_xticks(ns, [f"{v:,}".replace(",", " ") for v in ns])
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.set_xlabel("train images (log scale)")
        ax.set_ylabel("val RSNA mAP (v1 val)")
        ax.set_title("R1: learning curve of Full (same config, same val)")
        ax.legend(fontsize=7.5, loc="lower right")
        ax = axs[1]
        g = r1.groupby("frac")[["loss_fp", "loss_missed", "loss_loc"]].mean().loc[[f for f in FRACS if f in set(r1["frac"])]]
        bottom = np.zeros(len(g))
        x = np.arange(len(g))
        for c, lab, col in (("loss_fp", "FP on negatives", "#8a8984"), ("loss_missed", "missed positives", SLOTS[3]),
                            ("loss_loc", "localization", SLOTS[0])):
            ax.bar(x, g[c], bottom=bottom, color=col, width=0.6, edgecolor=SURFACE, lw=2, label=lab)
            for xi, (b, h) in enumerate(zip(bottom, g[c])):
                ax.text(xi, b + h / 2, f"{h:.3f}", ha="center", va="center", fontsize=8, color="white")
            bottom += g[c].to_numpy()
        ax.set_xticks(x, [f"{f}%" for f in g.index])
        ax.set_ylim(0, 1)
        ax.grid(axis="x", visible=False)
        ax.set_ylabel("contribution to 1 − mAP")
        ax.set_title("R1: where the mAP is lost, by train size")
        ax.legend(fontsize=7.5, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.27))
    ax = axs[2]
    if len(r2):
        y = np.arange(len(r2))[::-1]
        cols = [SLOTS[0] if s == "v1" else SLOTS[1] for s in r2["split"]]
        ax.hlines(y, r2["map_lo"], r2["map_hi"], color=cols, lw=2)
        ax.scatter(r2["map"], y, color=cols, s=40, zorder=3, edgecolor=SURFACE, lw=1.2)
        ax.set_yticks(y, [f"{s} (val n={n})" for s, n in zip(r2["split"], r2["n_val"])])
        ax.set_xlabel("val mAP (tuned), own val of each split, 95 % CI")
        ax.set_title("R2: Full s0 on 4 random grouped splits")
    fig.tight_layout()
    fig.savefig(paths.FIGURES / "hw3_robustness.png", dpi=130, facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    main()
