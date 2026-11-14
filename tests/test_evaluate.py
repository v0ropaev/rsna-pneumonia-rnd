"""Tests for rsna.evaluate (metrics bundle, error decomposition, oracle, compare, summarize) and rsna.baselines."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from rsna import paths
from rsna.evaluate import (compare, error_decomposition, evaluate_predictions, load_meta, main, oracle_gating,
                           summarize, write_preds)
from rsna.metric import preds_from_df

HAS_DATA = paths.METADATA.exists() and paths.SPLIT_FILE.exists() and paths.BOXES.exists()
needs_data = pytest.mark.skipif(not HAS_DATA, reason="processed data / split not available")
G = np.array([[100.0, 100.0, 200.0, 200.0]])


def _toy() -> tuple[pd.DataFrame, dict[str, np.ndarray], pd.DataFrame]:
    """4 images: p1 positive & perfectly hit, p2 positive & missed, n1 negative with a FP box, n2 negative & empty."""
    meta = pd.DataFrame({"patientId": ["p1", "p2", "n1", "n2"], "target": [1, 1, 0, 0],
                         "view": ["AP", "PA", "AP", "PA"], "sex": ["M", "F", "M", "F"],
                         "age_bucket": ["<20", "60+", "20-40", "40-60"],
                         "cls": ["Lung Opacity", "Lung Opacity", "No Lung Opacity / Not Normal", "Normal"],
                         "n_boxes": ["1", "1", "0", "0"]})
    gt = {"p1": G, "p2": G + 300, "n1": np.zeros((0, 4)), "n2": np.zeros((0, 4))}
    pred = pd.DataFrame([("p1", 0.9, *G[0]), ("n1", 0.8, 0, 0, 50, 50), ("n2", 0.1, 0, 0, 50, 50)],
                        columns=["patientId", "score", "x", "y", "width", "height"])
    return meta, gt, pred


def test_evaluate_predictions_toy() -> None:
    meta, gt, pred = _toy()
    ids = meta["patientId"].tolist()
    mt, per = evaluate_predictions(pred, None, ids, meta, thr=0.5, n_boot=200, slice_boot=50, gt=gt)
    # p1 -> 1, p2 -> 0, n1 -> 0 (FP), n2 excluded (its box is below thr)
    assert per.isna().tolist() == [False, False, False, True]
    assert mt["map"] == pytest.approx(1 / 3)
    assert mt["n_scored"] == 3
    assert mt["sensitivity"] == 0.5 and mt["specificity"] == 0.5
    assert mt["matched_iou"] == pytest.approx(1.0)
    e = mt["errors"]
    assert (e["n_fp_neg_images"], e["fp_image_rate"], e["map_pos"]) == (1, 0.5, 0.5)
    assert e["loss_fp_neg"] + e["loss_missed_pos"] + e["loss_loc_pos"] == pytest.approx(1 - mt["map"])
    assert (e["loss_fp_neg"], e["loss_missed_pos"], e["loss_loc_pos"]) == pytest.approx((1 / 3, 1 / 3, 0.0))
    # oracle gating removes the n1 FP: mean of (1, 0) over the positives
    assert mt["oracle_gating"]["map_at_run_thr"] == pytest.approx(0.5)
    cls = {r["value"]: r for r in mt["slices"]["cls"]}
    assert cls["No Lung Opacity / Not Normal"]["fp_image_rate"] == 1.0
    assert cls["Normal"]["fp_image_rate"] == 0.0 and np.isnan(cls["Normal"]["map"])
    assert [r["value"] for r in mt["slices"]["age_bucket"]] == ["<20", "20-40", "40-60", "60+"]
    # thr 0.05 keeps the n2 box too -> n2 scores 0 and is included
    mt2, per2 = evaluate_predictions(pred, None, ids, meta, thr=0.05, n_boot=50, slice_boot=10, gt=gt)
    assert mt2["map"] == pytest.approx(1 / 4) and per2.notna().all()


def test_error_decomposition_is_exact_on_random_data() -> None:
    rng = np.random.default_rng(0)
    n = 500
    target = pd.Series(rng.random(n) < 0.3).astype(int)
    has_pred = pd.Series(rng.random(n) < 0.6)
    ap = pd.Series(np.where(target == 1, np.where(has_pred, rng.random(n), 0.0),
                            np.where(has_pred, 0.0, np.nan)))
    e = error_decomposition(ap, target, has_pred)
    assert e["n_scored"] == ap.notna().sum()
    assert e["loss_fp_neg"] + e["loss_missed_pos"] + e["loss_loc_pos"] == pytest.approx(1 - ap.mean())


def test_oracle_gating_sweeps_its_own_threshold() -> None:
    gt = {"p": G, "n": np.zeros((0, 4))}
    pred = preds_from_df(pd.DataFrame([("p", 0.2, *G[0]), ("n", 0.9, *G[0])],
                                      columns=["patientId", "score", "x", "y", "width", "height"]))
    o = oracle_gating(gt, pred, ["p", "n"], pd.Series({"p": 1, "n": 0}), thr=0.5)
    assert o["map_at_run_thr"] == 0.0 and o["map_at_best_thr"] == 1.0 and o["best_thr"] <= 0.2


def _fake_run(root: Path, name: str, ids: list[str], pred: pd.DataFrame, thr: float) -> Path:
    run = root / name
    run.mkdir()
    write_preds(pred, pd.DataFrame({"patientId": ids, "image_score": 0.5}), run, "val")
    pd.DataFrame({"thr": [thr], "map": [0.1], "n_scored": [1]}).to_csv(run / "threshold_sweep.csv", index=False)
    return run


@needs_data
def test_load_meta_slices() -> None:
    meta = load_meta()
    assert set(meta["split"]) == {"train", "val", "test"}
    assert set(meta["age_bucket"]) <= {"<20", "20-40", "40-60", "60+", "invalid"}
    assert (meta.loc[meta["age"] > 100, "age_bucket"] == "invalid").all()
    assert set(meta["n_boxes"]) == {"0", "1", "2", "3+"}


@needs_data
def test_compare_and_summarize(tmp_path: Path) -> None:
    meta = load_meta()
    val = meta[meta["split"] == "val"].head(300)
    ids = val["patientId"].tolist()
    boxes = pd.read_csv(paths.BOXES)
    perfect = boxes[boxes["patientId"].isin(ids)].assign(score=0.9)
    a = _fake_run(tmp_path, "perfect", ids, perfect, 0.5)
    b = _fake_run(tmp_path, "empty", ids[:200], perfect.iloc[:0], 0.5)
    res = compare(a, b, "val", n_boot=300, out_dir=tmp_path / "cmp")
    assert res["n_common"] == 200 and res["n_only_a"] == 100
    assert res["map_a"] == pytest.approx(1.0) and res["map_b"] == 0.0
    assert res["diff"] == pytest.approx(1.0) and res["p_diff_le_0"] == 0.0
    assert (tmp_path / "cmp" / "perfect__vs__empty__val.md").exists()
    for run, m in [(a, 0.3), (b, 0.5)]:
        (run / "val_metrics.json").write_text(json.dumps(
            {"map": m, "ci_lo": 0, "ci_hi": 1, "threshold": 0.5, "image_roc_auc": 0.5, "sensitivity": 1,
             "specificity": 0, "matched_iou": 0.5, "errors": {"fp_image_rate": 0.1}}))
    df = summarize([a, b], "val", out=tmp_path / "sum")
    assert df.loc[df["run"] == "mean", "map"].item() == pytest.approx(0.4)
    assert (tmp_path / "sum" / "val_summary.md").exists()


@needs_data
def test_eval_cli_on_stored_val_predictions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    meta = load_meta()
    ids = meta.loc[meta["split"] == "val", "patientId"].head(120).tolist()
    pred = pd.read_csv(paths.BOXES)
    pred = pred[pred["patientId"].isin(ids)].assign(score=0.7)
    run = _fake_run(tmp_path, "toyrun", ids, pred, 0.5)
    monkeypatch.setattr(paths, "RUNS", tmp_path / "no_runs")
    main(["--run", str(run), "--split", "val", "--n-boot", "100", "--limit", "60"])
    mt = json.loads((run / "val_lim60_metrics.json").read_text())
    assert mt["n_images"] == 60 and mt["map"] == pytest.approx(1.0) and mt["threshold"] == 0.5
    assert (run / "val_lim60_metrics.md").exists()


@needs_data
def test_baseline_priors_are_fit_on_train_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from rsna.baselines import fit_priors, make_predictions

    meta = load_meta()
    pri = fit_priors(meta)
    assert pri.shape == (2, 4) and pri[0, 0] < 512 < pri[1, 0]
    # corrupting every val/test box must not change the priors -> only train boxes are used
    boxes = pd.read_csv(paths.BOXES)
    train = boxes["patientId"].isin(meta.loc[meta["split"] == "train", "patientId"])
    boxes.loc[~train, ["x", "y"]] += 300.0
    boxes.to_csv(tmp_path / "boxes.csv", index=False)
    monkeypatch.setattr(paths, "BOXES", tmp_path / "boxes.csv")
    assert np.allclose(fit_priors(meta), pri)
    monkeypatch.undo()
    ids = meta.loc[meta["split"] == "val", "patientId"].head(50).tolist()
    pred, img = make_predictions("prior_boxes_ap", ids, meta, pri)
    n_ap = int((meta.set_index("patientId").loc[ids, "view"] == "AP").sum())
    assert len(pred) == 2 * n_ap and (img["image_score"] > 0).sum() == n_ap
    assert len(make_predictions("empty", ids, meta, pri)[0]) == 0


@needs_data
def test_run_eval_reads_the_runs_split_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import yaml

    meta = load_meta()
    ids = meta.loc[meta["split"] == "val", "patientId"].head(40).tolist()
    pred = pd.read_csv(paths.BOXES)
    run = _fake_run(tmp_path, "splitrun", ids, pred[pred["patientId"].isin(ids)].assign(score=0.7), 0.5)
    monkeypatch.setattr(paths, "RUNS", tmp_path / "no_runs")
    # a run trained with another split file, in which these images are NOT val
    other = pd.read_csv(paths.SPLIT_FILE)
    other.loc[other["patientId"].isin(ids[:5]), "split"] = "test"
    other.to_csv(tmp_path / "split_other.csv", index=False)
    (run / "config.yaml").write_text(yaml.safe_dump({"data": {"split_file": str(tmp_path / "split_other.csv")}}))
    with pytest.raises(AssertionError, match="outside split"):
        main(["--run", str(run), "--split", "val", "--n-boot", "50"])
    (run / "config.yaml").write_text(yaml.safe_dump({"data": {"split_file": "data/splits/split_v1.csv"}}))
    main(["--run", str(run), "--split", "val", "--n-boot", "50"])
    (run / "config.yaml").write_text(yaml.safe_dump({"data": {"split_file": str(tmp_path / "missing.csv")}}))
    with pytest.raises(FileNotFoundError):
        main(["--run", str(run), "--split", "val", "--n-boot", "50"])


@needs_data
def test_metrics_carry_provenance_and_stale_ones_are_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    meta = load_meta()
    ids = meta.loc[meta["split"] == "val", "patientId"].head(40).tolist()
    run = _fake_run(tmp_path, "provrun", ids, pd.read_csv(paths.BOXES).iloc[:0].assign(score=[]), 0.5)
    monkeypatch.setattr(paths, "RUNS", tmp_path / "no_runs")
    train_meta = {"start": "2026-01-01T00:00:00", "mlflow_run_id": "abc", "git_sha": "1234567"}
    (run / "meta.json").write_text(json.dumps({**train_meta, "seed": 0}))
    main(["--run", str(run), "--split", "val", "--n-boot", "50"])
    assert json.loads((run / "val_metrics.json").read_text())["train_run"] == train_meta
    summarize([run], "val")  # fresh -> fine
    (run / "meta.json").write_text(json.dumps({**train_meta, "start": "2026-02-02T00:00:00"}))  # retrained
    with pytest.raises(ValueError, match="another training run"):
        summarize([run], "val")
    # test-split predictions of an older model are refused by compare as well
    write_preds(pd.DataFrame(columns=["patientId", "score", "x", "y", "width", "height"]),
                pd.DataFrame({"patientId": ids, "image_score": 0.0}), run, "test")
    (run / "test_metrics.json").write_text(json.dumps({"train_run": train_meta}))
    with pytest.raises(ValueError, match="another training run"):
        compare(run, run, "test", n_boot=10, out_dir=tmp_path / "cmp")
