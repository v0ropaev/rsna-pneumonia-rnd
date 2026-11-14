"""CenterNet-lite: torchvision ResNet backbone + FPN-lite neck to stride 8 + anchor-free heads, and its loss."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
_C345 = {"resnet18": (128, 256, 512), "resnet34": (128, 256, 512), "resnet50": (512, 1024, 2048)}


def _head(cin: int, mid: int, cout: int, bias: float = 0.0) -> nn.Sequential:
    h = nn.Sequential(nn.Conv2d(cin, mid, 3, padding=1), nn.ReLU(inplace=True), nn.Conv2d(mid, cout, 1))
    for m in h:
        if isinstance(m, nn.Conv2d):
            nn.init.normal_(m.weight, std=0.001)
            nn.init.constant_(m.bias, 0.0)
    nn.init.constant_(h[-1].bias, bias)
    return h


class CenterNetLite(nn.Module):
    """Input: float [B,1,S,S] in [0,1]. Output dict: hm [B,1,R,R] logits, wh [B,2,R,R], off [B,2,R,R], (cls [B])."""

    stride = 8

    def __init__(self, arch: str = "resnet18", pretrained: bool = True, neck_channels: int = 128,
                 head_channels: int = 128, cls_head: bool = False) -> None:
        super().__init__()
        weights = "IMAGENET1K_V1" if pretrained else None
        r = getattr(torchvision.models, arch)(weights=weights)
        self.stem = nn.Sequential(r.conv1, r.bn1, r.relu, r.maxpool, r.layer1)
        self.layer2, self.layer3, self.layer4 = r.layer2, r.layer3, r.layer4
        c3, c4, c5 = _C345[arch]
        n = neck_channels
        self.lat3, self.lat4, self.lat5 = nn.Conv2d(c3, n, 1), nn.Conv2d(c4, n, 1), nn.Conv2d(c5, n, 1)
        self.smooth = nn.Sequential(nn.Conv2d(n, n, 3, padding=1), nn.BatchNorm2d(n), nn.ReLU(inplace=True))
        self.hm = _head(n, head_channels, 1, bias=-2.19)
        self.wh = _head(n, head_channels, 2)
        self.off = _head(n, head_channels, 2)
        self.cls = nn.Linear(c5, 1) if cls_head else None
        self.register_buffer("mean", torch.tensor(IMAGENET_MEAN).view(1, 3, 1, 1), persistent=False)
        self.register_buffer("std", torch.tensor(IMAGENET_STD).view(1, 3, 1, 1), persistent=False)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        x = (x.expand(-1, 3, -1, -1) - self.mean) / self.std
        c3 = self.layer2(self.stem(x))
        c4 = self.layer3(c3)
        c5 = self.layer4(c4)
        p = self.lat5(c5)
        p = self.lat4(c4) + F.interpolate(p, size=c4.shape[-2:], mode="nearest")
        p = self.lat3(c3) + F.interpolate(p, size=c3.shape[-2:], mode="nearest")
        p = self.smooth(p)
        out = {"hm": self.hm(p), "wh": self.wh(p), "off": self.off(p)}
        if self.cls is not None:
            out["cls"] = self.cls(c5.mean((2, 3))).squeeze(1)
        return out


def build_model(cfg: dict[str, Any]) -> CenterNetLite:
    m = cfg["model"]
    return CenterNetLite(m["arch"], m.get("pretrained", True), m.get("neck_channels", 128),
                         m.get("head_channels", 128), m.get("cls_head", False))


def focal_loss(logits: torch.Tensor, gt: torch.Tensor, alpha: float = 2.0, beta: float = 4.0) -> torch.Tensor:
    """CenterNet modified focal loss, normalised by the number of positive (gt == 1) cells, clamped >= 1."""
    p = torch.sigmoid(logits).clamp(1e-4, 1 - 1e-4)
    pos = gt.eq(1).float()
    pos_loss = torch.log(p) * (1 - p) ** alpha * pos
    neg_loss = torch.log(1 - p) * p**alpha * (1 - gt) ** beta * (1 - pos)
    return -(pos_loss.sum() + neg_loss.sum()) / pos.sum().clamp(min=1)


def _masked_l1(pred: torch.Tensor, gt: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """CenterNet RegL1Loss: mean absolute error over masked elements (both channels)."""
    return (F.l1_loss(pred * mask, gt * mask, reduction="sum")) / (mask.sum() * pred.shape[1] + 1e-4)


def centernet_loss(out: dict[str, torch.Tensor], tgt: dict[str, torch.Tensor],
                   cfg_loss: dict[str, Any]) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    parts = {
        "hm": focal_loss(out["hm"], tgt["hm"], cfg_loss.get("hm_alpha", 2.0), cfg_loss.get("hm_beta", 4.0)),
        "wh": _masked_l1(out["wh"], tgt["wh"], tgt["mask"]),
        "off": _masked_l1(out["off"], tgt["off"], tgt["mask"]),
    }
    total = parts["hm"] + cfg_loss["wh_weight"] * parts["wh"] + cfg_loss["off_weight"] * parts["off"]
    if "cls" in out:
        parts["cls"] = F.binary_cross_entropy_with_logits(out["cls"], tgt["cls"])
        total = total + cfg_loss.get("cls_weight", 1.0) * parts["cls"]
    return total, parts


def save_checkpoint(path: str | Path, model: nn.Module, cfg: dict[str, Any], **extra: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "config": cfg, **extra}, path)


def load_checkpoint(path: str | Path, device: torch.device | str = "cpu") -> tuple[CenterNetLite, dict[str, Any]]:
    """Rebuild the model from the checkpoint's resolved config (no ImageNet download) and load weights."""
    ck = torch.load(path, map_location="cpu", weights_only=False)
    cfg = ck["config"]
    model = build_model({**cfg, "model": {**cfg["model"], "pretrained": False}})
    model.load_state_dict(ck["model"])
    return model.to(device).eval(), cfg
