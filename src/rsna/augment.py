"""Batch-wise on-device augmentations with consistent box transforms.

Geometry (hflip, affine scale/translate/rotate) is one 2x3 matrix per image in normalised coordinates
([-1, 1] spans the image edges, align_corners=False). The forward matrix M maps input -> output coords and is
applied to box corners on CPU; its inverse drives `grid_sample` on the device. Rotated boxes become the
axis-aligned hull of their corners. Intensity (brightness / contrast / gamma) acts on [0,1] floats.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import torch
import torch.nn.functional as F

from .paths import ORIG_SIZE


def sample_geometry(n: int, cfg: dict[str, Any], rng: np.random.Generator) -> np.ndarray | None:
    """Forward matrices M [n,2,3] (input -> output, normalised coords) or None if no geometric aug is on."""
    if not (cfg.get("hflip") or cfg.get("affine")):
        return None
    m = np.tile(np.eye(3), (n, 1, 1))
    if cfg.get("hflip"):
        flip = rng.random(n) < cfg.get("hflip_p", 0.5)
        m[flip, 0, 0] = -1.0
    if cfg.get("affine"):
        s = rng.uniform(1 - cfg.get("scale", 0.1), 1 + cfg.get("scale", 0.1), n)
        a = np.deg2rad(rng.uniform(-cfg.get("rotate", 5.0), cfg.get("rotate", 5.0), n))
        t = rng.uniform(-cfg.get("translate", 0.05), cfg.get("translate", 0.05), (n, 2)) * 2  # fraction of width
        rs = np.zeros((n, 3, 3))
        rs[:, 0, 0], rs[:, 0, 1], rs[:, 1, 0], rs[:, 1, 1] = s * np.cos(a), -s * np.sin(a), s * np.sin(a), s * np.cos(a)
        rs[:, :2, 2], rs[:, 2, 2] = t, 1.0
        m = rs @ m
    return m[:, :2, :]


def warp_images(x: torch.Tensor, m: np.ndarray) -> torch.Tensor:
    """Apply forward matrices M to images x [B,C,S,S] (zeros padding, bilinear)."""
    full = np.tile(np.eye(3), (len(m), 1, 1))
    full[:, :2] = m
    theta = torch.from_numpy(np.linalg.inv(full)[:, :2].astype(np.float32)).to(x.device)
    grid = F.affine_grid(theta, list(x.shape), align_corners=False)
    return F.grid_sample(x, grid, mode="bilinear", padding_mode="zeros", align_corners=False)


def warp_boxes(boxes: np.ndarray, m: np.ndarray, orig_size: int = ORIG_SIZE,
               min_visible: float = 0.3, min_side: float = 4.0) -> np.ndarray:
    """Transform xywh boxes (original px) with one forward matrix M [2,3]; clip; drop mostly-outside boxes."""
    b = np.asarray(boxes, np.float64).reshape(-1, 4)
    if len(b) == 0:
        return b
    x1, y1, x2, y2 = b[:, 0], b[:, 1], b[:, 0] + b[:, 2], b[:, 1] + b[:, 3]
    corners = np.stack([np.stack([x1, y1], 1), np.stack([x2, y1], 1), np.stack([x1, y2], 1), np.stack([x2, y2], 1)], 1)
    u = corners / orig_size * 2 - 1  # [k,4,2]
    v = u @ m[:, :2].T + m[:, 2]
    p = (v + 1) / 2 * orig_size
    lo, hi = p.min(1), p.max(1)
    area = np.prod(hi - lo, 1)
    clo, chi = lo.clip(0, orig_size), hi.clip(0, orig_size)
    wh = chi - clo
    keep = (wh.min(1) >= min_side) & (np.prod(wh, 1) >= min_visible * area)
    return np.concatenate([clo, wh], 1)[keep]


def intensity(x: torch.Tensor, cfg: dict[str, Any], rng: np.random.Generator) -> torch.Tensor:
    """Per-image contrast (around the image mean), brightness shift and gamma on [0,1] images."""
    n = x.shape[0]
    c = torch.from_numpy(rng.uniform(1 - cfg.get("contrast", 0.1), 1 + cfg.get("contrast", 0.1), n)).float()
    b = torch.from_numpy(rng.uniform(-cfg.get("brightness", 0.1), cfg.get("brightness", 0.1), n)).float()
    g = torch.from_numpy(np.exp(rng.uniform(-cfg.get("gamma", 0.1), cfg.get("gamma", 0.1), n))).float()
    c, b, g = (t.to(x.device).view(n, 1, 1, 1) for t in (c, b, g))
    mean = x.mean((1, 2, 3), keepdim=True)
    return (((x - mean) * c + mean + b).clamp(0, 1) + 1e-6).pow(g).clamp(0, 1)


def augment_batch(x: torch.Tensor, boxes: list[np.ndarray], cfg: dict[str, Any] | None,
                  rng: np.random.Generator) -> tuple[torch.Tensor, list[np.ndarray]]:
    """x: float [B,1,S,S] in [0,1] on any device; boxes: per-image xywh in original px."""
    if not cfg:
        return x, boxes
    m = sample_geometry(len(x), cfg, rng)
    if m is not None:
        if cfg.get("affine"):
            x = warp_images(x, m)
        else:  # pure flips: exact and cheaper than resampling
            flip = torch.from_numpy(m[:, 0, 0] < 0).to(x.device).view(-1, 1, 1, 1)
            x = torch.where(flip, x.flip(3), x)
        boxes = [warp_boxes(b, mi) for b, mi in zip(boxes, m)]
    if cfg.get("intensity"):
        x = intensity(x, cfg, rng)
    return x, boxes
