"""Exploratory data analysis -> reports/figures/eda_*.png + reports/eda_stats.json.

Scope rule: descriptive stats (classes, demographics, prevalence) use all labeled images;
everything that informs modelling (box geometry, centers, example images) uses split==train only.

CLI: python -m rsna.eda
"""
from __future__ import annotations

import json
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

from . import paths  # noqa: E402

# Validated categorical palette (dataviz reference, light mode) + neutral inks.
BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e1"
SEQ = LinearSegmentedColormap.from_list("blue_seq", ["#fcfcfb", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
CLS_ORDER = ["Normal", "No Lung Opacity / Not Normal", "Lung Opacity"]
CLS_RU = {"Normal": "Normal\n(норма)", "No Lung Opacity / Not Normal": "No Lung Opacity /\nNot Normal",
          "Lung Opacity": "Lung Opacity\n(пневмония)"}
CLS_COLOR = {"Normal": AQUA, "No Lung Opacity / Not Normal": GRAY, "Lung Opacity": ORANGE}
AGE_BINS = [0, 18, 40, 60, 80, 101]
AGE_LABELS = ["0-17", "18-39", "40-59", "60-79", "80-100"]
AGE_MAX_VALID = 100

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 130, "savefig.bbox": "tight", "font.size": 10,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "axes.titlecolor": INK, "axes.titlesize": 11,
    "axes.titleweight": "bold", "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
})


def age_bucket(age: pd.Series) -> pd.Series:
    """Age bucket label; ages > 100 (header errors) -> 'invalid'."""
    b = pd.cut(age, AGE_BINS, right=False, labels=AGE_LABELS).astype(object)
    return b.where(age <= AGE_MAX_VALID, "invalid")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p, d = k / n, 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def rate_table(df: pd.DataFrame, by: str) -> dict[str, dict[str, Any]]:
    out = {}
    for key, g in df.groupby(by, observed=True):
        k, n = int(g["target"].sum()), len(g)
        lo, hi = wilson(k, n)
        out[str(key)] = {"n": n, "positives": k, "rate": round(k / n, 4), "ci95": [round(lo, 4), round(hi, 4)]}
    return out


