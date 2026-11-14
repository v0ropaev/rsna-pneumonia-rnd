"""Decode CenterNet head outputs into per-image boxes (original px, xywh) and run batched inference.

Stored prediction tables are produced in two steps so that post-hoc variants never need re-inference:
1. RAW table: score = raw heatmap peak probability, box_scale 1.0; min_score, top-K and NMS act on this raw score.
2. Configured table = `rsna.posthoc.apply_posthoc(raw, img, decode.box_scale, decode.score_mode)`.
Gating multiplies every box of an image by the same cls probability, so it never changes which boxes survive
top-K / NMS; switching score_mode or box_scale offline on the stored table is therefore exact.
For a model with a cls head the table keeps `raw_score` next to `score`; the image table holds image_score
(cls prob if cls head, else max heatmap prob), max_box_score (max heatmap prob) and cls_prob (cls head only).
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torchvision.ops import nms

from .metric import IMAGE_SCORE_DECIMALS, round_preds
from .paths import ORIG_SIZE
from .posthoc import RAW_COL, apply_posthoc

Detections = list[tuple[np.ndarray, np.ndarray]]  # per image: boxes [k,4] xywh, scores [k]
PRED_COLS = ["patientId", "score", "x", "y", "width", "height"]


@torch.no_grad()
def decode(
    out: dict[str, torch.Tensor],
    topk: int = 10,
    nms_iou: float | None = 0.5,
    box_scale: float = 1.0,
    score_mode: str = "heatmap",
    min_score: float = 0.01,
    orig_size: int = ORIG_SIZE,
    return_raw: bool = False,
) -> list[tuple[np.ndarray, ...]]:
    """Heatmap peaks (3x3 max-pool) -> top-K -> boxes in original px -> clip -> min_score & NMS on the RAW
    heatmap score -> box_scale (around the center, clipped) -> cls gating. With return_raw: (boxes, scores, raw)."""
    if score_mode not in ("heatmap", "heatmap_x_cls"):
        raise ValueError(f"unknown score_mode {score_mode}")
    if score_mode == "heatmap_x_cls" and "cls" not in out:
        raise ValueError("score_mode heatmap_x_cls needs a model with cls_head")
    heat = torch.sigmoid(out["hm"].float())
    b, _, r, _ = heat.shape
    peaks = heat * (F.max_pool2d(heat, 3, stride=1, padding=1) == heat)
    raw, idx = peaks.view(b, -1).topk(min(topk, r * r))
    cy, cx = (idx // r).float(), (idx % r).float()
    gather = lambda t: t.flatten(2).gather(2, idx.unsqueeze(1).expand(-1, t.shape[1], -1))  # [B,C,K]
    wh, off = gather(out["wh"].float()).clamp(min=0), gather(out["off"].float())
    k = orig_size / r
    xc, yc = (cx + off[:, 0]) * k, (cy + off[:, 1]) * k
    w, h = wh[:, 0] * k, wh[:, 1] * k
    x1, y1 = (xc - w / 2).clamp(0, orig_size), (yc - h / 2).clamp(0, orig_size)
    x2, y2 = (xc + w / 2).clamp(0, orig_size), (yc + h / 2).clamp(0, orig_size)
    boxes = torch.stack([x1, y1, x2, y2], -1).cpu()  # [B,K,4] xyxy
    raw = raw.cpu()
    gate = torch.sigmoid(out["cls"].float()).view(b).cpu() if score_mode == "heatmap_x_cls" else None
    res: list[tuple[np.ndarray, ...]] = []
    for i, (bx, sc) in enumerate(zip(boxes, raw)):
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
        score = sc * gate[i] if gate is not None else sc
        item = (xywh.numpy().astype(np.float64), score.numpy().astype(np.float64))
        res.append(item + (sc.numpy().astype(np.float64),) if return_raw else item)
    return res


def decode_cfg(out: dict[str, torch.Tensor], cfg: dict[str, Any], **kw: Any) -> list[tuple[np.ndarray, ...]]:
    d = {**cfg["decode"], **kw}
    return decode(out, topk=d["topk"], nms_iou=d.get("nms_iou"), box_scale=d.get("box_scale", 1.0),
                  score_mode=d.get("score_mode", "heatmap"), min_score=d.get("min_score", 0.01),
                  return_raw=d.get("return_raw", False))


def image_outputs(out: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    """Image-level outputs: max_box_score (max heatmap prob = top-1 raw peak), cls_prob (cls head only) and
    image_score (cls_prob if the model has a cls head, else max_box_score)."""
    res = {"max_box_score": torch.sigmoid(out["hm"].float()).flatten(1).amax(1)}
    if "cls" in out:
        res["cls_prob"] = torch.sigmoid(out["cls"].float()).view(-1)
    res["image_score"] = res.get("cls_prob", res["max_box_score"])
    return res


def image_scores(out: dict[str, torch.Tensor]) -> torch.Tensor:
    """Image-level score: cls probability if the model has a cls head, else the max heatmap probability."""
    return image_outputs(out)["image_score"]


def _batches(model: torch.nn.Module, images: torch.Tensor | np.ndarray, device: torch.device, batch_size: int):
    model.eval()
    for i in range(0, len(images), batch_size):
        xb = torch.as_tensor(np.asarray(images[i : i + batch_size]))
        yield model(xb.to(device, non_blocking=True).unsqueeze(1).float().div_(255))


@torch.no_grad()
def predict(
    model: torch.nn.Module, images: torch.Tensor | np.ndarray, cfg: dict[str, Any],
    device: torch.device, batch_size: int = 64,
) -> tuple[Detections, np.ndarray]:
    """Online decode with the config's settings (float, unrounded). Returns detections and image scores."""
    dets: Detections = []
    img_scores = []
    for out in _batches(model, images, device, batch_size):
        dets += decode_cfg(out, cfg)
        img_scores.append(image_scores(out).cpu())
    return dets, torch.cat(img_scores).numpy().astype(np.float64)


