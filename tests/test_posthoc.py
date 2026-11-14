"""rsna.posthoc: offline box_scale / score_mode transforms == online decode; tune / variant on val; test variants."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch
import yaml

from rsna import paths
from rsna.decode import decode, predict, predict_frames
from rsna.evaluate import compare, evaluate_predictions, load_meta, main as eval_main, read_preds, summarize
from rsna.metric import SCORE_THRESHOLDS, load_gt, preds_from_df, rsna_map
from rsna.model import CenterNetLite
from rsna.posthoc import DEFAULT_GRID, apply_posthoc, main as posthoc_main, parse_grid

HAS_DATA = paths.METADATA.exists() and paths.SPLIT_FILE.exists() and paths.BOXES.exists()
needs_data = pytest.mark.skipif(not HAS_DATA, reason="processed data / split not available")
COLS = ["patientId", "score", "x", "y", "width", "height"]
DEC = {"topk": 10, "nms_iou": 0.5, "box_scale": 1.0, "score_mode": "heatmap", "min_score": 0.01}
SETTINGS = [(1.0, "heatmap"), (0.8, "heatmap"), (1.3, "heatmap"), (1.0, "heatmap_x_cls"), (0.85, "heatmap_x_cls"),
            (1.3, "heatmap_x_cls")]


def _synthetic_out(b: int = 8, r: int = 32, seed: int = 0) -> dict[str, torch.Tensor]:
    g = torch.Generator().manual_seed(seed)
    hm = torch.randn(b, 1, r, r, generator=g) * 1.5 - 2.0
    return {"hm": hm, "wh": torch.rand(b, 2, r, r, generator=g) * 30, "off": torch.rand(b, 2, r, r, generator=g),
            "cls": torch.cat([torch.tensor([-8.0]), torch.randn(b - 1, generator=g) * 3])}  # image 0: cls prob ~3e-4


def _frame(ids: list[str], dets: list) -> pd.DataFrame:
    rows = [(pid, s, *bx, s) for pid, (b, s_, raw) in zip(ids, dets) for bx, s in zip(b, raw)]
    return pd.DataFrame(rows, columns=COLS + ["raw_score"])


@pytest.mark.parametrize("box_scale,mode", SETTINGS)
def test_online_decode_equals_offline_posthoc(box_scale: float, mode: str) -> None:
    """Float level: decode(box_scale, mode) == apply_posthoc(decode(1.0, heatmap)) (same boxes, same rows)."""
    out = _synthetic_out()
    ids = [f"i{k}" for k in range(8)]
    raw = decode(out, return_raw=True)
    online = decode(out, box_scale=box_scale, score_mode=mode, return_raw=True)
    img = pd.DataFrame({"patientId": ids, "cls_prob": torch.sigmoid(out["cls"]).double().numpy()})
    off = apply_posthoc(_frame(ids, raw), img, box_scale, mode, round_output=False)
    on = pd.DataFrame([(pid, s, *bx, r) for pid, (b, sc, rw) in zip(ids, online) for bx, s, r in zip(b, sc, rw)],
                      columns=COLS + ["raw_score"])
    assert len(on) == len(off) > 20
    assert (on["patientId"] == off["patientId"]).all()
    np.testing.assert_array_equal(on["raw_score"], off["raw_score"])  # top-K / min_score / NMS on the raw score
    np.testing.assert_allclose(on[COLS[2:]].to_numpy(), off[COLS[2:]].to_numpy(), atol=2e-3)
    np.testing.assert_allclose(on["score"], off["score"], rtol=1e-6, atol=1e-9)
    if box_scale > 1:  # the clipping branch is exercised
        assert ((off["x"] == 0) | (off["y"] == 0) | (off["x"] + off["width"] >= 1024 - 1e-6)).any()
    if mode == "heatmap_x_cls":  # gated scores below min_score stay (switchable back to heatmap exactly)
        assert (off["score"] < 0.01).any() and (off["raw_score"] >= 0.01).all()


def _small_model(cls_head: bool) -> CenterNetLite:
    torch.manual_seed(0)
    m = CenterNetLite("resnet18", pretrained=False, cls_head=cls_head)
    for head in (m.hm, m.wh, m.off):
        torch.nn.init.normal_(head[-1].weight, std=0.05)
    torch.nn.init.constant_(m.hm[-1].bias, -1.0)
    torch.nn.init.constant_(m.wh[-1].bias, 4.0)
    return m.eval()


@pytest.mark.parametrize("cls_head", [True, False])
def test_predict_frames_are_exact_offline_transforms(cls_head: bool, tmp_path: Path) -> None:
    """Stored tables: the RAW table does not depend on the decode settings, and every configured table equals
    apply_posthoc of the RAW table read back from CSV (exactly), and the float online decode (to storage precision)."""
    model = _small_model(cls_head)
    images = np.random.default_rng(0).integers(0, 256, (6, 256, 256), dtype=np.uint8)
    ids = [f"p{k}" for k in range(6)]
    cpu = torch.device("cpu")
    base = {"decode": DEC, "model": {"cls_head": cls_head}}
    _, img0, raw0 = predict_frames(model, images, ids, base, cpu, batch_size=4)
    assert len(raw0) > 10 and raw0["score"].nunique() > 5
    assert ("raw_score" in raw0) == cls_head and ("cls_prob" in img0) == cls_head and "max_box_score" in img0
    if not cls_head:
        assert list(raw0.columns) == COLS and (img0["image_score"] == img0["max_box_score"]).all()
    raw0.to_csv(tmp_path / "raw.csv", index=False)
    img0.to_csv(tmp_path / "img.csv", index=False, float_format="%.5f")
    raw_disk, img_disk = read_preds(tmp_path / "raw.csv"), pd.read_csv(tmp_path / "img.csv", dtype={"patientId": str})
    pd.testing.assert_frame_equal(raw_disk, raw0)
    pd.testing.assert_frame_equal(img_disk, img0)
    for box_scale, mode in SETTINGS if cls_head else [s for s in SETTINGS if s[1] == "heatmap"]:
        cfg = {**base, "decode": {**DEC, "box_scale": box_scale, "score_mode": mode}}
        pred, img, raw = predict_frames(model, images, ids, cfg, cpu, batch_size=4)
        pd.testing.assert_frame_equal(raw, raw0)
        pd.testing.assert_frame_equal(img, img0)
        pd.testing.assert_frame_equal(pred, apply_posthoc(raw_disk, img_disk, box_scale, mode))
        dets, _ = predict(model, images, cfg, cpu, batch_size=4)  # float online decode, unrounded
        on = np.concatenate([np.c_[s, b] for b, s in dets])
        np.testing.assert_allclose(on[:, 0], pred["score"], atol=2e-4)
        np.testing.assert_allclose(on[:, 1:], pred[COLS[2:]].to_numpy(), atol=0.2)


def _raw_table(seed: int = 0, n: int = 30) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    ids = [f"p{i}" for i in range(n)]
    rows = []
    for pid in ids:
        for s in np.sort(rng.uniform(0.01, 1, rng.integers(0, 6)))[::-1]:
            xy, wh = rng.uniform(0, 800, 2), rng.uniform(10, 300, 2)
            rows.append((pid, round(s, 4), *np.round(np.r_[xy, np.minimum(wh, 1024 - xy)], 1)))
    df = pd.DataFrame(rows, columns=COLS).assign(raw_score=lambda d: d["score"])
    return df, pd.DataFrame({"patientId": ids, "image_score": 0.0, "cls_prob": np.round(rng.random(n), 5)})


def test_gating_is_monotonic() -> None:
    raw, img = _raw_table()
    gated = apply_posthoc(raw, img, 1.0, "heatmap_x_cls")
    assert len(gated) == len(raw) and (gated["score"] <= gated["raw_score"] + 5e-5).all()
    for _, g in gated.groupby("patientId"):  # the within-image ranking never changes
        r, s = g["raw_score"].to_numpy(), g["score"].to_numpy()
        assert (s[np.argsort(-r, kind="stable")] == np.sort(s)[::-1]).all()
    hi = apply_posthoc(raw, img.assign(cls_prob=np.minimum(img["cls_prob"] + 0.2, 1.0)), 1.0, "heatmap_x_cls")
    assert (hi["score"] >= gated["score"]).all()  # higher cls prob -> never a lower box score
    heat = apply_posthoc(raw, img, 1.0, "heatmap")
    for t in SCORE_THRESHOLDS:  # gating can only remove boxes at any threshold
        assert (gated["score"] >= t).sum() <= (heat["score"] >= t).sum()


def test_box_scale_one_is_identity_and_geometry() -> None:
    raw, img = _raw_table(1)
    for mode in ("keep", "heatmap"):
        pd.testing.assert_frame_equal(apply_posthoc(raw, img, 1.0, mode), raw)
        old, old_img = raw.drop(columns="raw_score"), img[["patientId", "image_score"]]
        pd.testing.assert_frame_equal(apply_posthoc(old, old_img, 1.0, mode), old)
    gated = apply_posthoc(raw, img, 0.8, "heatmap_x_cls")
    pd.testing.assert_frame_equal(apply_posthoc(gated, img, 1.0, "keep"), gated)  # composable
    pd.testing.assert_frame_equal(apply_posthoc(gated, img, 1.0, "heatmap"),  # raw_score kept -> gating reversible
                                  apply_posthoc(raw, img, 0.8, "heatmap"))
    t = pd.DataFrame([("a", 0.5, 100.0, 100.0, 200.0, 100.0), ("a", 0.4, 0.0, 0.0, 100.0, 100.0)], columns=COLS)
    np.testing.assert_allclose(apply_posthoc(t, None, 0.5)[COLS[2:]].to_numpy()[0], [150, 125, 100, 50])
    np.testing.assert_allclose(apply_posthoc(t, None, 2.0)[COLS[2:]].to_numpy()[1], [0, 0, 150, 150])  # clipped
    with pytest.raises(ValueError, match="cls_prob"):
        apply_posthoc(t, None, 1.0, "heatmap_x_cls")
    with pytest.raises(ValueError, match="raw_score"):  # a gated table without raw scores cannot be re-scored
        apply_posthoc(raw.drop(columns="raw_score"), img, 1.0, "heatmap")


def test_old_format_tables_evaluate_identically() -> None:
    meta = pd.DataFrame({"patientId": ["p1", "p2", "n1", "n2"], "target": [1, 1, 0, 0], "view": ["AP", "PA", "AP", "PA"],
                         "sex": ["M", "F", "M", "F"], "age_bucket": ["<20", "60+", "20-40", "40-60"],
                         "cls": ["Lung Opacity", "Lung Opacity", "Normal", "Normal"], "n_boxes": ["1", "1", "0", "0"]})
    g = np.array([[100.0, 100.0, 200.0, 200.0]])
    gt = {"p1": g, "p2": g + 300, "n1": np.zeros((0, 4)), "n2": np.zeros((0, 4))}
    old = pd.DataFrame([("p1", 0.9, *g[0]), ("p2", 0.4, *(g[0] + 290)), ("n1", 0.8, 0, 0, 50, 50),
                        ("n2", 0.1, 0, 0, 50, 50)], columns=COLS)
    img = pd.DataFrame({"patientId": meta["patientId"], "image_score": [0.9, 0.4, 0.8, 0.1]})
    ids = meta["patientId"].tolist()
    for thr in (0.05, 0.5):
        a, pa = evaluate_predictions(old, img, ids, meta, thr, n_boot=50, slice_boot=10, gt=gt)
        b, pb = evaluate_predictions(apply_posthoc(old, img, 1.0, "heatmap"), img, ids, meta, thr, n_boot=50,
                                     slice_boot=10, gt=gt)
        assert json.dumps(a, default=str) == json.dumps(b, default=str)
        pd.testing.assert_series_equal(pa, pb)


def test_parse_grid_always_contains_one() -> None:
    g = parse_grid("0.70:1.00:0.025")
    assert len(g) == 13 and g[0] == 0.7 and g[-1] == 1.0
    assert 1.0 in parse_grid("0.8:0.9:0.05")
    d = parse_grid(DEFAULT_GRID)  # two-sided: I3 may point either way (HW1 epoch-3 ckpt preferred x1.15)
    assert d.min() < 1.0 < d.max() and d.max() >= 1.25 and len(d) == 21


# ----------------------------------------------------------------------------- CLI on fake runs (real GT)

def _inflate(b: np.ndarray, f: float) -> np.ndarray:
    c = b[:, :2] + b[:, 2:] / 2
    return np.c_[c - b[:, 2:] * f / 2, b[:, 2:] * f]


def _fake_tables(ids: list[str], tp: float, fp: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Positives: GT boxes inflated x1.2 with score `tp`; negatives: one box with score `fp`."""
    gt = load_gt(paths.BOXES, ids)
    rows = []
    for pid in ids:
        if len(gt[pid]):
            rows += [(pid, tp, *b) for b in _inflate(gt[pid], 1.2)]
        else:
            rows.append((pid, fp, 300.0, 300.0, 200.0, 200.0))
    pred = pd.DataFrame(rows, columns=COLS).round(1)
    return pred, pd.DataFrame({"patientId": ids, "image_score": 0.5, "max_box_score": 0.5})