def quantiles(s: pd.Series, digits: int = 1) -> dict[str, float]:
    q = s.quantile([0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
    return {"mean": round(float(s.mean()), digits), "min": round(float(s.min()), digits),
            **{f"p{int(k * 100)}": round(float(v), digits) for k, v in q.items()},
            "max": round(float(s.max()), digits)}


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    meta = pd.read_csv(paths.METADATA, dtype={"nih_patient": str})
    split = pd.read_csv(paths.SPLIT_FILE, usecols=["patientId", "split"])
    meta = meta.merge(split, on="patientId", how="left", validate="one_to_one")
    assert meta["split"].notna().all(), "run python -m rsna.split first"
    boxes = pd.read_csv(paths.BOXES).merge(meta[["patientId", "idx", "split", "view"]], on="patientId")
    boxes["cx"], boxes["cy"] = boxes["x"] + boxes["width"] / 2, boxes["y"] + boxes["height"] / 2
    boxes["area"], boxes["aspect"] = boxes["width"] * boxes["height"], boxes["height"] / boxes["width"]
    return meta, boxes


def save(fig: plt.Figure, name: str) -> str:
    path = paths.FIGURES / f"eda_{name}.png"
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return str(path.relative_to(paths.ROOT))


def bar_labels(ax: plt.Axes, bars, texts: list[str], tops: list[float] | None = None) -> None:
    """Label above each bar (or above `tops`, e.g. the upper CI whisker)."""
    for b, t, top in zip(bars, texts, tops or [b.get_height() for b in bars]):
        ax.annotate(t, (b.get_x() + b.get_width() / 2, top), xytext=(0, 3),
                    textcoords="offset points", ha="center", va="bottom", fontsize=9, color=INK)


# ---------------------------------------------------------------- figures

def fig_classes(meta: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(7, 4))
    counts = meta["cls"].value_counts().reindex(CLS_ORDER)
    bars = ax.bar([CLS_RU[c] for c in CLS_ORDER], counts.values, color=[CLS_COLOR[c] for c in CLS_ORDER], width=0.6)
    bar_labels(ax, bars, [f"{v:,} ({v / len(meta):.1%})".replace(",", " ") for v in counts.values])
    ax.set(title=f"Распределение классов (все размеченные снимки, N={len(meta)})",
           ylabel="Число снимков")
    ax.set_ylim(0, counts.max() * 1.15)
    ax.grid(axis="x", visible=False)
    return save(fig, "class_distribution")


def fig_view_sex(meta: pd.DataFrame) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(9, 4), sharey=True)
    for ax, col, title in [(axes[0], "view", "по проекции снимка"), (axes[1], "sex", "по полу")]:
        rt = rate_table(meta, col)
        keys = sorted(rt)
        rates = [rt[k]["rate"] * 100 for k in keys]
        err = np.array([[rt[k]["rate"] - rt[k]["ci95"][0], rt[k]["ci95"][1] - rt[k]["rate"]] for k in keys]).T * 100
        bars = ax.bar(keys, rates, color=[BLUE, ORANGE][: len(keys)], width=0.55, yerr=err, ecolor=INK2, capsize=4)
        bar_labels(ax, bars, [f"{rt[k]['rate']:.1%}\n{rt[k]['positives']}/{rt[k]['n']}" for k in keys],
                   [rt[k]["ci95"][1] * 100 for k in keys])
        ax.set_title(f"Доля пневмонии {title}")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Доля снимков с Lung Opacity, %")
    axes[0].set_ylim(0, 50)
    fig.suptitle("AP-проекция — сильный неявный признак (риск shortcut learning); 95% ДИ Уилсона",
                 fontsize=9, color=INK2, y=0.01)
    return save(fig, "positive_rate_view_sex")


def fig_age(meta: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(8, 4))
    valid = meta[meta["age"] <= AGE_MAX_VALID]
    bins = np.arange(0, 101, 5)
    for t, color, label in [(0, BLUE, "без пневмонии (target=0)"), (1, ORANGE, "пневмония (target=1)")]:
        a = valid.loc[valid["target"] == t, "age"]
        ax.hist(a, bins=bins, density=True, histtype="step", linewidth=2, color=color, label=f"{label}, n={len(a)}")
    n_bad = int((meta["age"] > AGE_MAX_VALID).sum())
    ax.set(title="Распределение возраста по целевой метке (плотность)", xlabel="Возраст, лет", ylabel="Плотность")
    ax.legend(title=f"исключено возрастов > {AGE_MAX_VALID}: {n_bad}", title_fontsize=8, loc="upper left")
    return save(fig, "age_by_target")


def fig_age_rate(meta: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(7, 4))
    rt = rate_table(meta.assign(age_bucket=age_bucket(meta["age"])).query("age_bucket != 'invalid'"), "age_bucket")
    keys = [k for k in AGE_LABELS if k in rt]
    rates = [rt[k]["rate"] * 100 for k in keys]
    err = np.array([[rt[k]["rate"] - rt[k]["ci95"][0], rt[k]["ci95"][1] - rt[k]["rate"]] for k in keys]).T * 100
    bars = ax.bar(keys, rates, color=BLUE, width=0.6, yerr=err, ecolor=INK2, capsize=4)
    bar_labels(ax, bars, [f"{rt[k]['rate']:.1%}\nn={rt[k]['n']}" for k in keys], [rt[k]["ci95"][1] * 100 for k in keys])
    ax.axhline(meta["target"].mean() * 100, color=INK2, linestyle="--", linewidth=1,
               label=f"в среднем по датасету {meta['target'].mean():.1%}")
    ax.legend(loc="upper right")
    ax.set(title="Доля пневмонии по возрастным группам (95% ДИ)", xlabel="Возрастная группа, лет",
           ylabel="Доля Lung Opacity, %", ylim=(0, 45))
    ax.grid(axis="x", visible=False)
    return save(fig, "age_positive_rate")


def fig_boxes_per_image(meta: pd.DataFrame) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    c = meta["n_boxes"].value_counts().sort_index()
    bars = axes[0].bar(c.index.astype(str), c.values, color=BLUE, width=0.6)
    bar_labels(axes[0], bars, [str(v) for v in c.values])
    axes[0].set(title="Число боксов на снимок (все снимки)", xlabel="Боксов на снимке", ylabel="Число снимков",
                ylim=(0, c.max() * 1.12))
    pos = meta[meta["target"] == 1]
    ct = pd.crosstab(pos["view"], pos["n_boxes"], normalize="index") * 100
    w = 0.38
    for i, (view, color) in enumerate([("AP", BLUE), ("PA", ORANGE)]):
        x = np.arange(len(ct.columns)) + (i - 0.5) * w
        axes[1].bar(x, ct.loc[view].values, width=w - 0.02, color=color, label=f"{view} (n={int((pos['view'] == view).sum())})")
    axes[1].set_xticks(np.arange(len(ct.columns)), ct.columns.astype(str))
    axes[1].set(title="Позитивные снимки: боксов по проекции", xlabel="Боксов на снимке",
                ylabel="Доля позитивных снимков, %")
    axes[1].legend()
    for ax in axes:
        ax.grid(axis="x", visible=False)
    return save(fig, "boxes_per_image")


def fig_box_sizes(tb: pd.DataFrame) -> str:
    fig, axes = plt.subplots(2, 2, figsize=(10, 7.5))
    specs = [(axes[0, 0], "width", "Ширина бокса, px (из 1024)", np.arange(0, 600, 15)),
             (axes[0, 1], "height", "Высота бокса, px (из 1024)", np.arange(0, 1000, 20)),
             (axes[1, 0], "sqrt_area", "√площади бокса, px", np.arange(0, 800, 15)),
             (axes[1, 1], "aspect", "Отношение сторон h/w", np.arange(0, 5.01, 0.1))]
    tb = tb.assign(sqrt_area=np.sqrt(tb["area"]))
    for ax, col, xlabel, bins in specs:
        ax.hist(tb[col], bins=bins, color=BLUE, edgecolor="white", linewidth=0.5)
        med = tb[col].median()
        ax.axvline(med, color=ORANGE, linewidth=2)
        ax.annotate(f"медиана {med:.2f}" if col == "aspect" else f"медиана {med:.0f}", (med, ax.get_ylim()[1] * 0.92),
                    xytext=(5, 0), textcoords="offset points", fontsize=9, color=INK,
                    bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5})
        ax.set(xlabel=xlabel, ylabel="Число боксов")
    fig.suptitle(f"Геометрия GT-боксов (только train, {len(tb)} боксов)", fontweight="bold", color=INK)
    fig.tight_layout()
    return save(fig, "box_sizes")


