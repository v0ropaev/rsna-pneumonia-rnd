import numpy as np
import pytest
import torch

from rsna.decode import decode
from rsna.model import CenterNetLite, centernet_loss
from rsna.targets import build_targets, encode_image, gaussian_radius

LOSS_CFG = {"wh_weight": 0.1, "off_weight": 1.0}
BOXES = [
    np.array([[100.0, 150.0, 220.0, 380.0], [600.0, 200.0, 250.0, 400.0]]),
    np.array([[0.0, 0.0, 90.0, 120.0], [930.0, 880.0, 94.0, 144.0], [5.0, 700.0, 160.0, 310.0]]),  # borders
    np.zeros((0, 4)),
    np.array([[412.3, 517.9, 33.3, 41.7]]),  # small, non-integer
]


def iou_xywh(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a1, a2 = a[:, None, :2], a[:, None, :2] + a[:, None, 2:]
    b1, b2 = b[None, :, :2], b[None, :, :2] + b[None, :, 2:]
    inter = np.prod((np.minimum(a2, b2) - np.maximum(a1, b1)).clip(0), -1)
    return inter / (np.prod(a[:, None, 2:], -1) + np.prod(b[None, :, 2:], -1) - inter)


def perfect_output(tgt: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    p = tgt["hm"].clamp(1e-6, 1 - 1e-6)
    return {"hm": torch.log(p / (1 - p)), "wh": tgt["wh"], "off": tgt["off"]}


def test_gaussian_radius_matches_centernet_reference():
    assert gaussian_radius(10, 10) == pytest.approx((-28 + 1120**0.5) / 2, abs=1e-9)  # r3 term, by hand
    assert gaussian_radius(30, 60) > gaussian_radius(10, 20) > 0


def test_encode_peak_and_regression_cells():
    hm, wh, off, mask = encode_image(np.array([[100.0, 150.0, 220.0, 380.0]]), out_size=32)
    cx, cy = (100 + 110) / 32, (150 + 190) / 32  # 6.5625, 10.625
    assert hm[0, 10, 6] == 1.0 and hm.max() == 1.0 and mask.sum() == 1 and mask[0, 10, 6] == 1
    assert np.allclose(wh[:, 10, 6], [220 / 32, 380 / 32]) and np.allclose(off[:, 10, 6], [cx - 6, cy - 10])


@pytest.mark.parametrize("size", [256, 384])
def test_targets_decode_round_trip(size: int):
    tgt = build_targets(BOXES, size, stride=8)
    assert tgt["hm"].shape == (len(BOXES), 1, size // 8, size // 8)
    assert tgt["cls"].tolist() == [1.0, 1.0, 0.0, 1.0]
    dets = decode(perfect_output(tgt), topk=10, nms_iou=0.5)
    for gt, (pred, scores) in zip(BOXES, dets):
        pred = pred[scores > 0.5]
        assert len(pred) == len(gt)
        if len(gt):
            assert (iou_xywh(gt, pred).max(1) > 0.95).all()


def test_box_scale_and_clipping():
    tgt = build_targets([np.array([[0.0, 0.0, 200.0, 100.0]])], 256)
    (b, s), = decode(perfect_output(tgt), box_scale=0.5)
    assert np.allclose(b[0], [50.0, 25.0, 100.0, 50.0], atol=1e-3)
    (b, s), = decode(perfect_output(tgt), box_scale=2.0)
    assert (b[:, :2] >= 0).all() and (b[:, :2] + b[:, 2:] <= 1024 + 1e-6).all()


def test_loss_perfect_lower_than_random():
    torch.manual_seed(0)
    tgt = build_targets(BOXES, 256)
    perfect, _ = centernet_loss(perfect_output(tgt), tgt, LOSS_CFG)
    rnd = {"hm": torch.randn_like(tgt["hm"]), "wh": torch.randn_like(tgt["wh"]) * 5, "off": torch.rand_like(tgt["off"])}
    random_loss, _ = centernet_loss(rnd, tgt, LOSS_CFG)
    assert perfect.item() < 0.05 * random_loss.item()


def test_model_shapes_and_loss_backward():
    m = CenterNetLite("resnet18", pretrained=False, cls_head=True)
    out = m(torch.rand(2, 1, 256, 256))
    assert out["hm"].shape == (2, 1, 32, 32) and out["wh"].shape == (2, 2, 32, 32) and out["cls"].shape == (2,)
    loss, parts = centernet_loss(out, build_targets(BOXES[:2], 256), {**LOSS_CFG, "cls_weight": 1.0})
    loss.backward()
    assert set(parts) == {"hm", "wh", "off", "cls"} and torch.isfinite(loss)
    dets = decode(out, score_mode="heatmap_x_cls")
    assert len(dets) == 2 and all(len(b) == len(s) <= 10 for b, s in dets)