def _inside(ids: list[str]) -> list[str]:
    """Images whose x1.2 boxes stay inside the frame (no clipping, so the best scale is known exactly)."""
    gt = load_gt(paths.BOXES, ids)
    ok = lambda f: (f[:, :2] >= 0).all() and (f[:, :2] + f[:, 2:] <= 1024).all()
    return [i for i in ids if ok(_inflate(gt[i], 1.2))]


@pytest.fixture
def fake_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    meta = load_meta()
    ids = _inside(meta.loc[meta["split"] == "val", "patientId"].head(220).tolist())
    run = tmp_path / "fake_s0"
    run.mkdir()
    pred, img = _fake_tables(ids, tp=0.9, fp=0.3)
    pred.to_csv(run / "val_predictions.csv", index=False)
    img.to_csv(run / "val_image_scores.csv", index=False)
    gt = load_gt(paths.BOXES, ids)
    from rsna.metric import threshold_sweep
    threshold_sweep(gt, preds_from_df(pred), ids).to_csv(run / "threshold_sweep.csv", index=False)
    (run / "config.yaml").write_text(yaml.safe_dump({"data": {"split_file": "data/splits/split_v1.csv"},
                                                     "model": {"cls_head": False}, "decode": DEC}))
    (run / "meta.json").write_text(json.dumps({"start": "2026-11-14T10:00:00", "mlflow_run_id": "x", "git_sha": "abc"}))
    monkeypatch.setattr(paths, "RUNS", tmp_path / "no_runs")  # no checkpoint: nothing may be re-predicted
    return run


