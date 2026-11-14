"""Data access for training: metadata + split + RAM image cache, and fast in-process batching.

On macOS DataLoader workers use spawn and must re-open the cache; for a 1.7 GB uint8 RAM tensor plain
indexing in the main process is faster (measured, see train.py docstring), so that is the default path.
`RSNADataset` + `collate` remain for `train.num_workers > 0`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import numpy as np
import pandas as pd
import torch

from . import paths


@dataclass
class Data:
    meta: pd.DataFrame          # metadata.csv (+ split column), row i == cache index i
    images: torch.Tensor        # uint8 [N,S,S] in RAM
    boxes: list[np.ndarray]     # per cache index: xywh [k,4] original px
    image_size: int

    def indices(self, split: str) -> np.ndarray:
        return self.meta.index[self.meta["split"] == split].to_numpy()


def temporary_split(meta: pd.DataFrame, seed: int = 0) -> pd.Series:
    """Random 70/15/15 split for smoke tests only (never written to data/splits/)."""
    rng = np.random.default_rng(seed)
    u = rng.random(len(meta))
    return pd.Series(np.where(u < 0.7, "train", np.where(u < 0.85, "val", "test")), index=meta.index)


def load_data(image_size: int, split_file: str | None = None, smoke: bool = False) -> Data:
    meta = pd.read_csv(paths.METADATA)
    assert (meta["idx"].to_numpy() == np.arange(len(meta))).all(), "metadata idx must equal row order"
    split_path = paths.ROOT / split_file if split_file else paths.SPLIT_FILE
    if split_path.exists():
        split = pd.read_csv(split_path, usecols=["patientId", "split"])
        meta = meta.merge(split, on="patientId", how="left", validate="one_to_one")
        assert meta["split"].notna().all(), f"patients missing in {split_path}"
    elif smoke:
        meta["split"] = temporary_split(meta)
    else:
        raise FileNotFoundError(f"{split_path} not found (use --smoke for a temporary in-memory split)")
    bdf = pd.read_csv(paths.BOXES)
    grouped = {pid: g[["x", "y", "width", "height"]].to_numpy(np.float64) for pid, g in bdf.groupby("patientId")}
    empty = np.zeros((0, 4), np.float64)
    boxes = [grouped.get(pid, empty) for pid in meta["patientId"]]
    images = torch.from_numpy(np.load(paths.image_cache(image_size)))  # full load into RAM
    assert images.shape == (len(meta), image_size, image_size) and images.dtype == torch.uint8
    return Data(meta, images, boxes, image_size)


def iterate_batches(data: Data, idx: np.ndarray, batch_size: int, shuffle: bool,
                    generator: torch.Generator | None = None, drop_last: bool = True,
                    ) -> Iterator[tuple[torch.Tensor, list[np.ndarray], np.ndarray]]:
    """Yield (uint8 images [B,S,S] on CPU, boxes list, cache indices) straight from the RAM tensor."""
    order = idx[torch.randperm(len(idx), generator=generator).numpy()] if shuffle else idx
    stop = len(order) - (len(order) % batch_size if drop_last else 0)
    for i in range(0, stop, batch_size):
        b = np.sort(order[i : i + batch_size])  # sorted gather is cache-friendlier; order inside a batch is irrelevant
        yield data.images[torch.from_numpy(b)], [data.boxes[j] for j in b], b


class RSNADataset(torch.utils.data.Dataset):
    """Picklable dataset over the memory-mapped cache (for DataLoader workers)."""

    def __init__(self, image_size: int, idx: np.ndarray, boxes: list[np.ndarray]) -> None:
        self.image_size, self.idx, self.boxes = image_size, idx, boxes
        self._arr: np.ndarray | None = None

    def __len__(self) -> int:
        return len(self.idx)

    def __getitem__(self, i: int) -> tuple[torch.Tensor, np.ndarray, int]:
        if self._arr is None:
            self._arr = np.load(paths.image_cache(self.image_size), mmap_mode="r")
        j = int(self.idx[i])
        return torch.from_numpy(np.array(self._arr[j])), self.boxes[j], j


def collate(batch: list[tuple[torch.Tensor, np.ndarray, int]]) -> tuple[torch.Tensor, list[np.ndarray], np.ndarray]:
    return torch.stack([b[0] for b in batch]), [b[1] for b in batch], np.array([b[2] for b in batch])