def fig_box_centers(tb: pd.DataFrame, n_pos_images: int) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2), layout="constrained")
    h, *_ = np.histogram2d(tb["cy"], tb["cx"], bins=32, range=[[0, 1024], [0, 1024]])
    im = axes[0].imshow(h, extent=[0, 1024, 1024, 0], cmap=SEQ, interpolation="nearest")
    fig.colorbar(im, ax=axes[0], shrink=0.9, label="центров на ячейку 32×32 px")
    axes[0].set_title("Центры боксов (train)")
    cov = np.zeros((128, 128), np.float32)  # share of positive images whose boxes cover each 8x8 cell
    for _, g in tb.groupby("patientId"):
        m = np.zeros_like(cov, dtype=bool)
        for x, y, w, hh in g[["x", "y", "width", "height"]].to_numpy() / 8:
            m[int(y): int(np.ceil(y + hh)), int(x): int(np.ceil(x + w))] = True
        cov += m
    im = axes[1].imshow(cov / n_pos_images * 100, extent=[0, 1024, 1024, 0], cmap=SEQ, interpolation="nearest")
    fig.colorbar(im, ax=axes[1], shrink=0.9, label="% позитивных снимков")
    axes[1].set_title("Покрытие кадра боксами (train)")
    for ax in axes:
        ax.set(xlabel="x, px", ylabel="y, px")
        ax.grid(False)
        ax.axvline(512, color=INK2, linewidth=0.8, linestyle=":")
    fig.supxlabel("Левая половина кадра = правое лёгкое пациента (радиологическая ориентация)", fontsize=9, color=INK2)
    return save(fig, "box_centers")