@needs_data
def test_tune_and_variant_on_val(fake_run: Path) -> None:
    posthoc_main(["tune", "--run", str(fake_run)])
    ph = fake_run / "posthoc"
    res = json.loads((ph / "box_scale.json").read_text())
    tab = pd.read_csv(ph / "box_scale_tuning.csv")
    assert len(tab) == 21 and (ph / "box_scale.png").exists()
    # x1.2 boxes: every scale in ~(0.72, 0.96) gives mAP 1 -> tie -> the one closest to 1.0
    assert res["box_scale"] == 0.95 and res["val_map"] == pytest.approx(1.0)
    assert res["val_map_box_scale_1"] == pytest.approx(0.75) and res["score_mode"] == "heatmap"
    # cross-fit: selected on one half, scored on the other; the true effect is large here, so it survives
    assert not res["at_grid_edge"] and len(res["crossfit_folds"]) == 2
    assert {f["box_scale"] for f in res["crossfit_folds"]} == {0.95} and res["crossfit_gain"] > 0.15
    assert not list(fake_run.glob("test_*"))
    posthoc_main(["variant", "--run", str(fake_run), "--name", "tuned", "--box-scale", "tuned", "--n-boot", "50"])
    vdir = ph / "tuned"
    spec = json.loads((vdir / "variant.json").read_text())
    mt = json.loads((vdir / "val_metrics.json").read_text())
    assert spec["box_scale"] == 0.95 and spec["box_scale_source"].startswith("tuned on val")
    assert mt["map"] == pytest.approx(1.0) and mt["threshold"] == spec["val_thr"] == 0.35
    assert (vdir / "val_predictions.csv").exists() and (vdir / "threshold_sweep.csv").exists()
    with pytest.raises(FileNotFoundError, match="tune"):
        posthoc_main(["variant", "--run", str(fake_run), "--name", "x", "--box-scale", "tuned",
                      "--score-mode", "heatmap_x_cls"])