@torch.no_grad()
def predict_raw(
    model: torch.nn.Module, images: torch.Tensor | np.ndarray, cfg: dict[str, Any],
    device: torch.device, batch_size: int = 64,
) -> tuple[Detections, dict[str, np.ndarray]]:
    """RAW detections (score_mode heatmap, box_scale 1.0; config topk / nms_iou / min_score) + image outputs."""
    dets: Detections = []
    img: dict[str, list[torch.Tensor]] = {}
    for out in _batches(model, images, device, batch_size):
        dets += decode_cfg(out, cfg, box_scale=1.0, score_mode="heatmap", return_raw=False)
        for key, v in image_outputs(out).items():
            img.setdefault(key, []).append(v.cpu())
    return dets, {key: torch.cat(v).numpy().astype(np.float64) for key, v in img.items()}


def to_frames(ids: list[str], dets: Detections, img_scores: np.ndarray | dict[str, np.ndarray],
              raw_col: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Prediction-table contract: (patientId, score, x, y, width, height[, raw_score]) and
    (patientId, image_score[, max_box_score, cls_prob]). `img_scores`: image_score array or image_outputs arrays.

    Already rounded to storage precision, so metrics on these frames equal metrics on the written CSVs.
    `raw_col` adds raw_score := score (the detections must be raw ones).
    """
    rows = [(pid, s, *b) for pid, (bx, sc, *_) in zip(ids, dets) for b, s in zip(bx, sc)]
    pred = round_preds(pd.DataFrame(rows, columns=PRED_COLS))
    if raw_col:
        pred[RAW_COL] = pred["score"]
    img = img_scores if isinstance(img_scores, dict) else {"image_score": img_scores}
    cols = [c for c in ("image_score", "max_box_score", "cls_prob") if c in img]
    img_df = pd.DataFrame({"patientId": ids, **{c: np.round(img[c], IMAGE_SCORE_DECIMALS) for c in cols}})
    return pred, img_df


def raw_frames(ids: list[str], dets: Detections, img: dict[str, np.ndarray]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """RAW prediction table (raw_score column when the model has a cls head) + image table, storage-rounded."""
    return to_frames(ids, dets, img, raw_col="cls_prob" in img)


def configured_frame(raw_df: pd.DataFrame, img_df: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    """The config's decode settings applied to a RAW table: identical to online decode + storage rounding."""
    d = cfg["decode"]
    return apply_posthoc(raw_df, img_df, d.get("box_scale", 1.0), d.get("score_mode", "heatmap"),
                         d.get("min_score", 0.01))


@torch.no_grad()
def predict_frames(
    model: torch.nn.Module, images: torch.Tensor | np.ndarray, ids: list[str], cfg: dict[str, Any],
    device: torch.device, batch_size: int = 64,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Inference -> (configured table, image table, RAW table), all storage-rounded."""
    dets, img = predict_raw(model, images, cfg, device, batch_size)
    raw_df, img_df = raw_frames(ids, dets, img)
    return configured_frame(raw_df, img_df, cfg), img_df, raw_df
