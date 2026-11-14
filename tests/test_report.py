"""Tests for rsna.report (discovery, grouping, paired contrasts, ledger) and rsna.analysis (decomposition, slices)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from rsna import paths
from rsna.analysis import (box_pairs, calibration, decomposition, decomposition_md, greedy_pairs, per_image_table,
                           scale_boxes, slice_table)
from rsna.metric import load_gt, paired_bootstrap_diff, preds_from_df, rsna_map
from rsna.report import (Evaluated, Run, Unit, ablation_rows, build, build_ledger, config_name, contrast_bootstrap,
                         discover, evaluate_unit, factorial_rows, group_by_config, is_smoke, missing_report,
                         posthoc_units, primary_unit, seed_pairs, summary_frame, unit_metrics)

HAS_DATA = paths.METADATA.exists() and paths.SPLIT_FILE.exists() and paths.BOXES.exists()
needs_data = pytest.mark.skipif(not HAS_DATA, reason="processed data / split not available")

G = np.array([[100.0, 100.0, 200.0, 200.0]])
PRED_COLS = ["patientId", "score", "x", "y", "width", "height"]


# ----------------------------------------------------------------------------- fixtures

def _write_run(root: Path, name: str, config_path: str, seed: int, complete: bool = True, smoke: bool = False,
               variants: dict[str, dict] | None = None, box_scale: float = 1.0) -> Path:
    d = root / name
    d.mkdir(parents=True)
    run = {"name": name, "seed": seed, "config_path": config_path, "overrides": [], "max_steps": 5 if smoke else None,
           "limit_train": None, "limit_val": None, "smoke": False}
    mode = "heatmap_x_cls" if "full" in config_path else "heatmap"
    cfg = {"meta": {"hypothesis": "Гипотеза. Детали."}, "decode": {"box_scale": box_scale, "score_mode": mode},
           "run": run}
    (d / "config.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True))
    if complete:
        (d / "meta.json").write_text(json.dumps({"start": f"2026-11-14T1{seed}:00:00", "git_sha": "abc", "seed": seed,
                                                 "best_epoch": 3, "val_map": 0.1, "val_thr": 0.5, "val_auc": 0.8,
                                                 "train_min": 90.0, "mlflow_run_id": f"m{name}"}))
        _tables(d)
    for v, spec in (variants or {}).items():
        vd = d / "posthoc" / v
        _tables(vd)
        if spec:
            (vd / "variant.json").write_text(json.dumps(spec))
    return d


def _tables(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([("p1", 0.9, *G[0])], columns=PRED_COLS).to_csv(d / "val_predictions.csv", index=False)
    pd.DataFrame({"patientId": ["p1", "n1"], "image_score": [0.9, 0.0]}).to_csv(d / "val_image_scores.csv", index=False)


def _series(vals: list[float], ids: list[str] | None = None) -> pd.Series:
    return pd.Series(vals, index=pd.Index(ids or [f"i{k}" for k in range(len(vals))], name="patientId"), dtype=float)


def _ev(run_name: str, per: pd.Series, variant: str = "") -> Evaluated:
    run = Run(run_name, Path(run_name), {}, {}, run_name.rsplit("_s", 1)[0], int(run_name.rsplit("_s", 1)[1]), False,
              True)
    return Evaluated(Unit(run, variant, run.dir), 0.5, pd.DataFrame({"thr": [0.5], "map": [float(per.mean())]}), per,
                     {"map": float(np.nanmean(per))})


# ----------------------------------------------------------------------------- grouping / discovery

def test_config_name_and_smoke() -> None:
    assert config_name({"run": {"config_path": "configs/hw2/full.yaml"}}, "x_s0") == "full"
    assert config_name({"run": {"config_path": "configs/baseline.yaml", "overrides": ["train.epochs=2"]}}, "x") \
        == "baseline[train.epochs=2]"
    assert config_name({}, "b_aug_s3") == "b_aug"
    assert is_smoke({"run": {"limit_val": 64}}) and is_smoke({"run": {"smoke": True}})
    assert not is_smoke({"run": {"max_steps": None, "limit_train": None, "limit_val": None, "smoke": False}})


def test_discover_group_missing_and_variants(tmp_path: Path) -> None:
    r = tmp_path / "results"
    _write_run(r, "baseline_s0", "configs/baseline.yaml", 0)
    _write_run(r, "baseline_s1", "configs/baseline.yaml", 1, complete=False)  # still training
    _write_run(r, "full_s0", "configs/hw2/full.yaml", 0,
               variants={"no_gating": {"box_scale": 1.0, "score_mode": "heatmap"}, "tuned": {"box_scale": 0.9}})
    _write_run(r, "full_s1", "configs/hw2/full.yaml", 1, variants={"tuned": {}, "no_boxscale": {
        "box_scale": 1.0, "score_mode": "heatmap_x_cls"}})
    _write_run(r, "smoke_full", "configs/hw2/full.yaml", 0, smoke=True)
    (r / "baseline_trivial" / "empty").mkdir(parents=True)  # no config.yaml -> not a run
    runs, notes = discover([r, tmp_path / "nope"])
    assert {x.name for x in runs} == {"baseline_s0", "baseline_s1", "full_s0", "full_s1", "smoke_full"}
    assert any("does not exist" in n for n in notes)
    groups = group_by_config(runs)
    assert list(groups) == ["baseline", "full"]  # CONFIG_ORDER; smoke and incomplete runs excluded
    assert list(groups["baseline"]) == [0] and list(groups["full"]) == [0, 1]
    miss = "\n".join(missing_report(runs, groups, "tuned"))
    assert "baseline seed 1: in progress" in miss and "baseline seed 2: not run" in miss and "b_aug seed 0: not run" in miss
    assert "full seed 2: not run" in miss
    assert "'tuned' missing" not in miss  # B is the HW1 baseline as trained: no primary variant expected
    assert "no_boxscale" not in miss  # with a primary variant the raw tables stand in for no_boxscale
    f0, f1 = groups["full"][0], groups["full"][1]
    assert primary_unit(f0, "tuned").variant == "tuned" and primary_unit(f0, None).variant == ""
    assert primary_unit(groups["baseline"][0], "tuned").dir == groups["baseline"][0].dir  # falls back to raw tables
    # f0: raw tables become the no_boxscale ablation; f1 already has a no_boxscale dir (no duplicate)
    assert [(u.variant, u.dir) for u in posthoc_units(f0, "tuned")] == [("no_boxscale", f0.dir),
                                                                      ("no_gating", f0.variants["no_gating"])]
    assert [u.variant for u in posthoc_units(f1, "tuned")] == ["no_boxscale"]
    assert [u.variant for u in posthoc_units(f0, None)] == ["no_gating", "tuned"]


def test_build_ledger_statuses(tmp_path: Path) -> None:
    r = tmp_path / "results"
    _write_run(r, "a_s0", "configs/a.yaml", 0)
    _write_run(r, "a_s1", "configs/a.yaml", 1)
    _write_run(r, "a_s2", "configs/a.yaml", 2, complete=False)
    runs, _ = discover([r])
    ledger = pd.DataFrame([
        {"run_name": "a_s0", "date": "2026-11-14 10:00", "config": "configs/a.yaml", "seed": "0", "val_map": "0.1"},
        {"run_name": "a_s0", "date": "2026-11-13 09:00", "config": "configs/a.yaml", "seed": "0", "val_map": "0.2"},
        {"run_name": "gone", "date": "2026-11-12 09:00", "config": "configs/a.yaml", "seed": "0", "val_map": "0.3"}])
    st = build_ledger(runs, ledger).set_index(["run_name", "date"])["status"]
    assert st[("a_s0", "2026-11-14 10:00")] == "ok"
    assert st[("a_s0", "2026-11-13 09:00")].startswith("superseded")
    assert st[("gone", "2026-11-12 09:00")] == "no results dir"
    assert st[("a_s1", "2026-11-14 11:00")] == "ok (not in experiments.csv)"  # dir without a ledger row
    assert st[("a_s2", "")] == "in progress"


# ----------------------------------------------------------------------------- paired statistics

def test_contrast_single_pair_equals_paired_bootstrap() -> None:
    rng = np.random.default_rng(1)
    a = _series(np.where(rng.random(300) < 0.2, np.nan, rng.random(300)).tolist())
    b = _series(np.where(rng.random(300) < 0.3, np.nan, rng.random(300)).tolist())
    c = contrast_bootstrap([[(1.0, a), (-1.0, b)]], n_boot=500, seed=3)
    p = paired_bootstrap_diff(a, b, n_boot=500, seed=3)
    assert c["diff"] == pytest.approx(p["diff"]) and c["lo"] == pytest.approx(p["lo"]) and c["hi"] == pytest.approx(p["hi"])
    assert c["p_diff_le_0"] == pytest.approx(p["p_diff_le_0"])
    g = pd.Series([f"p{k // 4}" for k in range(len(a))], index=a.index)  # 4 images per patient
    cg = contrast_bootstrap([[(1.0, a), (-1.0, b)]], n_boot=500, seed=3, clusters=g)
    pg = paired_bootstrap_diff(a, b, n_boot=500, seed=3, groups=g)
    assert cg["lo"] == pytest.approx(pg["lo"]) and cg["hi"] == pytest.approx(pg["hi"]) and cg["n_units"] == 75


def test_contrast_seed_mean_and_identity() -> None:
    a0, b0 = _series([1, 0, 0.5, np.nan]), _series([0, 0, 0.5, 0])
    a1, b1 = _series([1, 1, 0.5, np.nan]), _series([1, 0, 0.5, np.nan])
    c = contrast_bootstrap([[(1, a0), (-1, b0)], [(1, a1), (-1, b1)]], n_boot=300)
    d0 = np.nanmean(a0) - np.nanmean(b0)
    d1 = np.nanmean(a1) - np.nanmean(b1)
    assert c["diff"] == pytest.approx((d0 + d1) / 2) and c["n_groups"] == 2
    same = contrast_bootstrap([[(1, a0), (-1, a0)]], n_boot=200)
    assert same["diff"] == 0 and same["lo"] == 0 and same["hi"] == 0 and same["p_diff_le_0"] == 1
    # only common image ids are used
    part = contrast_bootstrap([[(1, _series([1.0, 0.0], ["x", "y"])), (-1, _series([0.0], ["x"]))]], n_boot=50)
    assert part["n_images"] == 1 and part["diff"] == 1


def test_seed_matched_ablation_rows() -> None:
    rng = np.random.default_rng(0)
    full = {s: _ev(f"full_s{s}", _series(rng.random(50).tolist())) for s in (0, 1, 2)}
    b_cls = {s: _ev(f"b_cls_s{s}", _series(rng.random(50).tolist())) for s in (0, 1)}
    assert [s for s, _, _ in seed_pairs(full, b_cls)] == [0, 1]
    rows = ablation_rows(full, {"b_cls": b_cls, "b_aug": {}}, n_boot=200)
    assert len(rows) == 1 and rows[0]["seeds"] == [0, 1]  # configs without matching seeds are skipped
    per = [full[s].metrics["map"] - b_cls[s].metrics["map"] for s in (0, 1)]
    assert [p["diff"] for p in rows[0]["per_seed"]] == pytest.approx(per)
    assert rows[0]["diff"] == pytest.approx(np.mean(per)) and rows[0]["lo"] <= rows[0]["diff"] <= rows[0]["hi"]
    assert rows[0]["per_seed"][0]["ref"] == "full_s0" and rows[0]["per_seed"][0]["abl"] == "b_cls_s0"


def test_factorial_additive_has_zero_interaction() -> None:
    rng = np.random.default_rng(2)
    base = rng.random(80) * 0.5
    cells = {"baseline": 0.0, "b_aug": 0.05, "b_cls": 0.1, "full": 0.15}  # additive: interaction 0
    ev = {c: {s: _ev(f"{c}_s{s}", _series((base + d + 0.01 * s).tolist())) for s in (0, 1)} for c, d in cells.items()}
    rows = {r["effect"]: r for r in factorial_rows(ev, n_boot=200)}
    assert rows["aug main effect"]["diff"] == pytest.approx(0.05)
    assert rows["cls main effect"]["diff"] == pytest.approx(0.10)
    assert rows["interaction aug×cls"]["diff"] == pytest.approx(0.0, abs=1e-12)
    assert factorial_rows({k: v for k, v in ev.items() if k != "b_aug"}, n_boot=10) == []


def test_summary_frame_mean_std() -> None:
    rows = [{"config": "full", "n_seeds": 2, "seeds": [0, 1], "units": ["tuned", "raw"], "val_map": [0.1, 0.2],
             "test_map": [], "n_test": 0}]
    f = summary_frame(rows).iloc[0]
    assert f["val_map_mean"] == pytest.approx(0.15) and f["val_map_std"] == pytest.approx(np.std([0.1, 0.2], ddof=1))
    assert np.isnan(f["test_map_mean"]) and f["seeds"] == "0/tuned 1/raw"


# ----------------------------------------------------------------------------- decomposition (report + analysis)

def _toy():
    """p1 hit, p2 overlapping but IoU < 0.4, p3 missed, p4 partial (1 of 2 GT), n1 FP, n2 empty, n3 sub-thr box only."""
    ids = ["p1", "p2", "p3", "p4", "n1", "n2", "n3"]
    gt = {"p1": G, "p2": G, "p3": G, "p4": np.r_[G, G + 400], "n1": np.zeros((0, 4)), "n2": np.zeros((0, 4)),
          "n3": np.zeros((0, 4))}
    pred = pd.DataFrame([("p1", 0.9, *G[0]), ("p2", 0.8, 100, 100, 600, 600), ("p3", 0.2, *G[0]),
                         ("p4", 0.7, *G[0]), ("n1", 0.6, 0, 0, 50, 50), ("n3", 0.1, 0, 0, 50, 50)], columns=PRED_COLS)
    meta = pd.DataFrame({"patientId": ids, "target": [1, 1, 1, 1, 0, 0, 0], "idx": range(7),
                         "cls": ["Lung Opacity"] * 4 + ["Normal", "No Lung Opacity / Not Normal", "Normal"],
                         "view": ["AP", "PA", "AP", "PA", "AP", "PA", "AP"], "sex": list("MFMFMFM"),
                         "age_bucket": ["<20", "20-40", "40-60", "60+", "<20", "20-40", "40-60"],
                         "n_boxes": ["1", "1", "1", "2", "0", "0", "0"]}).set_index("patientId")
    return ids, gt, pred, meta


def test_unit_metrics_losses_add_up() -> None:
    ids, gt, pred, meta = _toy()
    mt, per = unit_metrics(pred, None, ids, gt, meta["target"], thr=0.5)
    assert mt["map"] == pytest.approx(rsna_map(gt, preds_from_df(pred), ids, 0.5))
    assert mt["map"] + mt["loss_fp_neg"] + mt["loss_missed_pos"] + mt["loss_loc_pos"] == pytest.approx(1.0)
    assert mt["n_scored"] == 5 and mt["fp_image_rate"] == pytest.approx(1 / 3)
    assert mt["sensitivity"] == pytest.approx(3 / 4) and mt["specificity"] == pytest.approx(2 / 3)


def test_unit_metrics_auc_uses_the_units_own_boxes() -> None:
    ids, gt, pred, meta = _toy()
    img = pd.DataFrame({"patientId": ids, "image_score": [0.1, 0.1, 0.1, 0.1, 0.9, 0.9, 0.9],  # cls prob: inverted
                        "cls_prob": [0.1, 0.1, 0.1, 0.1, 0.9, 0.9, 0.9]})
    mt, _ = unit_metrics(pred, img, ids, gt, meta["target"], thr=0.5)
    # max box score per image: p 0.9/0.8/0.2/0.7, n 0.6/0/0.1 -> 11 of 12 pairs ordered
    assert mt["image_auc"] == pytest.approx(11 / 12) and mt["cls_auc"] == pytest.approx(0.0)
    assert np.isnan(unit_metrics(pred, None, ids, gt, meta["target"], thr=0.5)[0]["cls_auc"])


def test_evaluate_unit_never_selects_the_threshold_on_test(tmp_path: Path) -> None:
    ids, gt, pred, meta = _toy()
    pred.to_csv(tmp_path / "test_predictions.csv", index=False)
    pd.DataFrame({"patientId": ids, "image_score": 0.5}).to_csv(tmp_path / "test_image_scores.csv", index=False)
    run = Run("full_s0", tmp_path, {}, {}, "full", 0, False, True)
    with pytest.raises(FileNotFoundError, match="VAL sweep"):
        evaluate_unit(Unit(run, "", tmp_path), gt, meta["target"], "test")
    pd.DataFrame({"thr": [0.15], "map": [0.3]}).to_csv(tmp_path / "threshold_sweep.csv", index=False)
    assert evaluate_unit(Unit(run, "", tmp_path), gt, meta["target"], "test").thr == 0.15  # the val one


def test_decomposition_md_states_total_localization() -> None:
    ids, gt, pred, meta = _toy()
    e = decomposition(per_image_table(preds_from_df(pred), gt, ids, meta, thr=0.5))
    loc = e["loss_loc_zero"] + e["loss_loc_partial"]
    assert f"Локализация всего (AP = 0 + 0 < AP < 1): {loc:.4f}" in decomposition_md(e)


@needs_data
def test_build_factorial_is_immune_to_box_scale_tuning(tmp_path: Path) -> None:
    """Null study: 4 configs with IDENTICAL val tables (boxes x1.25 too large), box_scale tuned for all but B as in
    run_hw2.sh. The 2x2 must be exactly 0 (as-trained cells); val Δs of tuned vs untuned units carry the † flag."""
    from rsna.evaluate import load_meta
    from rsna.posthoc import make_variant, tune

    meta = load_meta()
    ids = meta.loc[meta["split"] == "val", "patientId"].head(300).tolist()
    gt = load_gt(paths.BOXES, ids)
    rows = [(i, 0.9, *(np.r_[b[:2] + b[2:] / 2 - b[2:] * 0.625, b[2:] * 1.25])) for i in ids for b in gt[i]]
    rows += [(i, 0.3, 300.0, 300.0, 200.0, 200.0) for i in ids if not len(gt[i])][:60]
    pred = pd.DataFrame(rows, columns=PRED_COLS).round(1)
    pred[["x", "y"]] = pred[["x", "y"]].clip(lower=0)
    res = tmp_path / "results"
    for c, cfg in (("baseline", "configs/baseline.yaml"), ("b_aug", "configs/hw2/b_aug.yaml"),
                   ("b_cls", "configs/hw2/b_cls.yaml"), ("full", "configs/hw2/full.yaml")):
        d = res / f"{c}_s0"
        d.mkdir(parents=True)
        (d / "config.yaml").write_text(yaml.safe_dump({"model": {"cls_head": False}, "decode": {
            "box_scale": 1.0, "score_mode": "heatmap"}, "run": {"name": d.name, "seed": 0, "config_path": cfg}}))
        (d / "meta.json").write_text(json.dumps({"start": "2026-11-14T10:00:00", "git_sha": "x", "mlflow_run_id": c}))
        pred.to_csv(d / "val_predictions.csv", index=False)
        pd.DataFrame({"patientId": ids, "image_score": 0.5}).to_csv(d / "val_image_scores.csv", index=False)
        from rsna.metric import threshold_sweep
        threshold_sweep(gt, preds_from_df(pred), ids).to_csv(d / "threshold_sweep.csv", index=False)
        if c != "baseline":
            tune(d)
            make_variant(d, "tuned", "tuned", "keep", n_boot=20)
    out = build([res], "tuned", n_boot=100, out_md=tmp_path / "exp.md", fig_dir=tmp_path / "fig",
                mlflow_uri=f"sqlite:///{tmp_path / 'none.db'}")
    assert len(out["factorial"]) == 3 and all(f["diff"] == 0 for f in out["factorial"])
    d = {r["ablation"]: r for r in out["deltas"]}
    assert d["baseline"]["diff"] > 0.05 and d["baseline"]["box_scale_selection"]  # tuning gain only, flagged
    assert d["no_boxscale"]["box_scale_selection"] and d["b_cls"]["diff"] == 0 and not d["b_cls"]["box_scale_selection"]
    md = (tmp_path / "exp.md").read_text()
    assert "одинаково для всех конфигов" not in md and "cross-fit" in md and "Full − all  (vs B) †" in md


def test_analysis_categories_decomposition_and_slices() -> None:
    ids, gt, pred, meta = _toy()
    tab = per_image_table(preds_from_df(pred), gt, ids, meta, thr=0.5)
    assert tab["category"].to_dict() == {"p1": "perfect", "p2": "loc_zero", "p3": "missed", "p4": "partial",
                                         "n1": "fp_neg", "n2": "tn", "n3": "tn"}
    assert 0 < tab.loc["p2", "best_iou"] <= 0.4 and tab.loc["p3", "max_sub"] == pytest.approx(0.2)
    e = decomposition(tab)
    parts = e["loss_fp_neg"] + e["loss_missed_pos"] + e["loss_loc_zero"] + e["loss_loc_partial"]
    assert e["map"] + parts == pytest.approx(1.0)
    assert e["loss_loc_zero"] + e["loss_loc_partial"] == pytest.approx(e["loss_loc_pos"])
    sl = slice_table(tab)
    gap = 1 - e["map"]
    for col, g in sl.groupby("slice"):  # every slice column partitions the total gap
        assert g["gap_points"].sum() == pytest.approx(gap), col
        assert g["n"].sum() == len(ids)


def test_box_pairs_ratios_and_scaling() -> None:
    gt = {"a": np.array([[100.0, 100.0, 100.0, 200.0]])}
    pred = {"a": (np.array([[90.0, 80.0, 120.0, 240.0], [600, 600, 50, 50]]), np.array([0.9, 0.8]))}
    pairs = box_pairs(pred, gt, ["a"], thr=0.5)
    assert len(pairs) == 1 and pairs.iloc[0]["rw"] == pytest.approx(1.2) and pairs.iloc[0]["rh"] == pytest.approx(1.2)
    assert greedy_pairs(np.zeros((0, 4)), np.zeros(0), gt["a"]) == []
    same = scale_boxes(pred, 1.0)["a"][0]
    assert np.allclose(same, pred["a"][0])
    small = scale_boxes({"e": (np.array([[0.0, 0.0, 100.0, 100.0]]), np.array([1.0]))}, 2.0)["e"][0]
    assert np.allclose(small, [[0, 0, 150, 150]])  # clipped at the image border like rsna.decode


def test_calibration_perfect() -> None:
    y = np.r_[np.zeros(50), np.ones(50)]
    t, ece, brier = calibration(y, y.copy())
    assert ece == pytest.approx(0) and brier == pytest.approx(0) and t["n"].sum() == 100
