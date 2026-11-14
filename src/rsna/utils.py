"""Small shared helpers: seeding, device, config IO, git sha."""
from __future__ import annotations

import os
import random
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml

from .paths import ROOT


def seed_everything(seed: int) -> torch.Generator:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    g = torch.Generator()
    g.manual_seed(seed)
    return g


def get_device() -> torch.device:
    """Env RSNA_DEVICE=cpu|mps|cuda forces a device (e.g. CPU smoke runs while the GPU is busy); else mps > cuda > cpu."""
    forced = os.environ.get("RSNA_DEVICE", "").strip().lower()
    if forced:
        if forced not in ("cpu", "mps", "cuda"):
            raise ValueError(f"RSNA_DEVICE must be cpu|mps|cuda, got {forced!r}")
        if forced == "mps" and not torch.backends.mps.is_available():
            raise RuntimeError("RSNA_DEVICE=mps but MPS is not available")
        if forced == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("RSNA_DEVICE=cuda but CUDA is not available")
        return torch.device(forced)
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def load_config(path: str | Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


def save_config(cfg: dict[str, Any], path: str | Path) -> None:
    with open(path, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)


def flatten(d: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


CODE_PATHS = ("src", "configs", "scripts", "pyproject.toml", "uv.lock")


def git_revision(paths: tuple[str, ...] = CODE_PATHS) -> str:
    """Short HEAD sha + '-dirty' if code/config paths have staged, unstaged OR untracked changes.

    Uses `git status --porcelain`, restricted to `paths` so run outputs (results/, mlflow.db) do not count.
    'nocommit' = repository without commits, 'nogit' = git unavailable.
    """
    try:
        status = subprocess.check_output(["git", "status", "--porcelain", "--", *paths], cwd=ROOT, text=True,
                                         stderr=subprocess.DEVNULL)
    except Exception:
        return "nogit"
    dirty = "-dirty" if status.strip() else ""
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True,
                                      stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        return "nocommit" + dirty
    return sha + dirty
