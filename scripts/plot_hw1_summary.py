"""HW1 figure: val mAP with bootstrap 95% CI, trivial baselines vs every finished baseline seed.

Usage (repo root): .venv/bin/python scripts/plot_hw1_summary.py
Reads only results/*/val_metrics.json; writes reports/figures/hw1_val_map_vs_trivial.png.
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RUNS = [  # (label, path, is_model)
    ("empty\n(no boxes)", "results/baseline_trivial/empty/val_metrics.json", False),
    ("prior_boxes\n(2 k-means boxes, all images)", "results/baseline_trivial/prior_boxes/val_metrics.json", False),
    ("prior_boxes_ap\n(2 boxes, AP-view only)", "results/baseline_trivial/prior_boxes_ap/val_metrics.json", False),
]
for p in sorted(ROOT.glob("results/baseline_s[0-9]*/val_metrics.json")):
    RUNS.append((f"{p.parent.name}\n(CenterNet-lite R18)", str(p.relative_to(ROOT)), True))
INK, MUTED, GRID = "#1f1f1f", "#6b6b6b", "#e6e6e6"
C_TRIVIAL, C_MODEL = "#9a9a9a", "#2a78d6"

rows = []
for label, rel, is_model in RUNS:
    d = json.loads((ROOT / rel).read_text())
    assert d["n_images"] == 4002, (rel, d["n_images"])
    rows.append((label, d["map"], d["ci_lo"], d["ci_hi"], d["threshold"], is_model))
    print(f"{rel}: mAP {d['map']:.4f} [{d['ci_lo']:.4f}, {d['ci_hi']:.4f}] thr {d['threshold']}")

fig, ax = plt.subplots(figsize=(8.0, 1.2 + 0.6 * len(RUNS)), dpi=150)
fig.patch.set_facecolor("white")
ys = list(range(len(rows)))[::-1]
for y, (label, m, lo, hi, thr, is_model) in zip(ys, rows):
    ax.barh(y, m, height=0.55, color=C_MODEL if is_model else C_TRIVIAL, zorder=2)
    ax.errorbar(m, y, xerr=[[m - lo], [hi - m]], fmt="none", ecolor=INK, elinewidth=1.2,
                capsize=4, zorder=3)
    ax.text(hi + 0.004, y, f"{m:.3f}  [{lo:.3f}, {hi:.3f}]", va="center", ha="left",
            fontsize=9, color=INK)
ax.set_yticks(ys)
ax.set_yticklabels([r[0] for r in rows], fontsize=9, color=INK)
ax.set_xlim(0, 0.29)
ax.set_xlabel("val RSNA mAP (IoU 0.4–0.75), 4002 images; error bar = bootstrap 95% CI (2000 resamples)",
              fontsize=8.5, color=MUTED)
ax.set_title("Val mAP: trivial baselines vs CenterNet-lite baseline seeds", fontsize=11, color=INK, loc="left")
ax.grid(axis="x", color=GRID, zorder=0)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(MUTED)
ax.tick_params(axis="y", length=0)
ax.tick_params(axis="x", colors=MUTED, labelsize=8.5)
fig.text(0.01, 0.01, "baseline thresholds and checkpoint epochs were selected on this val split, "
         "so their mAP is optimistically biased.", fontsize=7.5, color=MUTED)
fig.tight_layout(rect=(0, 0.04, 1, 1))
out = ROOT / "reports/figures/hw1_val_map_vs_trivial.png"
fig.savefig(out, facecolor="white")
print("wrote", out)