def fig_examples(meta: pd.DataFrame, boxes: pd.DataFrame, seed: int = 0) -> str:
    """4 Lung Opacity (AP/PA, 1-2+ boxes), 2 'No Lung Opacity / Not Normal', 2 Normal — train only."""
    tr = meta[meta["split"] == "train"]
    rng = np.random.default_rng(seed)
    pick = lambda q: tr.query(q).iloc[rng.integers(len(tr.query(q)))]  # noqa: E731
    rows = [pick("cls == 'Lung Opacity' and view == 'AP' and n_boxes == 2"),
            pick("cls == 'Lung Opacity' and view == 'AP' and n_boxes == 1"),
            pick("cls == 'Lung Opacity' and view == 'PA' and n_boxes == 2"),
            pick("cls == 'Lung Opacity' and view == 'PA' and n_boxes == 1"),
            pick("cls == 'No Lung Opacity / Not Normal' and view == 'AP'"),
            pick("cls == 'No Lung Opacity / Not Normal' and view == 'PA'"),
            pick("cls == 'Normal' and view == 'AP'"), pick("cls == 'Normal' and view == 'PA'")]
    cache = np.load(paths.image_cache(384), mmap_mode="r")
    s = 384 / paths.ORIG_SIZE
    fig, axes = plt.subplots(2, 4, figsize=(14, 8.2))
    for ax, r in zip(axes.flat, rows):
        ax.imshow(cache[int(r["idx"])], cmap="gray", vmin=0, vmax=255)
        for x, y, w, h in boxes.loc[boxes["patientId"] == r["patientId"], ["x", "y", "width", "height"]].to_numpy() * s:
            ax.add_patch(Rectangle((x, y), w, h, fill=False, edgecolor=ORANGE, linewidth=2))
        ax.set_title(f"{r['cls']}\n{r['view']}, {r['sex']}, {r['age']} лет, боксов: {r['n_boxes']}", fontsize=9,
                     fontweight="normal")
        ax.set_axis_off()
    fig.suptitle("Примеры снимков train с GT-боксами (кэш 384 px)", fontweight="bold", color=INK)
    fig.tight_layout()
    return save(fig, "examples")


# ---------------------------------------------------------------- stats

def exact_duplicates(meta: pd.DataFrame) -> dict[str, Any]:
    """Exact pixel duplicates in the 256 cache (hash per row); reports cross-split pairs."""
    cache = np.load(paths.image_cache(256), mmap_mode="r")
    h = pd.Series([hash(cache[i].tobytes()) for i in range(len(cache))], index=meta.index)
    dup = meta[h.duplicated(keep=False)].assign(h=h)
    groups = dup.groupby("h")
    return {"n_images_in_duplicate_groups": len(dup), "n_groups": groups.ngroups,
            "groups_crossing_splits": int((groups["split"].nunique() > 1).sum()),
            "groups_with_label_conflict": int((groups["target"].nunique() > 1).sum()),
            "groups_within_one_nih_patient": int((groups["nih_patient"].nunique() == 1).sum()) if "nih_patient" in dup else None,
            "patientIds": sorted(dup["patientId"].tolist())}


