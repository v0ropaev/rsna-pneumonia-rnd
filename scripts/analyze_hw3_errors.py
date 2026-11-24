"""HW3 §1 typical errors and §2 slices of the chosen solution: Full (I1 + I2), variant `tuned`, seeds 0/1/2, v1 VAL.

Every number is a seed mean (per seed: the seed's own VAL-selected threshold and box_scale, as in HW2); CIs are 95 %
cluster bootstraps over NIH patients (rsna.hw3). "Persistent" = the same error category for an image in all 3 seeds.
Outputs (results/hw3/): errors.md, slices.md, slices.csv, per_image.csv;
figures (reports/figures/): hw3_errors_overview.png, hw3_confusion.png, hw3_slices.png,
hw3_gallery_{fp,missed,localization,labels}.png.
Run: PYTHONPATH=src .venv/bin/python scripts/analyze_hw3_errors.py   (val only; reads no test file)
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from rsna import paths
from rsna.analysis import CLS_SHORT, box_pairs, decomposition
from rsna.evaluate import val_threshold
from rsna.hw3 import (attach_meta, ci, fmt, gallery, group_diff, group_table, load_units, localization_counterfactuals,
                      masked_metric, md_table, size_cutoffs)
from rsna.metric import load_gt
from rsna.report import GRID, INK, INK2, SLOTS, SURFACE, style

SIZE_RU = {"small": "малые", "medium": "средние", "large": "крупные"}
RUNS = ["full_s0", "full_s1", "full_s2"]
OUT = paths.RESULTS / "hw3"
FIG = paths.FIGURES
CLS_ORDER = ["Normal", "No Lung Opacity / Not Normal", "Lung Opacity"]
SLICES = [("view", ["AP", "PA"]), ("sex", ["F", "M"]), ("age_group", ["<30", "30–60", "≥60"]),
          ("cls", CLS_ORDER), ("n_gt_cap", ["1", "2", "3+"]), ("size", ["small", "medium", "large"]),
          ("nih_group", ["No Finding", "pneumonia-like", "other finding"])]
SLICE_RU = {"view": "проекция", "sex": "пол", "age_group": "возраст", "age_lt18": "возраст", "cls": "класс RSNA",
            "n_gt_cap": "GT-боксов", "size": "размер очага", "nih_group": "NIH-метка"}
CAT_RU = {"fp_neg": "FP на негативе", "missed": "пропуск позитива", "loc_zero": "боксы есть, AP = 0",
          "partial": "0 < AP < 1", "perfect": "AP = 1", "tn": "верный негатив"}


def caption_fn(t: pd.DataFrame):
    def cap(i: str) -> str:
        r = t.loc[i]
        lab = r["nih_labels"].replace("No Finding", "NoFind").replace("Infiltration", "Infiltr").replace("Consolidation", "Consol")
        lab = lab.replace("Atelectasis", "Atelect").replace("Pleural_Thickening", "PlThick").replace("|", ", ")
        lab = lab if len(lab) < 34 else lab[:33] + "…"
        return f"{CLS_SHORT[r['cls']]} · {r['view']} · {r['sex']}{int(r['age'])}\nNIH: {lab}"
    return cap


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    style()
    units = load_units(RUNS, "tuned")
    ids = units[0].ids
    assert all(u.ids == ids for u in units)
    gt = load_gt(paths.BOXES, ids)
    cut = size_cutoffs()
    tabs = []
    for u in units:
        t = attach_meta(u.tab, cut)
        t["n_gt_cap"] = np.where(t["n_gt"] >= 3, "3+", t["n_gt"].astype(str))
        t["neg_cls"] = np.where(t["target"] == 1, "pos", t["cls"])
        u.tab = t
        tabs.append(t)
    t0 = tabs[0]
    pos = (t0["target"] == 1).to_numpy()
    neg = ~pos
    S = len(units)
    md: list[str] = ["# HW3 §1: типовые ошибки Full (tuned), v1 val", "",
                     f"_Генерируется `scripts/analyze_hw3_errors.py`. Прогоны {', '.join(RUNS)} (вариант `tuned`), "
                     f"{len(ids)} снимков val, порог и box_scale каждого сида выбраны на val в HW2. Среднее по сидам; "
                     "95 % CI — кластерный бутстрап по NIH-пациентам (2000 повторов, общий для сидов)._", ""]

    # ------------------------------------------------------------------ 1. decomposition and persistence
    dec = [decomposition(t) for t in tabs]
    cats = np.array([t["category"].to_numpy() for t in tabs])  # [S, N]
    rows = []
    for c in ["fp_neg", "missed", "loc_zero", "partial", "perfect", "tn"]:
        n = [int((cats[s] == c).sum()) for s in range(S)]
        allc = int((cats == c).all(0).sum())
        anyc = int((cats == c).any(0).sum())
        loss = {"fp_neg": "loss_fp_neg", "missed": "loss_missed_pos", "loc_zero": "loss_loc_zero",
                "partial": "loss_loc_partial"}.get(c)
        share = [d[loss] / (1 - d["map"]) for d in dec] if loss else None
        rows.append([CAT_RU[c], f"{np.mean(n):.0f} ({min(n)}–{max(n)})", allc, anyc,
                     f"{np.mean([d[loss] for d in dec]):.3f}" if loss else "–",
                     f"{100 * np.mean(share):.1f} %" if share else "–"])
    maps = [d["map"] for d in dec]
    md += ["## 1. Где теряется mAP и насколько ошибки повторяются по сидам", "",
           f"mAP по сидам: {', '.join(f'{m:.4f}' for m in maps)} (среднее {np.mean(maps):.4f}); пороги "
           f"{', '.join(f'{u.thr:.2f}' for u in units)}.", "",
           md_table(["категория снимка", "снимков (мин–макс по сидам)", "во всех 3 сидах", "хотя бы в 1",
                     "потеря mAP", "доля разрыва 1 − mAP"], rows), "",
           "«Во всех 3 сидах» / «хотя бы в 1» — мера систематичности: если отношение близко к 1, ошибка "
           "определяется снимком, а не случайностью обучения.", ""]

    # ------------------------------------------------------------------ 2. E1: FP on negatives by RSNA class and NIH label
    fp_cls = {c: masked_metric(tabs, neg & (t0["cls"] == c).to_numpy(), "fp_rate") for c in CLS_ORDER[:2]}
    nihl = t0["nih_labels"].str.split("|")
    labels = sorted({l for ls in nihl for l in ls})
    lab_rows = []
    for l in labels:
        has = nihl.apply(lambda ls: l in ls).to_numpy()
        for c in CLS_ORDER[:2]:
            m = neg & has & (t0["cls"] == c).to_numpy()
            if m.sum() >= 25:
                r = masked_metric(tabs, m, "fp_rate")
                lab_rows.append({"label": l, "cls": c, **r})
    lab = pd.DataFrame(lab_rows).sort_values(["cls", "est"], ascending=[True, False])
    fp_any = np.array([t["category"].to_numpy() == "fp_neg" for t in tabs])
    fp_all = fp_any.all(0)
    conf = np.mean([t["max_kept"].to_numpy() for t in tabs], 0)
    # confident persistent FPs: in all seeds, top quartile of the mean kept score among them
    q = np.quantile(conf[fp_all], 0.75) if fp_all.any() else np.inf
    conf_fp = fp_all & (conf >= q)
    base_pl = float((t0.loc[neg, "nih_group"] == "pneumonia-like").mean())
    conf_pl = float((t0.loc[conf_fp, "nih_group"] == "pneumonia-like").mean()) if conf_fp.any() else np.nan
    gate = [t.loc[t["category"] == "fp_neg", "cls_prob"].median() for t in tabs]
    nn = (t0["cls"] == CLS_ORDER[1]).to_numpy()
    d_nn = group_diff(tabs, neg & nn, neg & (t0["cls"] == "Normal").to_numpy(), "fp_rate")
    md += ["## 2. E1 — FP на трудных негативах", "",
           md_table(["негативы", "n", "FP-rate (снимков с ≥ 1 боксом)"],
                    [[c, fp_cls[c]["n"], f"{fmt(fp_cls[c]['est'])} [{fmt(fp_cls[c]['lo'])}, {fmt(fp_cls[c]['hi'])}]"]
                     for c in CLS_ORDER[:2]]), "",
           f"Разность Not Normal − Normal: {d_nn['diff']:+.3f} [{d_nn['lo']:+.3f}, {d_nn['hi']:+.3f}]. "
           f"FP-снимков во всех 3 сидах: {int(fp_all.sum())}, из них «Not Normal» "
           f"{int((fp_all & nn).sum())} ({100 * (fp_all & nn).sum() / max(fp_all.sum(), 1):.0f} %). Медиана cls_prob "
           f"на FP-снимках по сидам: {', '.join(f'{g:.2f}' for g in gate)} — классификатор их не отсекает, гейтинг их не "
           "снимает.", "",
           "FP-rate по исходным NIH-меткам (мульти-метка; строки с ≥ 25 негативами, внутри класса RSNA):", "",
           md_table(["NIH-метка", "класс RSNA", "n негативов", "FP-rate [95 % CI]"],
                    [[r.label, CLS_SHORT[r.cls], r.n, f"{fmt(r.est)} [{fmt(r.lo)}, {fmt(r.hi)}]"] for r in lab.itertuples()]), "",
           f"Уверенные систематические FP (во всех сидах, верхняя четверть по score, n = {int(conf_fp.sum())}): доля "
           f"NIH «pneumonia-like» (Pneumonia / Consolidation / Infiltration) {100 * conf_pl:.0f} % против {100 * base_pl:.0f} % "
           "среди всех негативов val.", ""]

    # ------------------------------------------------------------------ 3. E2: missed positives
    ng_thr = [val_threshold(paths.RESULTS / r / "posthoc" / "no_gating") for r in RUNS]
    miss_rows, miss_flags = [], []
    for t, u, thr_ng in zip(tabs, units, ng_thr):
        m = (t["category"] == "missed").to_numpy()
        raw = t["max_box_score"].to_numpy()
        gated = t["max_score"].to_numpy()
        suppressed = m & (raw >= thr_ng)          # the detector alone (no gating, its own val thr) would fire
        near = m & (gated >= 0.5 * u.thr)         # gated score within a factor 2 of the threshold
        located = m & (t["sub_iou"].to_numpy() >= 0.4)  # the best sub-threshold box is in the right place
        miss_flags.append({"m": m, "suppressed": suppressed, "near": near, "located": located})
        miss_rows.append({"n": int(m.sum()), "suppressed": int(suppressed.sum()), "near": int(near.sum()),
                          "located": int(located.sum()), "cls_med": float(np.median(t.loc[m, "cls_prob"])),
                          "cls_med_found": float(np.median(t.loc[pos & ~m, "cls_prob"]))})
    mr = pd.DataFrame(miss_rows)
    miss_all = np.array([f["m"] for f in miss_flags]).all(0)
    supp_all = np.array([f["suppressed"] for f in miss_flags]).all(0)
    sens = {k: group_table(tabs, k, order=v, metrics=("sens", "map_pos")) for k, v in
            [("size", ["small", "medium", "large"]), ("n_gt_cap", ["1", "2", "3+"]), ("view", ["AP", "PA"])]}
    md += ["## 3. E2 — пропущенные позитивы", "",
           md_table(["сид", "пропусков", "детектор без гейтинга нашёл бы (raw ≥ thr no_gating)",
                     "gated score ≥ thr/2", "лучший бокс ниже порога на месте (IoU ≥ 0.4)", "медиана cls_prob: пропуски / найденные"],
                    [[u.run, r.n, f"{r.suppressed} ({100 * r.suppressed / r.n:.0f} %)", f"{r.near} ({100 * r.near / r.n:.0f} %)",
                      f"{r.located} ({100 * r.located / r.n:.0f} %)", f"{r.cls_med:.2f} / {r.cls_med_found:.2f}"]
                     for u, r in zip(units, mr.itertuples())]), "",
           f"Пропущены во всех 3 сидах: {int(miss_all.sum())} позитивов из {int(pos.sum())}; из них у "
           f"{int((miss_all & supp_all).sum())} детектор без гейтинга во всех сидах дал бы бокс.", "",
           "Чувствительность и mAP на позитивах по размеру очага (терцили √площади по train: "
           f"{cut[0]:.0f} / {cut[1]:.0f} px на сетке 1024), числу GT-боксов и проекции:", "",
           md_table(["срез", "группа", "n_pos", "sensitivity [95 % CI]", "mAP pos [95 % CI]"],
                    [[k, r.value, r.n_pos, ci(r._asdict(), "sens"), ci(r._asdict(), "map_pos")]
                     for k, tt in sens.items() for r in tt.itertuples()]), ""]

    # ------------------------------------------------------------------ 4. E3: localization
    loc_rows = []
    cm = np.zeros((3, 4))
    for t, u in zip(tabs, units):
        p = t[(t["target"] == 1) & t["has_box"]]
        pairs = box_pairs(u.pred, gt, p.index.tolist(), u.thr)
        iou = pairs["iou"].to_numpy()
        ng = np.minimum(p["n_gt"].to_numpy(), 3) - 1
        nk = np.minimum(p["n_kept"].to_numpy(), 3)
        np.add.at(cm, (ng, nk), 1)
        loc_rows.append({"n_pos_box": len(p), "iou_lt04": float((iou < 0.4).mean()), "iou_mid": float(((iou >= 0.4) & (iou < 0.75)).mean()),
                         "iou_ge075": float((iou >= 0.75).mean()), "median_iou": float(np.median(iou)),
                         "merged": float(p["merged"].mean()), "split": float(p["split_gt"].mean()),
                         "ap_merged": float(p.loc[p["merged"], "ap"].mean()), "ap_not": float(p.loc[~p["merged"], "ap"].mean()),
                         "more": float((p["n_kept"] > p["n_gt"]).mean()), "fewer": float((p["n_kept"] < p["n_gt"]).mean()),
                         "ap_more": float(p.loc[p["n_kept"] > p["n_gt"], "ap"].mean()),
                         "ap_fewer": float(p.loc[p["n_kept"] < p["n_gt"], "ap"].mean()),
                         "ap_equal": float(p.loc[p["n_kept"] == p["n_gt"], "ap"].mean())})
    for t in tabs:  # positives without a box (the "0" column of the count confusion)
        p = t[t["target"] == 1]
        np.add.at(cm, (np.minimum(p["n_gt"].to_numpy(), 3) - 1, np.zeros(len(p), int)), (p["n_kept"] == 0).to_numpy().astype(float))
    cm /= S
    lr = pd.DataFrame(loc_rows).mean()
    cfs = pd.DataFrame([localization_counterfactuals(u, gt) for u in units])
    loc_loss = np.mean([d["loss_loc_zero"] + d["loss_loc_partial"] for d in dec])
    pairs_all = pd.concat([box_pairs(u.pred, gt, [i for i in t.index if t.loc[i, "target"] == 1], u.thr) for u, t in zip(units, tabs)])
    pairs_bad = pairs_all[pairs_all["iou"] <= 0.4]  # matched (IoU > 0.1) but scored 0 at every metric threshold
    size_all, larger_all = float(np.median(pairs_all["r_side"])), float((pairs_all["r_side"] > 1).mean())
    size_bad, larger_bad = float(np.median(pairs_bad["r_side"])), float((pairs_bad["r_side"] > 1).mean())
    share_bad = len(pairs_bad) / len(pairs_all)
    pairs_all = pairs_all[pairs_all["iou"] > 0.4]
    size_ratio = float(np.median(pairs_all["r_side"]))
    larger = float((pairs_all["r_side"] > 1).mean())
    md += ["## 4. E3 — локализация и число боксов (позитивы с ≥ 1 боксом)", "",
           f"Пары предсказание–GT (жадно по score, IoU > 0.1): IoU < 0.4 (ноль на всех порогах метрики) — "
           f"{100 * lr.iou_lt04:.0f} %, 0.4–0.75 (частичный зачёт) — {100 * lr.iou_mid:.0f} %, ≥ 0.75 (зачёт на всех порогах) — "
           f"{100 * lr.iou_ge075:.0f} %; медиана IoU {lr.median_iou:.3f}.", "",
           md_table(["ситуация на позитиве", "доля снимков", "средний AP"],
                    [["предсказано больше боксов, чем в GT", f"{100 * lr.more:.0f} %", fmt(lr.ap_more)],
                     ["предсказано меньше боксов, чем в GT", f"{100 * lr.fewer:.0f} %", fmt(lr.ap_fewer)],
                     ["столько же боксов", f"{100 * (1 - lr.more - lr.fewer):.0f} %", fmt(lr.ap_equal)],
                     ["один бокс накрывает ≥ 2 GT-бокса («слияние»)", f"{100 * lr.merged:.1f} %", fmt(lr.ap_merged)],
                     ["GT-бокс накрыт ≥ 2 боксами («дробление»)", f"{100 * lr.split:.1f} %", "–"]]), "",
           f"Контрфакты (среднее по сидам; прирост mAP на той же val; вся потеря на локализации {loc_loss:.3f}): "
           f"убрать боксы, не касающиеся ни одного GT (IoU ≤ 0.1; есть на {cfs['n_images_with_far_box'].mean():.0f} позитивах) — "
           f"**{cfs['no_far'].mean():+.3f}**; убрать дубли (касаются GT, уже занятого боксом с большим score; "
           f"{cfs['n_duplicate_boxes'].mean():.0f} боксов) — {cfs['no_dup'].mean():+.3f}; дать каждому сопоставленному боксу "
           f"точные границы его GT — **{cfs['exact_extent'].mean():+.3f}**; всё вместе — {cfs['all'].mean():+.3f}. GT-боксов, "
           f"которых не касается ни один бокс (IoU ≤ 0.1), на позитивах с боксами: {cfs['n_gt_untouched'].mean():.0f}. "
           f"Размер: медиана √(площадь pred / GT) по парам с IoU > 0.4 ×{size_ratio:.3f}, предсказание больше GT в "
           f"{100 * larger:.0f} % пар; по всем парам (IoU > 0.1) ×{size_all:.3f} и {100 * larger_all:.0f} %; по парам с "
           f"IoU 0.1–0.4 ({100 * share_bad:.0f} % пар) ×{size_bad:.3f} и {100 * larger_bad:.0f} %.", "",
           "Лишний бокс на одноочаговых позитивах по терцилям размера: доля снимков с ≥ 2 боксами среди позитивов с "
           "одним GT-боксом и хотя бы одним боксом (среднее по сидам; в скобках — мин–макс по сидам): " + "; ".join(
               f"{SIZE_RU.get(sz, sz)} {100 * np.mean(v):.0f} % ({100 * min(v):.0f}–{100 * max(v):.0f})" for sz, v in (
                   (sz, [float((t[(t["target"] == 1) & (t["n_gt"] == 1) & (t["n_kept"] >= 1) & (t["size"] == sz)]["n_kept"] >= 2).mean())
                         for t in tabs]) for sz in ("small", "medium", "large"))) + ".", "",
           "Матрица «число GT-боксов × число предсказанных» по всем позитивам (среднее по сидам, снимков):", "",
           md_table(["GT \\ pred", "0", "1", "2", "3+"],
                    [[g] + [f"{v:.0f}" for v in cm[i]] for i, g in enumerate(["1", "2", "3+"])]), ""]

    # ------------------------------------------------------------------ 5. E4: label ambiguity (NIH vs RSNA)
    ct = pd.crosstab(t0["nih_group"], t0["cls"]).reindex(columns=CLS_ORDER)
    fp_nih = group_table([t[t["target"] == 0] for t in tabs], "nih_group",
                         order=["No Finding", "pneumonia-like", "other finding"], metrics=("fp_rate",))
    sens_nih = group_table([t[t["target"] == 1] for t in tabs], "nih_group",
                           order=["No Finding", "pneumonia-like", "other finding"], metrics=("sens", "map_pos"))
    miss_nf = float((t0.loc[miss_all, "nih_group"] == "No Finding").mean()) if miss_all.any() else np.nan
    base_nf = float((t0.loc[pos, "nih_group"] == "No Finding").mean())
    md += ["## 5. E4 — неоднозначность разметки: RSNA против исходных NIH-меток", "",
           "NIH-метки извлечены NLP из текстовых заключений (ChestX-ray14), в модели и при отборе не используются; "
           "здесь это независимый, тоже шумный, второй источник мнения о снимке.", "",
           md_table(["NIH-группа \\ RSNA", *[CLS_SHORT[c] for c in CLS_ORDER]],
                    [[g] + [int(v) for v in ct.loc[g]] for g in ct.index]), "",
           md_table(["NIH-группа", "негативов RSNA", "FP-rate [95 % CI]", "позитивов RSNA", "sensitivity [95 % CI]", "mAP pos"],
                    [[a.value, a.n, ci(a._asdict(), "fp_rate"), b.n_pos, ci(b._asdict(), "sens"), ci(b._asdict(), "map_pos")]
                     for a, b in zip(fp_nih.itertuples(), sens_nih.itertuples())]), "",
           f"Систематические пропуски (во всех сидах): NIH «No Finding» у {100 * miss_nf:.0f} % против {100 * base_nf:.0f} % "
           "среди всех позитивов val.", ""]

    # ------------------------------------------------------------------ 6. slices
    sl = [group_table(tabs, k, order=v) for k, v in SLICES]
    t_kids = [t.assign(age_lt18=np.where(t["age"] < 18, "<18", "≥18")) for t in tabs]
    sl.insert(3, group_table(t_kids, "age_lt18", order=["<18"]))
    slices = pd.concat(sl, ignore_index=True)
    slices.to_csv(OUT / "slices.csv", index=False, float_format="%.5f")
    contrasts = []
    def contrast(name: str, col: str, a: str, b: str, metrics: tuple[str, ...], tt: list[pd.DataFrame] = tabs) -> None:
        for m in metrics:
            d = group_diff(tt, (tt[0][col] == a).to_numpy(), (tt[0][col] == b).to_numpy(), m)
            contrasts.append([name, m, f"{d['diff']:+.3f} [{d['lo']:+.3f}, {d['hi']:+.3f}]"])
    contrast("AP − PA", "view", "AP", "PA", ("map", "std_map", "map_pos", "fp_rate", "sens"))
    contrast("≥60 − <30", "age_group", "≥60", "<30", ("map", "std_map", "map_pos", "fp_rate", "sens"))
    contrast("F − M", "sex", "F", "M", ("map", "std_map", "fp_rate", "sens"))
    contrast("small − large", "size", "small", "large", ("map_pos", "sens"))
    contrast("1 − 2 GT-бокса", "n_gt_cap", "1", "2", ("map_pos", "sens"))
    contrast("Not Normal − Normal (негативы)", "neg_cls", "No Lung Opacity / Not Normal", "Normal", ("fp_rate",))
    nn_tabs = [t[t["cls"] == "No Lung Opacity / Not Normal"] for t in tabs]
    contrast("Not Normal: NIH pneumonia-like − No Finding", "nih_group", "pneumonia-like", "No Finding", ("fp_rate",), nn_tabs)
    for v in ("AP", "PA"):  # is the age effect a view effect? (older patients: more PA)
        tv = [t[t["view"] == v] for t in tabs]
        contrast(f"≥60 − <30, только {v}", "age_group", "≥60", "<30", ("map_pos", "sens", "fp_rate"), tv)
    av = pd.crosstab(t0["age_group"], t0["view"], normalize="index").reindex(["<30", "30–60", "≥60"])
    view_by_age = "; ".join(f"{a}: AP {100 * av.loc[a, 'AP']:.0f} %" for a in av.index)
    auc_all = np.mean([roc_auc_score(t["target"], t["cls_prob"]) for t in tabs])
    pi = float(pos.mean())
    srows = []
    for r in slices.itertuples():
        d = r._asdict()
        small = " ⚠" if (r.n_pos and r.n_pos < 50) or r.n < 100 else ""
        srows.append([SLICE_RU[r.slice], f"{r.value}{small}", r.n, r.n_pos, f"{100 * r.prev:.0f} %", ci(d, "map"),
                      ci(d, "std_map"), ci(d, "map_pos"), ci(d, "fp_rate"), ci(d, "sens"), fmt(r.auc)])
    smd = ["# HW3 §2: диагностика по срезам, Full (tuned), v1 val", "",
           f"_Генерируется `scripts/analyze_hw3_errors.py`; среднее по сидам 0/1/2, 95 % CI — кластерный бутстрап по "
           f"NIH-пациентам. std-mAP = π·mAP_pos / (π + (1 − π)·FP-rate) при π = {pi:.3f} (доля позитивов всей val): "
           "внутри группы RSNA mAP ровно равен n_pos·mAP_pos / (n_pos + n_neg·FP-rate), так что std-mAP — mAP, который был "
           "бы у группы при средней доле позитивов. AUC — ROC-AUC cls-вероятности внутри группы. ⚠ — n_pos < 50 или n < 100: "
           "оценка нестабильна._", "",
           md_table(["срез", "группа", "n", "n_pos", "доля поз.", "mAP", "std-mAP", "mAP pos", "FP-rate", "sens", "AUC"], srows), "",
           "## Разности между группами (те же снимки, кластерный бутстрап)", "",
           md_table(["контраст", "метрика", "Δ [95 % CI]"], contrasts), "",
           f"Доля AP по возрастным группам: {view_by_age}. ROC-AUC cls-вероятности на всей val (среднее по сидам): "
           f"{auc_all:.3f}; внутри AP и PA — см. колонку AUC выше.", ""]
    (OUT / "slices.md").write_text("\n".join(smd))
    md += ["## 6. Срезы", "", "См. [`slices.md`](slices.md).", ""]

    # ------------------------------------------------------------------ per-image table
    per = t0[["target", "cls", "view", "sex", "age", "age_group", "nih_labels", "nih_group", "n_gt", "size"]].copy()
    for s, t in enumerate(tabs):
        per[f"cat_s{s}"] = t["category"]
        per[f"ap_s{s}"] = t["ap"].round(4)
        per[f"n_kept_s{s}"] = t["n_kept"]
        per[f"max_kept_s{s}"] = t["max_kept"].round(4)
        per[f"cls_prob_s{s}"] = t["cls_prob"].round(4)
    per.to_csv(OUT / "per_image.csv")
    (OUT / "errors.md").write_text("\n".join(md))
    print("\n".join(md))
    print("\n".join(smd))

    # ------------------------------------------------------------------ figures
    normal_all = masked_metric(tabs, neg & (t0["cls"] == "Normal").to_numpy(), "fp_rate")
    lab_fig = pd.concat([lab[lab["cls"] == "No Lung Opacity / Not Normal"],
                         pd.DataFrame([{"label": "any label", "cls": "Normal", **normal_all}])], ignore_index=True)
    fig_overview(dec, lab_fig, mr, units)
    fig_confusion(tabs, cm)
    fig_slices(slices, pi)
    galleries(units, tabs, gt, fp_all, conf, miss_flags, miss_all)
    json.dump({"maps": maps, "thr": [u.thr for u in units], "size_cutoffs": cut}, open(OUT / "errors_meta.json", "w"), indent=2)


# ----------------------------------------------------------------------------- figures

def fig_overview(dec: list[dict], lab: pd.DataFrame, mr: pd.DataFrame, units) -> None:
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.6), gridspec_kw={"width_ratios": [0.9, 1.5, 1.0]})
    parts = [("loss_fp_neg", "FP on negatives", "#8a8984"), ("loss_missed_pos", "missed positives", SLOTS[3]),
             ("loss_loc_zero", "boxes but AP = 0", SLOTS[6]), ("loss_loc_partial", "0 < AP < 1", SLOTS[0])]
    ax = axs[0]
    bottom = np.zeros(len(dec))
    x = np.arange(len(dec))
    for k, name, col in parts:
        v = np.array([d[k] for d in dec])
        ax.bar(x, v, bottom=bottom, color=col, width=0.6, edgecolor=SURFACE, linewidth=2, label=name)
        for xi, (b, h) in enumerate(zip(bottom, v)):
            if h > 0.03:
                ax.text(xi, b + h / 2, f"{h:.3f}", ha="center", va="center", fontsize=8, color="white")
        bottom += v
    for xi, tot in enumerate(bottom):
        ax.text(xi, tot + 0.012, f"1 − mAP {tot:.3f}", ha="center", fontsize=8, color=INK2)
    ax.set_xticks(x, [u.run for u in units])
    ax.set_ylim(0, 1.0)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("contribution to 1 − mAP (val)")
    ax.set_title("Where Full loses mAP (per seed)")
    ax.legend(fontsize=7.5, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.32))

    ax = axs[1]
    l = lab.sort_values("est")
    y = np.arange(len(l))
    cols = [SLOTS[1] if c == "No Lung Opacity / Not Normal" else SLOTS[0] for c in l["cls"]]
    ax.hlines(y, l["lo"], l["hi"], color=cols, lw=2)
    ax.scatter(l["est"], y, color=cols, s=36, zorder=3, edgecolor=SURFACE, linewidth=1.2)
    ax.set_yticks(y, [f"{r.label} · {CLS_SHORT[r.cls]} (n={r.n})" for r in l.itertuples()], fontsize=7.5)
    ax.set_xlabel("FP-image rate on RSNA negatives (seed mean, 95 % CI)")
    ax.set_title("E1: FP rate by original NIH finding label")
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], color=SLOTS[1], marker="o", lw=2, label="Not Normal negatives"),
                       Line2D([], [], color=SLOTS[0], marker="o", lw=2, label="Normal negatives")], fontsize=7.5, loc="lower right")

    ax = axs[2]
    m = mr.mean()
    vals = [m.suppressed, m.n - m.suppressed]
    names = ["detector would fire;\ngating suppressed it", "detector itself weak"]
    ax.barh([1, 0], [v / m.n for v in vals], color=[SLOTS[2], SLOTS[3]], height=0.55)
    for yy, v in zip([1, 0], vals):
        ax.text(v / m.n + 0.01, yy, f"{v / m.n:.0%} ({v:.0f})", va="center", fontsize=8.5)
    ax.barh([-1], [m.located / m.n], color=SLOTS[6], height=0.55)
    ax.text(m.located / m.n + 0.01, -1, f"{m.located / m.n:.0%}", va="center", fontsize=8.5)
    ax.set_yticks([1, 0, -1], names + ["best sub-thr box\nin place (IoU ≥ 0.4)"], fontsize=8)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel(f"share of missed positives (seed mean, n ≈ {m.n:.0f})")
    ax.set_title("E2: why positives get no box")
    fig.tight_layout()
    fig.savefig(FIG / "hw3_errors_overview.png", dpi=130)
    plt.close(fig)


def fig_confusion(tabs: list[pd.DataFrame], cm: np.ndarray) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.9), gridspec_kw={"width_ratios": [1, 1.25]})
    M = np.zeros((3, 2))
    for t in tabs:
        for i, c in enumerate(CLS_ORDER):
            g = t[t["cls"] == c]
            M[i] += [(~g["has_box"]).sum(), g["has_box"].sum()]
    M /= len(tabs)
    for ax, mat, rows, cols, title in [
        (axs[0], M, [CLS_SHORT[c] for c in CLS_ORDER], ["no box", "≥ 1 box"], "Image level: RSNA class × output"),
        (axs[1], cm, ["1 GT box", "2 GT boxes", "3+ GT boxes"], ["0", "1", "2", "3+"], "Positives: GT boxes × predicted boxes")]:
        frac = mat / mat.sum(1, keepdims=True)
        ax.imshow(frac, cmap="Blues", vmin=0, vmax=1, aspect="auto")
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                ax.text(j, i, f"{frac[i, j]:.0%}\n({mat[i, j]:.0f})", ha="center", va="center", fontsize=8.5,
                        color="white" if frac[i, j] > 0.55 else INK)
        ax.set_xticks(range(len(cols)), cols)
        ax.set_yticks(range(len(rows)), rows)
        ax.grid(False)
        ax.set_title(title + "\n(row %, seed-mean count)", fontsize=9.5)
    axs[1].set_xlabel("predicted boxes ≥ thr")
    fig.tight_layout()
    fig.savefig(FIG / "hw3_confusion.png", dpi=130)
    plt.close(fig)


def fig_slices(slices: pd.DataFrame, pi: float) -> None:
    s = slices[~slices["slice"].isin(["cls"])].copy()
    s = s.iloc[::-1].reset_index(drop=True)
    fig, axs = plt.subplots(1, 3, figsize=(14, 0.32 * len(s) + 1.6), sharey=True)
    y = np.arange(len(s))
    labels = [f"{SLICE_RU[r.slice]}: {r.value}  (n={r.n}, pos={r.n_pos})" for r in s.itertuples()]
    for ax, (m, title, col) in zip(axs, [("std_map", "prevalence-standardized mAP\n(raw mAP: hollow)", SLOTS[0]),
                                         ("sens", "sensitivity (positives with ≥ 1 box)", SLOTS[2]),
                                         ("fp_rate", "FP-image rate (negatives with ≥ 1 box)", SLOTS[1])]):
        v = s[m].to_numpy()
        ok = ~np.isnan(v)
        ax.hlines(y[ok], s.loc[ok, f"{m}_lo"], s.loc[ok, f"{m}_hi"], color=col, lw=2)
        ax.scatter(v[ok], y[ok], color=col, s=34, zorder=3, edgecolor=SURFACE, linewidth=1.2)
        if m == "std_map":
            mv = s["map"].to_numpy()
            ok2 = ~np.isnan(mv)
            ax.scatter(mv[ok2], y[ok2], facecolor="none", edgecolor=INK2, s=30, zorder=3, lw=1.2)
        ax.set_title(title, fontsize=9.5)
        prev = None
        for i, r in enumerate(s.itertuples()):  # separators between slices
            if prev is not None and r.slice != prev:
                ax.axhline(i - 0.5, color=GRID, lw=1.2)
            prev = r.slice
    axs[0].set_yticks(y, labels, fontsize=7.6)
    axs[0].set_xlabel(f"π = {pi:.3f}")
    fig.suptitle("Full (tuned), v1 val: metrics by slice (seed mean, 95 % cluster-bootstrap CI)", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(FIG / "hw3_slices.png", dpi=130)
    plt.close(fig)


def galleries(units, tabs, gt, fp_all, conf, miss_flags, miss_all) -> None:
    u0, t0 = units[0], tabs[0]
    cap = caption_fn(t0)
    order = lambda m, key, asc=False: t0.index[m][np.argsort(key[m] * (1 if asc else -1), kind="stable")].tolist()
    nn = (t0["cls"] == "No Lung Opacity / Not Normal").to_numpy()
    pl = (t0["nih_group"] == "pneumonia-like").to_numpy()
    top = order(fp_all & nn & ~pl, conf)
    gallery([("FP · Not Normal\n(all seeds, top score)", top[:5]), ("FP · Not Normal\n(next by score)", top[5:10])],
            u0, gt, "E1 — systematic FP on negatives (FP in all 3 seeds; boxes of seed 0)", FIG / "hw3_gallery_fp.png", caption=cap)
    supp_all = np.array([f["suppressed"] for f in miss_flags]).all(0)
    weak_all = miss_all & np.array([~f["suppressed"] for f in miss_flags]).all(0)
    side = t0["gt_side"].to_numpy()
    gallery([("missed · gating\nsuppressed (all seeds)", order(miss_all & supp_all, side)),
             ("missed · detector weak\n(all seeds, largest GT)", order(weak_all, side))],
            u0, gt, "E2 — positives without any box in all 3 seeds (boxes of seed 0)", FIG / "hw3_gallery_missed.png",
            caption=cap, show_sub=True)
    ap = np.array([t["ap"].to_numpy() for t in tabs])
    ap_mean = np.nanmean(ap, 0)
    merged = t0["merged"].to_numpy() & (t0["target"] == 1).to_numpy()
    zero = np.array([t["category"].to_numpy() == "loc_zero" for t in tabs]).all(0)
    gallery([("one box over\n2 GT boxes (merge)", order(merged, -np.nan_to_num(ap_mean))),
             ("boxes but AP = 0\n(all seeds)", order(zero, conf))],
            u0, gt, "E3 — localization errors (boxes of seed 0)", FIG / "hw3_gallery_localization.png", caption=cap)
    nf = (t0["nih_group"] == "No Finding").to_numpy()
    gallery([("FP · NIH says\npneumonia-like", order(fp_all & pl, conf)),
             ("missed · NIH says\n'No Finding'", order(miss_all & nf, side))],
            u0, gt, "E4 — label ambiguity: model vs RSNA label, with the independent NIH report label (boxes of seed 0)",
            FIG / "hw3_gallery_labels.png", caption=cap, show_sub=True)


if __name__ == "__main__":
    main()
