"""HW2 error figure + table: where 1 − mAP goes per config, and ROC curves with the operating points (val).

Left: exact additive decomposition of 1 − mAP (README §5.6): negative images with ≥ 1 box (each counts once, whatever
its number of boxes) / missed positives / localization on positives; mean over the seeds of each config.
Right: ROC of the image-level max box score (the score that decides whether an image gets any box; TPR =
sensitivity, FPR = FP-image rate on negatives) for seed 0 of every config, plus the no_gating variant of the cls
models; the dot on each curve is the unit's operating point at its VAL-selected threshold. Differences in the dots mix
a better curve with a move along the curve; the curves separate the two.
Also writes results/hw2_summary/error_decomposition.md: the per-config means and the seed-matched shifts vs B (B on
the same seeds), so §7 of reports/HW2.md cites a generated table.
Run: PYTHONPATH=src .venv/bin/python scripts/plot_hw2_errors.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import roc_curve

from rsna import paths
from rsna.evaluate import load_meta
from rsna.report import CONFIG_LABEL, CONFIG_ORDER, FIXED_COLOR, INK2, SURFACE, style

PARTS = [("loss_fp_neg", "negative images with ≥ 1 box (FP)", "#8a8984"),
         ("loss_missed_pos", "missed positives (no box)", "#eda100"),
         ("loss_loc_pos", "localization on positives", "#6250d6")]
PART_RU = {"loss_fp_neg": "негативы с боксом (FP)", "loss_missed_pos": "пропущенные позитивы",
           "loss_loc_pos": "локализация на позитивах"}


def load(run: Path, variant: str = "") -> dict | None:
    p = run / (f"posthoc/{variant}/" if variant else "") / "val_metrics.json"
    return json.loads(p.read_text()) if p.exists() else None


def max_box(d: Path, ids: list[str]) -> np.ndarray:
    p = pd.read_csv(d / "val_predictions.csv", dtype={"patientId": str})
    return p.groupby("patientId")["score"].max().reindex(ids).fillna(0.0).to_numpy()


def seed_of(r: Path) -> int:
    return int(r.name.rsplit("_s", 1)[1])


def main() -> None:
    runs: dict[str, list[Path]] = {c: sorted(paths.RESULTS.glob(f"{c}_s[0-9]")) for c in CONFIG_ORDER}
    runs = {c: [r for r in rs if (r / "meta.json").exists()] for c, rs in runs.items()}
    runs = {c: rs for c, rs in runs.items() if rs}
    m = {r.name: load(r) for rs in runs.values() for r in rs}
    style()
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [1.1, 1]})

    labels, bottoms = [], np.zeros(len(runs))
    vals = {k: [] for k, _, _ in PARTS}
    for c, rs in runs.items():
        labels.append(f"{CONFIG_LABEL[c]}\n(n={len(rs)})")
        for k, _, _ in PARTS:
            vals[k].append(np.mean([m[r.name]["errors"][k] for r in rs]))
    x = np.arange(len(runs))
    for k, name, col in PARTS:
        v = np.array(vals[k])
        ax.bar(x, v, bottom=bottoms, color=col, width=0.6, edgecolor=SURFACE, linewidth=2, label=name)
        for xi, (b, h) in enumerate(zip(bottoms, v)):
            ax.text(xi, b + h / 2, f"{h:.3f}", ha="center", va="center", fontsize=9, color="white")
        bottoms += v
    for xi, tot in enumerate(bottoms):
        ax.text(xi, tot + 0.01, f"1 − mAP = {tot:.3f}", ha="center", va="bottom", fontsize=9, color=INK2)
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 1.12)
    ax.set_yticks(np.linspace(0, 1, 6))
    ax.set_axisbelow(True)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("contribution to 1 − mAP (val, mean over the config's seeds)")
    ax.set_title("Where the val metric is lost")
    ax.legend(loc="upper center", ncol=3, fontsize=8, frameon=False, bbox_to_anchor=(0.5, 1.0))

    meta = load_meta()
    val = meta[meta["split"] == "val"]
    ids, y = val["patientId"].tolist(), val["target"].to_numpy()
    for c, rs in runs.items():
        r0 = next((r for r in rs if seed_of(r) == 0), None)
        if r0 is None:
            continue
        col = FIXED_COLOR[c]
        gated = (r0 / "posthoc/no_gating/val_predictions.csv").exists()
        units = [(r0, "", "-", CONFIG_LABEL[c] + (" (gated)" if gated else ""))]
        if gated:
            units.append((r0 / "posthoc/no_gating", "no_gating", ":", f"{CONFIG_LABEL[c]} without gating"))
        for d, v, ls, lab in units:
            fpr, tpr, _ = roc_curve(y, max_box(d, ids))
            bx.plot(fpr, tpr, ls=ls, color=col, lw=1.6, label=lab)
            mt = load(r0, v)
            bx.scatter(mt["errors"]["fp_image_rate"], mt["sensitivity"], s=45, color=col, zorder=3,
                       edgecolor=SURFACE, linewidth=1.2, marker="o" if not v else "X")
    bx.set_xlim(0, 0.3)
    bx.set_ylim(0.3, 0.9)
    bx.set_axisbelow(True)
    bx.set_xlabel("FP-image rate on negatives (FPR of the max box score)")
    bx.set_ylabel("sensitivity (TPR: positives with ≥ 1 box)")
    bx.set_title("ROC of the max box score, seed 0 (marker = VAL-selected threshold)")
    bx.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    out = paths.FIGURES / "hw2_error_decomposition.png"
    fig.savefig(out, dpi=130, facecolor=SURFACE)
    plt.close(fig)
    print(f"-> {out}")

    base = {seed_of(r): m[r.name]["errors"] for r in runs.get("baseline", [])}
    rows = ["# Декомпозиция 1 − mAP по конфигам (val)", "",
            "_Генерируется `scripts/plot_hw2_errors.py` из `results/<run>/val_metrics.json` (README §5.6). Слагаемые "
            "в сумме дают 1 − mAP. «Среднее» — по всем сидам конфига; «сдвиг против B» — среднее по сидам конфига "
            "разностей с B того же сида (B: 3 сида, B+aug и B+cls: 0 и 1)._", "",
            "| конфиг | сиды | " + " | ".join(PART_RU[k] for k, _, _ in PARTS) + " | 1 − mAP |", "|---|---|---|---|---|---|"]
    for c, rs in runs.items():
        e = [m[r.name]["errors"] for r in rs]
        parts = [np.mean([q[k] for q in e]) for k, _, _ in PARTS]
        rows.append(f"| {CONFIG_LABEL[c]} | {','.join(str(seed_of(r)) for r in rs)} | "
                    + " | ".join(f"{p:.3f}" for p in parts) + f" | {sum(parts):.3f} |")
    rows += ["", "| сдвиг против B (тот же seed) | сиды | " + " | ".join(PART_RU[k] for k, _, _ in PARTS)
             + " | Δ mAP |", "|---|---|---|---|---|---|"]
    for c, rs in runs.items():
        if c == "baseline":
            continue
        rs = [r for r in rs if seed_of(r) in base]
        d = [[m[r.name]["errors"][k] - base[seed_of(r)][k] for k, _, _ in PARTS] for r in rs]
        mean = np.mean(d, axis=0)
        rows.append(f"| {CONFIG_LABEL[c]} − B | {','.join(str(seed_of(r)) for r in rs)} | "
                    + " | ".join(f"{v:+.3f}" for v in mean) + f" | {-mean.sum():+.4f} |")
    tbl = paths.RESULTS / "hw2_summary" / "error_decomposition.md"
    tbl.parent.mkdir(parents=True, exist_ok=True)
    tbl.write_text("\n".join(rows) + "\n")
    print("\n".join(rows))
    print(f"-> {tbl}")


if __name__ == "__main__":
    main()