def compute_stats(meta: pd.DataFrame, boxes: pd.DataFrame, figures: list[str]) -> dict[str, Any]:
    tr = meta[meta["split"] == "train"]
    tb = boxes[boxes["split"] == "train"]
    pos_tr = tr[tr["target"] == 1]
    ages = meta["age"]
    view_auc = roc_auc_score(tr["target"], (tr["view"] == "AP").astype(int))
    rv = rate_table(meta, "view")
    nih = {}
    if "nih_patient" in meta.columns:
        per = meta.groupby("nih_patient")
        size = per.size()
        nih = {"n_nih_patients": int(per.ngroups), "images_per_patient": quantiles(size.astype(float)),
               "patients_with_gt1_image": int((size > 1).sum()),
               "share_images_from_multi_image_patients": round(float(size[size > 1].sum() / len(meta)), 4),
               "patients_with_mixed_target": int((per["target"].nunique() > 1).sum()),
               "note": "split is grouped by nih_patient: all images of one person are in one split"}
    to_input = {f"{c}_in_{S}px_input": quantiles(tb[c] * S / paths.ORIG_SIZE) for S in (256, 384) for c in ("width", "height")}
    return {
        "scope": "dataset_* = all 26684 labeled images (descriptive); train_* = split==train only (informs modelling)",
        "figures": figures,
        "dataset": {
            "n_images": len(meta), "n_positive": int(meta["target"].sum()),
            "prevalence": round(float(meta["target"].mean()), 4),
            "class_counts": meta["cls"].value_counts().to_dict(),
            "n_boxes_counts": {str(k): int(v) for k, v in meta["n_boxes"].value_counts().sort_index().items()},
            "n_boxes_total": int(meta["n_boxes"].sum()),
            "view_counts": meta["view"].value_counts().to_dict(), "sex_counts": meta["sex"].value_counts().to_dict(),
            "age": {**quantiles(ages[ages <= AGE_MAX_VALID].astype(float)), "n_over_100": int((ages > AGE_MAX_VALID).sum()),
                    "values_over_100": sorted(ages[ages > AGE_MAX_VALID].astype(int).tolist())},
            "pixel_spacing_range": [float(meta["pixel_spacing"].min()), float(meta["pixel_spacing"].max())],
            "image_size": sorted({f"{h}x{w}" for h, w in zip(meta["height"], meta["width"])}),
        },
        "dataset_positive_rate_by_view": rv,
        "dataset_positive_rate_by_sex": rate_table(meta, "sex"),
        "dataset_positive_rate_by_age_bucket": rate_table(meta.assign(b=age_bucket(ages)), "b"),
        "dataset_class_by_view_pct": (pd.crosstab(meta["view"], meta["cls"], normalize="index") * 100).round(2).to_dict("index"),
        "view_shortcut": {
            "ap_over_pa_rate_ratio": round(rv["AP"]["rate"] / rv["PA"]["rate"], 2),
            "train_roc_auc_view_only": round(float(view_auc), 4),
            "train_positive_rate_by_view": rate_table(tr, "view"),
            "note": "AP (bedside, sicker patients) has ~4x the prevalence of PA; a model can exploit view without "
                    "looking at the lungs. Use view only for stratification and per-slice metrics, not as a feature.",
        },
        "nih_patients": nih,
        "split_sizes": {s: {"n": int((meta["split"] == s).sum()), "prevalence": round(float(meta.loc[meta["split"] == s, "target"].mean()), 4)}
                        for s in ("train", "val", "test")},
        "train_boxes": {
            "n_boxes": len(tb), "n_positive_images": len(pos_tr),
            "boxes_per_positive_image": {str(k): int(v) for k, v in pos_tr["n_boxes"].value_counts().sort_index().items()},
            "width": quantiles(tb["width"]), "height": quantiles(tb["height"]),
            "sqrt_area": quantiles(np.sqrt(tb["area"])), "aspect_h_over_w": quantiles(tb["aspect"], 2),
            "center_x": quantiles(tb["cx"]), "center_y": quantiles(tb["cy"]),
            "share_centers_left_half_image": round(float((tb["cx"] < 512).mean()), 4),
            "median_wh_by_view": tb.groupby("view")[["width", "height"]].median().round(1).to_dict("index"),
            **to_input,
        },
        "exact_duplicate_images": exact_duplicates(meta),
        "label_noise_notes": [
            "Train boxes were drawn by a single radiologist per image (Shih et al. 2019); the Kaggle test was read by "
            "three and merged by intersection, so official test boxes are smaller. Our val/test come from the "
            "single-read train pool: no train/test reader shift internally, but the labels are themselves noisy.",
            "About 2,500 triple-read images (stage-1 test + 1,500 others) are mixed into stage-2 train and cannot be identified.",
            "'No Lung Opacity / Not Normal' (other abnormalities) is target=0: hard negatives that look abnormal; "
            "boxes exist only for 'Lung Opacity'.",
            "Box extents are subjective (opacity boundaries are diffuse): L1-trained boxes tend to be too large; "
            "top Kaggle teams shrank predicted boxes by ~12-17%.",
            "stage_2_detailed_class_info.csv has 3,543 duplicate rows (removed); no conflicting class/target labels.",
            f"PatientAge has {int((ages > AGE_MAX_VALID).sum())} values > 100 (header errors); kept raw in metadata, "
            "bucketed as 'invalid' here.",
            "Source NIH labels (orig_labels / subset_init_label in the mapping JSON) are NLP-mined and must not be used as features.",
        ],
    }


def main() -> None:
    paths.FIGURES.mkdir(parents=True, exist_ok=True)
    meta, boxes = load()
    tb = boxes[boxes["split"] == "train"]
    n_pos_tr = int(((meta["split"] == "train") & (meta["target"] == 1)).sum())
    figures = [fig_classes(meta), fig_view_sex(meta), fig_age(meta), fig_age_rate(meta), fig_boxes_per_image(meta),
               fig_box_sizes(tb), fig_box_centers(tb, n_pos_tr), fig_examples(meta, boxes)]
    stats = compute_stats(meta, boxes, figures)
    out = paths.REPORTS / "eda_stats.json"
    out.write_text(json.dumps(stats, indent=2, ensure_ascii=False, default=int))
    print("\n".join(figures + [str(out.relative_to(paths.ROOT))]))
    d, v = stats["dataset"], stats["view_shortcut"]
    print(f"N={d['n_images']} prevalence={d['prevalence']:.3f} AP/PA rate ratio={v['ap_over_pa_rate_ratio']} "
          f"view-only AUC(train)={v['train_roc_auc_view_only']} dup={stats['exact_duplicate_images']}")


if __name__ == "__main__":
    main()