@needs_data
def test_tune_flags_grid_edge(fake_run: Path) -> None:
    posthoc_main(["tune", "--run", str(fake_run), "--grid", "1.00:1.10:0.05"])  # optimum (<= 0.95) lies below the grid
    res = json.loads((fake_run / "posthoc" / "box_scale.json").read_text())
    assert res["box_scale"] == 1.0 and res["at_grid_edge"]  # 1.0 on the edge counts too (the old one-sided grid)


@needs_data
def test_redefining_variant_drops_stale_test_artifacts(fake_run: Path) -> None:
    posthoc_main(["tune", "--run", str(fake_run)])
    posthoc_main(["variant", "--run", str(fake_run), "--name", "tuned", "--box-scale", "tuned", "--n-boot", "50"])
    vdir = fake_run / "posthoc" / "tuned"
    for f in ("test_predictions.csv", "test_image_scores.csv", "test_metrics.json", "test_lim5_metrics.md"):
        (vdir / f).write_text("old")  # made with the old definition
    cdir = fake_run.parent / "comparisons"
    cdir.mkdir()
    old = [cdir / "fake_s0@tuned__vs__b_s0__test.json", cdir / "x_s0__vs__fake_s0@tuned__val.md"]
    keep = [cdir / "fake_s0__vs__b_s0__test.json", cdir / "fake_s0@tuned2__vs__b_s0__val.json"]
    for f in old + keep:
        f.write_text("{}")
    posthoc_main(["variant", "--run", str(fake_run), "--name", "tuned", "--box-scale", "1.0", "--n-boot", "50"])
    assert not list(vdir.glob("test*")) and not any(f.exists() for f in old) and all(f.exists() for f in keep)
    assert json.loads((vdir / "variant.json").read_text())["box_scale"] == 1.0


