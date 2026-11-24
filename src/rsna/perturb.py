"""Input perturbations for the HW3 robustness check (inference only) and the RQ3 lung-field mask.

All functions take a uint8 batch [N, S, S] (the model's input cache) and return uint8 of the same shape: the
perturbation acts on the image the model actually sees (256 px) and the result is re-quantized to 8 bit, like any
real input. Random perturbations use a fixed seed, so every checkpoint sees the SAME noisy images (paired design).

Families (level = the parameter):
  noise     additive Gaussian noise, sigma in [0, 1] intensity units (0.02 = 5 gray levels)
  blur      Gaussian blur, sigma in pixels of the 256 px input
  lowres    area-downsample to `level` px and bilinear-upsample back (a lower-resolution acquisition / export)
  jpeg      JPEG re-compression at quality `level`
  contrast  (x - mean) * level + mean per image (training augmentation covered 0.9-1.1)
  gamma     x ** level (training augmentation covered exp(+-0.1) = 0.905-1.105)
  mask      RQ3: pixels outside the lung-field rectangle `level` = (x0, y0, x1, y1) in 1024-px coordinates set to the
            image median (removes text such as PORTABLE, markers and frame edges; not a lung segmentation)
"""
from __future__ import annotations

import io

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from scipy.ndimage import gaussian_filter

from .paths import ORIG_SIZE

FAMILIES = ("noise", "blur", "lowres", "jpeg", "contrast", "gamma", "mask")


def _to_u8(x: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(x * 255.0), 0, 255).astype(np.uint8)


def perturb(images: np.ndarray, family: str, level, seed: int = 0) -> np.ndarray:
    x = np.asarray(images)
    if family == "clean":
        return x.copy()
    f = x.astype(np.float32) / 255.0
    if family == "noise":
        rng = np.random.default_rng(seed)
        out = f + rng.normal(0.0, float(level), f.shape).astype(np.float32)
    elif family == "blur":
        out = gaussian_filter(f, sigma=(0, float(level), float(level)), mode="nearest")
    elif family == "lowres":
        t = torch.from_numpy(f).unsqueeze(1)
        small = F.interpolate(t, size=(int(level), int(level)), mode="area")
        out = F.interpolate(small, size=f.shape[1:], mode="bilinear", align_corners=False).squeeze(1).numpy()
    elif family == "jpeg":
        out_u8 = np.empty_like(x)
        for i, im in enumerate(x):
            buf = io.BytesIO()
            Image.fromarray(im).save(buf, format="JPEG", quality=int(level))
            out_u8[i] = np.asarray(Image.open(io.BytesIO(buf.getvalue())).convert("L"))
        return out_u8
    elif family == "contrast":
        mean = f.mean(axis=(1, 2), keepdims=True)
        out = (f - mean) * float(level) + mean
    elif family == "gamma":
        out = np.power(np.clip(f, 0, 1) + 1e-6, float(level))
    elif family == "mask":
        x0, y0, x1, y1 = (int(round(v * x.shape[1] / ORIG_SIZE)) for v in level)
        out_u8 = x.copy()
        med = np.median(x.reshape(len(x), -1), axis=1).astype(np.uint8)
        keep = np.zeros(x.shape[1:], bool)
        keep[max(y0, 0):min(y1, x.shape[1]), max(x0, 0):min(x1, x.shape[2])] = True
        out_u8[:, ~keep] = med[:, None]
        return out_u8
    else:
        raise ValueError(f"unknown family {family}")
    return _to_u8(out)


def lung_field(boxes: np.ndarray, q: float = 0.005) -> tuple[float, float, float, float]:
    """Rectangle (x0, y0, x1, y1), 1024-px coordinates, covering the central 99 % of TRAIN GT box extents:
    x0 = q-quantile of left edges, x1 = (1-q)-quantile of right edges, same for y."""
    b = np.asarray(boxes, np.float64)
    x0, y0 = np.quantile(b[:, 0], q), np.quantile(b[:, 1], q)
    x1, y1 = np.quantile(b[:, 0] + b[:, 2], 1 - q), np.quantile(b[:, 1] + b[:, 3], 1 - q)
    return float(x0), float(y0), float(x1), float(y1)
