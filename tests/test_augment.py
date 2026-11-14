import numpy as np
import pytest
import torch

from rsna.augment import augment_batch, intensity, warp_boxes

S, ORIG = 256, 1024
BOX = np.array([[300.0, 200.0, 240.0, 360.0]])  # original px


def rect_image(box: np.ndarray) -> torch.Tensor:
    x = torch.zeros(1, 1, S, S)
    x0, y0, w, h = (box * S / ORIG).round().astype(int)
    x[..., y0 : y0 + h, x0 : x0 + w] = 1.0
    return x


def white_bbox(x: torch.Tensor) -> np.ndarray:
    ys, xs = np.nonzero(x[0, 0].numpy() > 0.5)
    return np.array([xs.min(), ys.min(), xs.max() + 1 - xs.min(), ys.max() + 1 - ys.min()]) * ORIG / S


def iou(a: np.ndarray, b: np.ndarray) -> float:
    lo, hi = np.maximum(a[:2], b[:2]), np.minimum(a[:2] + a[2:], b[:2] + b[2:])
    inter = np.prod((hi - lo).clip(0))
    return inter / (a[2] * a[3] + b[2] * b[3] - inter)


def test_hflip_exact():
    x = rect_image(BOX[0])
    y, (b,) = augment_batch(x, [BOX], {"hflip": True, "hflip_p": 1.0}, np.random.default_rng(0))
    assert torch.equal(y, torch.flip(x, dims=[3]))
    assert np.allclose(b[0], [1024 - 300 - 240, 200, 240, 360])


@pytest.mark.parametrize("seed", range(5))
@pytest.mark.parametrize("rotate", [0.0, 8.0])
def test_affine_box_follows_pixels(seed: int, rotate: float):
    cfg = {"hflip": True, "hflip_p": 0.5, "affine": True, "scale": 0.15, "translate": 0.08, "rotate": rotate}
    x = rect_image(BOX[0])
    y, (b,) = augment_batch(x, [BOX], cfg, np.random.default_rng(seed))
    assert b.shape == (1, 4)
    wb = white_bbox(y)
    tol = 2 * ORIG / S  # two output pixels
    assert (wb[:2] >= b[0, :2] - tol).all() and (wb[:2] + wb[2:] <= b[0, :2] + b[0, 2:] + tol).all()  # covers
    assert iou(wb, b[0]) > (0.9 if rotate == 0 else 0.75)  # and is tight (rotation hull is looser)


def test_box_dropped_when_moved_out():
    m = np.array([[1.0, 0.0, 1.9], [0.0, 1.0, 0.0]])  # shift right by 95% of the image
    assert len(warp_boxes(BOX, m)) == 0
    assert len(warp_boxes(np.zeros((0, 4)), m)) == 0


def test_intensity_range_and_noop():
    x = torch.rand(4, 1, 32, 32)
    y = intensity(x, {"brightness": 0.2, "contrast": 0.2, "gamma": 0.2}, np.random.default_rng(0))
    assert y.shape == x.shape and y.min() >= 0 and y.max() <= 1 and not torch.equal(x, y)
    z, b = augment_batch(x, [BOX] * 4, {"hflip": False, "affine": False, "intensity": False}, np.random.default_rng(0))
    assert torch.equal(z, x) and b[0] is BOX
