"""CenterNet training targets: gaussian center heatmap + size/offset regression at the center cell.

Boxes come in original-pixel xywh (default 1024 px); maps live on the output grid R = image_size / stride.
Size targets are in output-grid units, offsets are the sub-cell remainder of the continuous center.
"""
from __future__ import annotations

import math

import numpy as np
import torch

from .paths import ORIG_SIZE


def gaussian_radius(h: float, w: float, min_overlap: float = 0.7) -> float:
    """Radius from CenterNet (xingyizhou/CenterNet, utils/image.py), kept verbatim incl. its known quirk."""
    b1 = h + w
    c1 = w * h * (1 - min_overlap) / (1 + min_overlap)
    r1 = (b1 + math.sqrt(b1**2 - 4 * c1)) / 2
    b2 = 2 * (h + w)
    c2 = (1 - min_overlap) * w * h
    r2 = (b2 + math.sqrt(b2**2 - 16 * c2)) / 2
    a3 = 4 * min_overlap
    b3 = -2 * min_overlap * (h + w)
    c3 = (min_overlap - 1) * w * h
    r3 = (b3 + math.sqrt(b3**2 - 4 * a3 * c3)) / 2
    return min(r1, r2, r3)


def _gaussian2d(radius: int) -> np.ndarray:
    d = 2 * radius + 1
    sigma = d / 6
    y, x = np.ogrid[-radius : radius + 1, -radius : radius + 1]
    g = np.exp(-(x * x + y * y) / (2 * sigma * sigma))
    g[g < np.finfo(g.dtype).eps * g.max()] = 0
    return g.astype(np.float32)


def draw_gaussian(hm: np.ndarray, cx: int, cy: int, radius: int) -> None:
    """Max-merge a gaussian peak (value 1 at (cx, cy)) into hm [H, W] in place."""
    g = _gaussian2d(radius)
    hgt, wid = hm.shape
    left, right = min(cx, radius), min(wid - cx, radius + 1)
    top, bottom = min(cy, radius), min(hgt - cy, radius + 1)
    patch = hm[cy - top : cy + bottom, cx - left : cx + right]
    np.maximum(patch, g[radius - top : radius + bottom, radius - left : radius + right], out=patch)


def encode_image(
    boxes: np.ndarray, out_size: int, orig_size: int = ORIG_SIZE, min_overlap: float = 0.7
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Targets for one image. Returns hm [1,R,R], wh [2,R,R], off [2,R,R], mask [1,R,R] (float32)."""
    r = out_size
    hm = np.zeros((1, r, r), np.float32)
    wh = np.zeros((2, r, r), np.float32)
    off = np.zeros((2, r, r), np.float32)
    mask = np.zeros((1, r, r), np.float32)
    k = r / orig_size
    for x, y, w, h in np.asarray(boxes, np.float64).reshape(-1, 4):
        wo, ho = w * k, h * k
        if wo <= 0 or ho <= 0:
            continue
        cxf, cyf = (x + w / 2) * k, (y + h / 2) * k
        cx, cy = min(max(int(cxf), 0), r - 1), min(max(int(cyf), 0), r - 1)
        rad = max(0, int(gaussian_radius(math.ceil(ho), math.ceil(wo), min_overlap)))
        draw_gaussian(hm[0], cx, cy, rad)
        wh[:, cy, cx] = (wo, ho)
        off[:, cy, cx] = (cxf - cx, cyf - cy)
        mask[0, cy, cx] = 1.0
    return hm, wh, off, mask


def build_targets(
    boxes_list: list[np.ndarray], image_size: int, stride: int = 8, min_overlap: float = 0.7,
    device: torch.device | str = "cpu",
) -> dict[str, torch.Tensor]:
    """Batch targets as tensors on `device`: hm, wh, off, mask (+ cls = image has >=1 box)."""
    enc = [encode_image(b, image_size // stride, min_overlap=min_overlap) for b in boxes_list]
    out = {k: torch.from_numpy(np.stack([e[i] for e in enc])) for i, k in enumerate(("hm", "wh", "off", "mask"))}
    out["cls"] = torch.tensor([float(len(np.asarray(b).reshape(-1, 4)) > 0) for b in boxes_list])
    return {k: v.to(device, non_blocking=True) for k, v in out.items()}
