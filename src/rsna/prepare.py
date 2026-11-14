"""Decode the RSNA training DICOMs once and build the processed-data contract.

Outputs (see SPEC): data/processed/metadata.csv, boxes.csv, images_{S}.npy (uint8 [N, S, S],
area-resized with PIL BOX), plus prepare_report.json with validation results.

    python -m rsna.prepare --sizes 256 384 [--workers 8]
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pydicom
from PIL import Image
from tqdm import tqdm

from .paths import BOXES, CLASS_INFO, METADATA, ORIG_SIZE, PROCESSED, TRAIN_DICOM_DIR, TRAIN_LABELS, image_cache

EXPECTED_LABEL_ROWS = 30227
EXPECTED_IMAGES = 26684
CLASSES = ("Lung Opacity", "No Lung Opacity / Not Normal", "Normal")


def resize_area(img: np.ndarray, size: int) -> np.ndarray:
    """Area downsampling of a uint8 2-D image to size x size.

    PIL BOX on float32 is exact area averaging; BOX on uint8 uses fixed-point math with a
    measured +0.24 gray-level upward bias, so we resize in float and round to nearest.
    """
    out = np.asarray(Image.fromarray(img.astype(np.float32)).resize((size, size), Image.Resampling.BOX))
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def decode(path: Path) -> tuple[np.ndarray, pydicom.Dataset]:
    """Decode one DICOM to uint8 grayscale where higher == brighter (MONOCHROME2 convention)."""
    ds = pydicom.dcmread(path)
    img = ds.pixel_array
    if img.dtype != np.uint8:  # not expected for this dataset; rescale defensively
        img = img.astype(np.float32)
        img = ((img - img.min()) / max(float(np.ptp(img)), 1e-6) * 255).round().astype(np.uint8)
    if ds.PhotometricInterpretation == "MONOCHROME1":
        img = 255 - img
    return img, ds


def _process(args: tuple[str, tuple[int, ...]]) -> tuple[dict[str, Any], list[np.ndarray]]:
    pid, sizes = args
    img, ds = decode(TRAIN_DICOM_DIR / f"{pid}.dcm")
    spacing = [float(v) for v in ds.get("PixelSpacing", [np.nan, np.nan])]
    meta = {
        "patientId": pid,
        "sex": str(ds.get("PatientSex", "")),
        "age": int(str(ds.get("PatientAge", "-1")).rstrip("Yy") or -1),
        "view": str(ds.get("ViewPosition", "")),
        "height": int(img.shape[0]),
        "width": int(img.shape[1]),
        "pixel_spacing": spacing[0],
        "_spacing_row_eq_col": bool(np.isclose(spacing[0], spacing[1])),
        "_photometric": str(ds.PhotometricInterpretation),
        "_ndim": int(img.ndim),
    }
    return meta, [resize_area(img, s) for s in sizes]


def load_labels() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Read and validate the label CSVs. Returns (per-patient table, boxes, report)."""
    labels = pd.read_csv(TRAIN_LABELS)
    cls = pd.read_csv(CLASS_INFO)
    rep: dict[str, Any] = {"label_rows": len(labels), "class_info_rows": len(cls)}
    assert len(labels) == EXPECTED_LABEL_ROWS, f"labels rows {len(labels)} != {EXPECTED_LABEL_ROWS}"

    box_cols = ["x", "y", "width", "height"]
    has_box = labels[box_cols].notna().all(axis=1)
    rep["rows_partial_nan_box"] = int((labels[box_cols].notna().any(axis=1) & ~has_box).sum())
    rep["rows_target_box_mismatch"] = int(((labels.Target == 1) != has_box).sum())
    rep["patients_mixed_target"] = int((labels.groupby("patientId").Target.nunique() > 1).sum())
    rep["duplicate_label_rows"] = int(labels.duplicated().sum())

    rep["class_info_duplicate_rows"] = int(cls.duplicated().sum())
    rep["class_info_conflicting_patients"] = int((cls.groupby("patientId")["class"].nunique() > 1).sum())
    cls = cls.drop_duplicates("patientId")
    unknown = set(cls["class"]) - set(CLASSES)
    assert not unknown, f"unexpected classes: {unknown}"

    boxes = labels.loc[labels.Target == 1, ["patientId", *box_cols]].reset_index(drop=True)
    per = labels.groupby("patientId").agg(target=("Target", "max")).reset_index()
    per["n_boxes"] = per.patientId.map(boxes.patientId.value_counts()).fillna(0).astype(int)
    per = per.merge(cls.rename(columns={"class": "cls"}), on="patientId", how="left", validate="1:1")
    rep["patients_missing_class"] = int(per.cls.isna().sum())
    rep["target_class_inconsistent"] = int(((per.target == 1) != (per.cls == "Lung Opacity")).sum())
    rep["unique_patients"] = len(per)
    rep["boxes"] = len(boxes)
    rep["non_positive_box_size"] = int(((boxes.width <= 0) | (boxes.height <= 0)).sum())
    rep["boxes_out_of_bounds"] = int(
        ((boxes.x < 0) | (boxes.y < 0) | (boxes.x + boxes.width > ORIG_SIZE) | (boxes.y + boxes.height > ORIG_SIZE)).sum()
    )
    assert len(per) == EXPECTED_IMAGES, f"unique patients {len(per)} != {EXPECTED_IMAGES}"
    return per.sort_values("patientId").reset_index(drop=True), boxes, rep


