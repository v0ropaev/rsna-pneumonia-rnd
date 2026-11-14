"""Decode CenterNet head outputs into per-image boxes (original px, xywh) and run batched inference."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torchvision.ops import nms

from .metric import IMAGE_SCORE_DECIMALS, round_preds
from .paths import ORIG_SIZE

Detections = list[tuple[np.ndarray, np.ndarray]]  # per image: boxes [k,4] xywh, scores [k]


@torch.no_grad()
def decode(
    out: dict[str, torch.Tensor],
    topk: int = 10,
    nms_iou: float | None = 0.5,
    box_scale: float = 1.0,
    score_mode: str = "heatmap",
    min_score: float = 0.01,
    orig_size: int = ORIG_SIZE,
) -> Detections:
    """Heatmap peaks (3x3 max-pool) -> top-K -> boxes in original px -> clip -> NMS -> box_scale -> cls gating."""
    heat = torch.sigmoid(out["hm"].float())
    b, _, r, _ = heat.shape
    peaks = heat * (F.max_pool2d(heat, 3, stride=1, padding=1) == heat)
    scores, idx = peaks.view(b, -1).topk(min(topk, r * r))
    cy, cx = (idx // r).float(), (idx % r).float()
    gather = lambda t: t.flatten(2).gather(2, idx.unsqueeze(1).expand(-1, t.shape[1], -1))  # [B,C,K]
    wh, off = gather(out["wh"].float()).clamp(min=0), gather(out["off"].float())
    k = orig_size / r
    xc, yc = (cx + off[:, 0]) * k, (cy + off[:, 1]) * k
    w, h = wh[:, 0] * k, wh[:, 1] * k
    x1, y1 = (xc - w / 2).clamp(0, orig_size), (yc - h / 2).clamp(0, orig_size)
    x2, y2 = (xc + w / 2).clamp(0, orig_size), (yc + h / 2).clamp(0, orig_size)
    boxes = torch.stack([x1, y1, x2, y2], -1)  # [B,K,4] xyxy
    if score_mode == "heatmap_x_cls":
        if "cls" not in out:
            raise ValueError("score_mode heatmap_x_cls needs a model with cls_head")
        scores = scores * torch.sigmoid(out["cls"].float()).view(b, 1)
    elif score_mode != "heatmap":
        raise ValueError(f"unknown score_mode {score_mode}")
    boxes, scores = boxes.cpu(), scores.cpu()
    res: Detections = []
    for bx, sc in zip(boxes, scores):
        keep = (sc >= min_score) & (bx[:, 2] > bx[:, 0]) & (bx[:, 3] > bx[:, 1])
        bx, sc = bx[keep], sc[keep]
        if nms_iou and len(bx) > 1:
            keep = nms(bx, sc, nms_iou)
            bx, sc = bx[keep], sc[keep]
        xywh = torch.cat([bx[:, :2], bx[:, 2:] - bx[:, :2]], 1)
        if box_scale != 1.0:
            ctr = xywh[:, :2] + xywh[:, 2:] / 2
            lo = (ctr - xywh[:, 2:] * box_scale / 2).clamp(0, orig_size)
            hi = (ctr + xywh[:, 2:] * box_scale / 2).clamp(0, orig_size)
            xywh = torch.cat([lo, hi - lo], 1)
        res.append((xywh.numpy().astype(np.float64), sc.numpy().astype(np.float64)))
    return res


def decode_cfg(out: dict[str, torch.Tensor], cfg: dict[str, Any]) -> Detections:
    d = cfg["decode"]
    return decode(out, topk=d["topk"], nms_iou=d.get("nms_iou"), box_scale=d.get("box_scale", 1.0),
                  score_mode=d.get("score_mode", "heatmap"), min_score=d.get("min_score", 0.01))


def image_scores(out: dict[str, torch.Tensor]) -> torch.Tensor:
    """Image-level score: cls probability if the model has a cls head, else the max heatmap probability."""
    if "cls" in out:
        return torch.sigmoid(out["cls"].float()).view(-1)
    return torch.sigmoid(out["hm"].float()).flatten(1).amax(1)


@torch.no_grad()
def predict(
    model: torch.nn.Module, images: torch.Tensor | np.ndarray, cfg: dict[str, Any],
    device: torch.device, batch_size: int = 64,
) -> tuple[Detections, np.ndarray]:
    """Inference over uint8 images [N,S,S] (RAM tensor / array / memmap). Returns detections and image scores."""
    model.eval()
    dets: Detections = []
    img_scores = []
    for i in range(0, len(images), batch_size):
        xb = torch.as_tensor(np.asarray(images[i : i + batch_size]))
        xb = xb.to(device, non_blocking=True).unsqueeze(1).float().div_(255)
        out = model(xb)
        dets += decode_cfg(out, cfg)
        img_scores.append(image_scores(out).cpu())
    return dets, torch.cat(img_scores).numpy().astype(np.float64)


def to_frames(ids: list[str], dets: Detections, img_scores: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Prediction-table contract: (patientId, score, x, y, width, height) and (patientId, image_score).

    Already rounded to storage precision, so metrics on these frames equal metrics on the written CSVs.
    """
    rows = [(pid, s, *b) for pid, (bx, sc) in zip(ids, dets) for b, s in zip(bx, sc)]
    pred = round_preds(pd.DataFrame(rows, columns=["patientId", "score", "x", "y", "width", "height"]))
    return pred, pd.DataFrame({"patientId": ids, "image_score": np.round(img_scores, IMAGE_SCORE_DECIMALS)})
