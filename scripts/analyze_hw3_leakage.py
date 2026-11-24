"""HW3 §4.4 / RQ2 of HW1: how much does patient leakage inflate the val estimate? Controlled experiment, val only.

Design (rsna.split_variants.leaky_split): a random half of the multi-image v1-val NIH patients donate floor(k/2) of
their images to train ("leaked" patients; their remaining val images = leaked_eval); the other half keep all images in
val (clean_multi, the control). Train size equals v1 (as many random train images are dropped). The leaky model
(hw3_leak_s{0,1}, configs/hw2/full.yaml) and the v1 model of the same seed (full_s{0,1}) are scored on the SAME images.
Effect = difference-in-differences: [mAP_leak − mAP_v1](leaked_eval) − [mAP_leak − mAP_v1](clean_multi);
the control absorbs everything that changes between the two trainings except the patient overlap. Seed mean; paired
cluster bootstrap over NIH patients (all four terms resampled jointly). Variant `tuned` (each model's own val
selection), plus the same for sensitivity, FP-rate and mAP on positives.
Mechanism: leaked_eval split by whether the image's label (positive / negative) equals its donated siblings' majority
label. Patient-level memorization predicts a gain where it agrees and no gain (or a loss) where it does not.
Outputs: results/hw3/leakage.md, leakage.csv, reports/figures/hw3_leakage.png.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from rsna import paths
from rsna.hw3 import combo, load_units, md_table
from rsna.report import INK2, SLOTS, SURFACE, style

ROLES = paths.SPLITS / "hw3" / "leak_s0_roles.csv"
SEEDS = [0, 1]
NAIVE_LEAK_SHARE = 0.674  # README §3.7: share of val images with a same-patient image in train under a patientId split
N_BOOT = 2000


def did(leak: list[pd.DataFrame], ref: list[pd.DataFrame], m_a: np.ndarray, m_b: np.ndarray, metric: str,
        pi: float) -> dict:
    """[metric(leak) − metric(ref)] on A minus the same on B; seed means; one joint cluster bootstrap (hw3.combo)."""
    return combo([(1.0, leak, m_a, metric), (-1.0, ref, m_a, metric), (-1.0, leak, m_b, metric), (1.0, ref, m_b, metric)],
                 N_BOOT, pi)


def simple(tabs: list[pd.DataFrame], mask: np.ndarray, metric: str, pi: float) -> float:
    return combo([(1.0, tabs, mask, metric)], 1, pi)["est"]


def main() -> None:
    out = paths.RESULTS / "hw3"
    out.mkdir(parents=True, exist_ok=True)
    seeds = [s for s in SEEDS if (paths.RESULTS / f"hw3_leak_s{s}" / "posthoc" / "tuned" / "val_metrics.json").exists()]
    if not seeds:
        print("no finished hw3_leak_s* run")
        return
    roles = pd.read_csv(ROLES, dtype=str).set_index("patientId")
    leak_u = load_units([f"hw3_leak_s{s}" for s in seeds])
    ref_u = load_units([f"full_s{s}" for s in seeds])
    ids = leak_u[0].ids  # the leak split's val = v1 val minus donors
    assert set(ids) == set(roles.index[roles["role"] != "donor"]), "leak val != v1 val minus donors"
    leak = [u.tab.loc[ids] for u in leak_u]
    ref = [u.tab.loc[ids] for u in ref_u]
    role = roles.loc[ids, "role"].to_numpy()
    target = leak[0]["target"].to_numpy()
    pi = float(target.mean())
    # sibling-label agreement for leaked_eval images
    meta = pd.read_csv(paths.METADATA, usecols=["patientId", "target", "nih_patient"], dtype={"nih_patient": str})
    don = roles[roles["role"] == "donor"].join(meta.set_index("patientId")["target"])
    don_major = don.groupby("nih_patient")["target"].mean()  # share of positive donated images
    nihp = roles.loc[ids, "nih_patient"].to_numpy()
    share = np.array([don_major.get(p, np.nan) for p in nihp])  # share of positive donated siblings
    sib = np.where(share > 0.5, 1, np.where(share < 0.5, 0, -1))  # -1: tie (no sibling majority) or not leaked
    agree = (role == "leaked_eval") & (sib >= 0) & (sib == target)
    disagree = (role == "leaked_eval") & (sib >= 0) & (sib != target)
    tie = (role == "leaked_eval") & (share == 0.5)
    L, C, S1 = role == "leaked_eval", role == "clean_multi", role == "clean_single"
    rows, csv = [], []
    for metric, lab in (("map", "mAP"), ("map_pos", "mAP на позитивах"), ("sens", "sensitivity"), ("fp_rate", "FP-rate")):
        d = did(leak, ref, L, C, metric, pi)
        vals = [simple(t, msk, metric, pi) for t in (leak, ref) for msk in (L, C)]
        rows.append([lab, f"{vals[0]:.4f} / {vals[1]:.4f}", f"{vals[2]:.4f} / {vals[3]:.4f}",
                     f"{vals[0] - vals[2]:+.4f}", f"{vals[1] - vals[3]:+.4f}",
                     f"**{d['est']:+.4f}** [{d['lo']:+.4f}, {d['hi']:+.4f}]"])
        csv.append({"metric": metric, "leak_L": vals[0], "leak_C": vals[1], "ref_L": vals[2], "ref_C": vals[3], **d})
    mech = []
    for name, msk in (("метка совпадает с отданными снимками пациента", agree), ("метка не совпадает", disagree)):
        d = did(leak, ref, msk, C, "map", pi)
        ds = did(leak, ref, msk, C, "std_map", pi)
        mech.append([name, int(msk.sum()), int(target[msk].sum()), f"{d['est']:+.4f} [{d['lo']:+.4f}, {d['hi']:+.4f}]",
                     f"{ds['est']:+.4f} [{ds['lo']:+.4f}, {ds['hi']:+.4f}]"])
        csv.append({"metric": f"map | {name}", **d})
    d_map = csv[0]
    comp = [[n, int(m.sum()), int(target[m].sum()), f"{100 * target[m].mean():.1f} %",
             int(pd.Series(nihp[m]).nunique())] for n, m in (("leaked_eval", L), ("clean_multi", C), ("clean_single", S1))]
    leak_val = [u.tab for u in leak_u]
    overall_leak = np.mean([t["ap"].mean() for t in leak_val])
    overall_ref = np.mean([t.loc[ids, "ap"].mean() for t in [u.tab for u in ref_u]])
    md = ["# HW3 §4.4 / RQ2: контролируемая утечка через пациента (val)", "",
          f"_Генерируется `scripts/analyze_hw3_leakage.py`; сиды {', '.join(map(str, seeds))}; модели `hw3_leak_s*` против "
          "`full_s*` того же сида на одних и тех же снимках; вариант `tuned`; 95 % CI — парный кластерный бутстрап по NIH-пациентам "
          "(все четыре слагаемых DiD ресэмплируются вместе)._", "",
          md_table(["группа снимков val", "снимков", "позитивов", "доля поз.", "пациентов"], comp), "",
          md_table(["метрика", "leak-модель: утёкшие / контроль", "v1-модель: утёкшие / контроль", "Δ утёкшие",
                    "Δ контроль", "DiD [95 % CI]"], rows), "",
          "Механизм: DiD mAP внутри утёкших снимков по совпадению метки снимка с меткой большинства отданных в train "
          f"снимков того же пациента; пациенты без большинства (поровну позитивов и негативов среди отданных: {int(tie.sum())} "
          "снимков) исключены. std-mAP — mAP при общей доле позитивов val, т. к. подгруппы сильно различаются по ней:", "",
          md_table(["утёкшие снимки", "n", "позитивов", "DiD mAP [95 % CI]", "DiD std-mAP [95 % CI]"], mech), "",
          f"Пересчёт на наивный сплит по `patientId` (там у {100 * NAIVE_LEAK_SHARE:.1f} % val-снимков пациент есть в train): "
          f"ожидаемое завышение val mAP ≈ {NAIVE_LEAK_SHARE:.3f} × DiD = {NAIVE_LEAK_SHARE * d_map['est']:+.4f} "
          f"[{NAIVE_LEAK_SHARE * d_map['lo']:+.4f}, {NAIVE_LEAK_SHARE * d_map['hi']:+.4f}] (грубо: «доза» утечки в наивном "
          "сплите другая).", "",
          f"Справочно, mAP на всей val leak-сплита: leak-модель {overall_leak:.4f}, v1-модель {overall_ref:.4f} (на тех же снимках).", ""]
    (out / "leakage.md").write_text("\n".join(md))
    pd.DataFrame(csv).to_csv(out / "leakage.csv", index=False, float_format="%.5f")
    print("\n".join(md))
    fig(leak, ref, L, C, agree, disagree, pi)


def fig(leak, ref, L, C, agree, disagree, pi) -> None:
    style()
    fig, axs = plt.subplots(1, 2, figsize=(11, 4), gridspec_kw={"width_ratios": [1.1, 1]})
    ax = axs[0]
    groups = [("leaked\n(patient in train)", L), ("control\n(multi-image, clean)", C)]
    x = np.arange(len(groups))
    for j, (tabs, lab, col) in enumerate(((ref, "v1 model (grouped split)", SLOTS[0]), (leak, "leaky model", SLOTS[1]))):
        v = [simple(tabs, m, "map", pi) for _, m in groups]
        ax.bar(x + (j - 0.5) * 0.36, v, width=0.34, color=col, label=lab)
        for xi, vv in zip(x, v):
            ax.text(xi + (j - 0.5) * 0.36, vv + 0.004, f"{vv:.3f}", ha="center", fontsize=8)
    ax.set_xticks(x, [g[0] for g in groups])
    ax.set_ylabel("val RSNA mAP (seed mean)")
    ax.set_title("Same val images, two trainings")
    ax.set_ylim(0, 0.3)
    ax.legend(fontsize=8, loc="upper center", ncol=2, frameon=False)
    ax.grid(axis="x", visible=False)
    ax = axs[1]
    rows = [("all leaked", L), ("label = siblings'", agree), ("label ≠ siblings'", disagree)]
    for i, (name, m) in enumerate(rows):
        d = did(leak, ref, m, C, "map", pi)
        ax.errorbar(d["est"], -i, xerr=[[d["est"] - d["lo"]], [d["hi"] - d["est"]]], fmt="o", color=SLOTS[1] if i else SLOTS[0],
                    capsize=3, ms=6)
        ax.text(d["hi"] + 0.002, -i, f"{d['est'] + 0:+.3f}".replace("-0.000", "0.000"), va="center", fontsize=8)
    ax.axvline(0, color=INK2, lw=1)
    ax.set_ylim(-len(rows) + 0.5, 0.5)
    ax.set_yticks([-i for i in range(len(rows))], [r[0] for r in rows])
    ax.set_xlabel("difference-in-differences of mAP vs control (95 % CI)")
    ax.set_title("Leakage effect")
    fig.tight_layout()
    fig.savefig(paths.FIGURES / "hw3_leakage.png", dpi=130, facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    main()