def build(sizes: list[int], workers: int) -> dict[str, Any]:
    t0 = time.time()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    per, boxes, rep = load_labels()
    pids = per.patientId.tolist()
    files = {p.stem for p in TRAIN_DICOM_DIR.glob("*.dcm")}
    rep["dicom_files"] = len(files)
    rep["labels_without_dicom"] = len(set(pids) - files)
    rep["dicom_without_labels"] = len(files - set(pids))
    assert rep["labels_without_dicom"] == 0, "some labelled patients have no DICOM"

    n = len(pids)
    tmp = {s: image_cache(s).with_suffix(".npy.tmp") for s in sizes}
    caches = {s: np.lib.format.open_memmap(tmp[s], mode="w+", dtype=np.uint8, shape=(n, s, s)) for s in sizes}
    metas: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        jobs = ((p, tuple(sizes)) for p in pids)
        for i, (meta, imgs) in enumerate(tqdm(ex.map(_process, jobs, chunksize=32), total=n, desc="decode")):
            assert meta["patientId"] == pids[i]
            metas.append(meta)
            for s, im in zip(sizes, imgs):
                caches[s][i] = im
    for s, arr in caches.items():
        arr.flush()
        del arr
    caches.clear()
    for s in sizes:
        os.replace(tmp[s], image_cache(s))

    m = pd.DataFrame(metas)
    odd = m[(m.height != ORIG_SIZE) | (m.width != ORIG_SIZE) | (m._photometric != "MONOCHROME2") | (m._ndim != 2)]
    rep["nonstandard_images"] = odd[["patientId", "height", "width", "_photometric"]].to_dict("records")
    rep["pixel_spacing_row_ne_col"] = int((~m._spacing_row_eq_col).sum())
    m = m.drop(columns=[c for c in m.columns if c.startswith("_")])
    meta = per.merge(m, on="patientId", how="left", validate="1:1")
    meta.insert(0, "idx", np.arange(n))
    if len(odd):  # explicit original->cache scale factors, only needed when sizes differ
        for s in sizes:
            meta[f"scale_x_{s}"] = s / meta.width
            meta[f"scale_y_{s}"] = s / meta.height
    cols = ["idx", "patientId", "target", "cls", "n_boxes", "sex", "age", "view", "height", "width", "pixel_spacing"]
    meta = meta[cols + [c for c in meta.columns if c not in cols]]
    meta.to_csv(METADATA, index=False)
    boxes.to_csv(BOXES, index=False)

    rep.update(
        n_images=n,
        positives=int(meta.target.sum()),
        class_counts=meta.cls.value_counts().to_dict(),
        view_counts=meta.view.value_counts().to_dict(),
        sex_counts=meta.sex.value_counts().to_dict(),
        n_boxes_counts=meta.n_boxes.value_counts().sort_index().to_dict(),
        age_min=int(meta.age.min()),
        age_max=int(meta.age.max()),
        age_over_100=int((meta.age > 100).sum()),
        age_over_100_values=sorted(meta.age[meta.age > 100].tolist()),
        pixel_spacing_range=[float(meta.pixel_spacing.min()), float(meta.pixel_spacing.max())],
        sizes=sizes,
        file_mb={p.name: round(p.stat().st_size / 2**20, 1) for p in [METADATA, BOXES, *map(image_cache, sizes)]},
        runtime_s=round(time.time() - t0, 1),
    )
    rep = {k: (int(v) if isinstance(v, np.integer) else v) for k, v in rep.items()}
    (PROCESSED / "prepare_report.json").write_text(json.dumps(rep, indent=2, default=int))
    return rep


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sizes", type=int, nargs="+", default=[256, 384])
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    rep = build(sorted(set(a.sizes)), a.workers)
    print(json.dumps(rep, indent=2, default=int))
    problems = [k for k in ("target_class_inconsistent", "patients_mixed_target", "rows_target_box_mismatch",
                            "patients_missing_class", "class_info_conflicting_patients") if rep[k]]
    if rep["nonstandard_images"] or problems:
        print(f"WARNING: nonstandard images={len(rep['nonstandard_images'])}, inconsistencies={problems}")


if __name__ == "__main__":
    main()