@needs_data
def test_test_split_variant_uses_val_selection(fake_run: Path) -> None:
    posthoc_main(["tune", "--run", str(fake_run)])
    posthoc_main(["variant", "--run", str(fake_run), "--name", "tuned", "--box-scale", "tuned", "--n-boot", "50"])
    meta = load_meta()
    ids = _inside(meta.loc[meta["split"] == "test", "patientId"].head(150).tolist())
    # on test the FP boxes score 0.4: the test-optimal threshold (0.45) differs from the val one (0.35)
    raw, img = _fake_tables(ids, tp=0.5, fp=0.4)
    raw.to_csv(fake_run / "test_predictions_raw.csv", index=False)
    img.to_csv(fake_run / "test_image_scores.csv", index=False)
    prov = json.loads((fake_run / "meta.json").read_text())
    (fake_run / "test_predictions_raw.json").write_text(json.dumps({"train_run": prov}))
    eval_main(["--run", str(fake_run), "--split", "test", "--variant", "tuned", "--n-boot", "50"])
    vdir = fake_run / "posthoc" / "tuned"
    mt = json.loads((vdir / "test_metrics.json").read_text())
    assert mt["threshold"] == 0.35 and mt["variant"]["box_scale"] == 0.95
    gt = load_gt(paths.BOXES, ids)
    expected = rsna_map(gt, preds_from_df(apply_posthoc(raw, img, 0.95, "heatmap")), ids, 0.35)
    assert mt["map"] == pytest.approx(expected) and expected < 0.9
    best_test = max(rsna_map(gt, preds_from_df(apply_posthoc(raw, img, 0.95, "heatmap")), ids, t) for t in SCORE_THRESHOLDS)
    assert best_test > mt["map"]  # the test optimum was not used
    # main run on the same RAW table: config box_scale 1.0 / heatmap -> test_predictions.csv == raw table
    eval_main(["--run", str(fake_run), "--split", "test", "--n-boot", "50"])
    pd.testing.assert_frame_equal(read_preds(fake_run / "test_predictions.csv"), read_preds(fake_run / "test_predictions_raw.csv"))
    res = compare(f"{fake_run}:tuned", fake_run, "test", n_boot=100, out_dir=fake_run / "cmp")
    assert res["a"] == "fake_s0:tuned" and res["thr_a"] == 0.35 and res["diff"] > 0
    assert (fake_run / "cmp" / "fake_s0@tuned__vs__fake_s0__test.md").exists()
    df = summarize([f"{fake_run}:tuned", str(fake_run)], "test")
    assert df["run"].tolist()[:2] == ["fake_s0:tuned", "fake_s0"]
    # a retrained run invalidates the RAW test table and the variant
    (fake_run / "meta.json").write_text(json.dumps({**prov, "start": "2026-11-15T00:00:00"}))
    with pytest.raises(ValueError, match="another training run"):
        eval_main(["--run", str(fake_run), "--split", "test", "--variant", "tuned", "--n-boot", "50"])


@needs_data
def test_cls_run_without_raw_scores_refuses_mode_switch(fake_run: Path) -> None:
    cfg = yaml.safe_load((fake_run / "config.yaml").read_text())
    cfg["model"]["cls_head"], cfg["decode"]["score_mode"] = True, "heatmap_x_cls"
    (fake_run / "config.yaml").write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError, match="raw_score"):
        posthoc_main(["tune", "--run", str(fake_run), "--score-mode", "heatmap", "--grid", "0.9:1.0:0.1"])
    posthoc_main(["tune", "--run", str(fake_run), "--grid", "0.9:1.0:0.1"])  # keep (box_scale only) is fine
    assert (fake_run / "posthoc" / "box_scale.json").exists()
