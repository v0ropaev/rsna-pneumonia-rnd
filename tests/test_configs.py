"""HW2 configs: full copies of the baseline that differ only in the intended keys; they build and run one step."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest
import torch

from rsna.augment import augment_batch
from rsna.decode import decode_cfg
from rsna.model import build_model, centernet_loss
from rsna.targets import build_targets
from rsna.utils import flatten, get_device, load_config

ROOT = Path(__file__).resolve().parents[1]
BASE = load_config(ROOT / "configs" / "baseline.yaml")
AUG = {"aug.hflip": True, "aug.affine": True, "aug.rotate": 0.0, "aug.intensity": True}
CLS = {"model.cls_head": True, "decode.score_mode": "heatmap_x_cls"}
EXPECTED = {"b_aug": AUG, "b_cls": CLS, "full": {**AUG, **CLS}}


def _load(name: str) -> dict[str, Any]:
    return load_config(ROOT / "configs" / "hw2" / f"{name}.yaml")


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_only_intended_keys_differ(name: str) -> None:
    cfg = _load(name)
    base, new = flatten({k: v for k, v in BASE.items() if k != "meta"}), flatten({k: v for k, v in cfg.items() if k != "meta"})
    assert set(new) == set(base), f"{name}: added/removed keys {set(new) ^ set(base)}"
    diff = {k: new[k] for k in base if new[k] != base[k]}
    assert diff == EXPECTED[name]
    # intended values that are equal to the baseline but must stay pinned
    assert cfg["loss"]["cls_weight"] == 1.0 and cfg["decode"]["box_scale"] == 1.0
    assert cfg["aug"]["scale"] == 0.1 and cfg["aug"]["translate"] == 0.05 and cfg["aug"]["hflip_p"] == 0.5
    assert all(cfg["aug"][k] == 0.1 for k in ("brightness", "contrast", "gamma"))


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_meta_documents_the_change(name: str) -> None:
    m = _load(name)["meta"]
    assert m["experiment"] == BASE["meta"]["experiment"] and m["parent"] == "configs/baseline.yaml"
    assert len(m["hypothesis"]) > 200 and any("а" <= ch <= "я" for ch in m["hypothesis"])  # Russian prose
    changed = {c.split(":")[0] for c in m["changes"]}
    assert set(EXPECTED[name]) <= changed, f"meta.changes misses {set(EXPECTED[name]) - changed}"


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_config_runs_one_step(name: str) -> None:
    """Augment -> targets -> forward -> loss -> backward -> decode with the config itself (tiny random weights)."""
    cfg = _load(name)
    cfg = {**cfg, "model": {**cfg["model"], "pretrained": False}}
    model = build_model(cfg)
    x = torch.rand(2, 1, 64, 64)
    boxes = [np.array([[300.0, 200.0, 240.0, 360.0]]), np.zeros((0, 4))]
    x, boxes = augment_batch(x, boxes, cfg["aug"], np.random.default_rng(0))
    out = model(x)
    loss, parts = centernet_loss(out, build_targets(boxes, 64, model.stride), cfg["loss"])
    loss.backward()
    assert torch.isfinite(loss) and ("cls" in parts) == cfg["model"]["cls_head"]
    dets = decode_cfg({k: v.detach() for k, v in out.items()}, cfg)
    assert len(dets) == 2


@pytest.mark.parametrize("value,expected", [("cpu", "cpu"), (" CPU ", "cpu")])
def test_get_device_env_override(value: str, expected: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RSNA_DEVICE", value)
    assert get_device().type == expected
    monkeypatch.setenv("RSNA_DEVICE", "tpu")
    with pytest.raises(ValueError, match="RSNA_DEVICE"):
        get_device()
