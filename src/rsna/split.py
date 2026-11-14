"""Fixed patient-grouped, stratified train/val/test split + CV folds inside train.

Procedure (deterministic for a given seed):
1. Group = NIH patient (data/external/nih_mapping.csv) if available, else RSNA patientId.
   73% of RSNA images belong to NIH patients with >1 image, so grouping by patientId leaks.
2. Stratum = cls x min(n_boxes, 3) x view x sex (20 non-empty strata; sex added because without it
   the test split drifted by ~4pp in sex share).
3. StratifiedGroupKFold(n_splits=20, shuffle=True, seed) -> 20 chunks of ~5%;
   chunks 0-2 -> test, 3-5 -> val, 6-19 -> train (70/15/15).
4. StratifiedGroupKFold(n_splits=5, shuffle=True, seed) on train -> cv_fold 0..4; val/test rows get cv_fold = -1.

The committed split_v1.csv is protected: if a regenerated split differs from it (e.g. the NIH mapping is
missing, so grouping falls back to patientId), the CLI refuses to overwrite it unless --force.

CLI: python -m rsna.split [--seed 42] [--out data/splits/split_v1.csv] [--force]
"""
from __future__ import annotations

import argparse
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from . import paths

NIH_MAPPING = paths.EXTERNAL / "nih_mapping.csv"
N_CHUNKS, TEST_CHUNKS, VAL_CHUNKS, N_FOLDS = 20, (0, 1, 2), (3, 4, 5), 5
SPLITS = ("train", "val", "test")


def load_metadata(merge_nih: bool = True) -> pd.DataFrame:
    """metadata.csv; merges nih_image/nih_patient into it (and rewrites the file) if the mapping exists."""
    meta = pd.read_csv(paths.METADATA, dtype={"nih_patient": str})
    if not merge_nih or "nih_patient" in meta.columns or not NIH_MAPPING.exists():
        return meta
    nih = pd.read_csv(NIH_MAPPING, dtype=str)
    meta = meta.merge(nih, on="patientId", how="left", validate="one_to_one")
    assert meta["nih_patient"].notna().all(), "patients missing in nih_mapping.csv"
    tmp = paths.METADATA.with_suffix(".csv.tmp")
    meta.to_csv(tmp, index=False)
    os.replace(tmp, paths.METADATA)
    print(f"merged nih_image/nih_patient into {paths.METADATA.relative_to(paths.ROOT)}")
    return meta


def strata(meta: pd.DataFrame) -> pd.Series:
    return meta["cls"] + "|" + meta["n_boxes"].clip(upper=3).astype(str) + "|" + meta["view"] + "|" + meta["sex"]


def groups(meta: pd.DataFrame) -> tuple[pd.Series, str]:
    if "nih_patient" in meta.columns:
        return meta["nih_patient"].astype(str), "nih_patient"
    return meta["patientId"], "patientId"


def make_split(meta: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Return DataFrame[patientId, split, cv_fold] in metadata row order."""
    y, (g, _) = strata(meta).to_numpy(), groups(meta)
    g = g.to_numpy()
    chunk, fold = np.empty(len(meta), dtype=int), np.full(len(meta), -1, dtype=int)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", "The least populated class", UserWarning)  # rare n_boxes>=3 strata
        sgkf = StratifiedGroupKFold(N_CHUNKS, shuffle=True, random_state=seed)
        for k, (_, te) in enumerate(sgkf.split(np.zeros(len(y)), y, g)):
            chunk[te] = k
        split = np.where(np.isin(chunk, TEST_CHUNKS), "test", np.where(np.isin(chunk, VAL_CHUNKS), "val", "train"))
        tr = np.flatnonzero(split == "train")
        sgkf = StratifiedGroupKFold(N_FOLDS, shuffle=True, random_state=seed)
        for k, (_, te) in enumerate(sgkf.split(np.zeros(len(tr)), y[tr], g[tr])):
            fold[tr[te]] = k
    return pd.DataFrame({"patientId": meta["patientId"].to_numpy(), "split": split, "cv_fold": fold})


def check_split(meta: pd.DataFrame, split: pd.DataFrame) -> None:
    """Assert disjoint groups across splits and across CV folds; fail loudly on leakage."""
    df = meta.merge(split, on="patientId", validate="one_to_one")
    g, _ = groups(df)
    assert len(df) == len(meta) and df["split"].isin(SPLITS).all()
    per_group = df.assign(g=g).groupby("g")
    assert (per_group["split"].nunique() == 1).all(), "group leakage across splits"
    tr = df["split"] == "train"
    assert df.loc[tr, "cv_fold"].between(0, N_FOLDS - 1).all() and (df.loc[~tr, "cv_fold"] == -1).all()
    assert (df[tr].assign(g=g[tr]).groupby("g")["cv_fold"].nunique() == 1).all(), "group leakage across CV folds"


def summary(meta: pd.DataFrame, split: pd.DataFrame, by: str = "split") -> pd.DataFrame:
    """Per-split sizes and distribution (% within split) of target, cls, view, sex, n_boxes."""
    df = meta.merge(split, on="patientId")
    g, _ = groups(df)
    out = {"n_images": df.groupby(by).size(), "n_groups": df.assign(g=g).groupby(by)["g"].nunique(),
           "share_%": df.groupby(by).size() / len(df) * 100, "pos_%": df.groupby(by)["target"].mean() * 100,
           "age_median": df.groupby(by)["age"].median()}
    for col in ("cls", "view", "sex"):
        for v, s in pd.crosstab(df[by], df[col], normalize="index").items():
            out[f"{col}={v}_%"] = s * 100
    for v, s in pd.crosstab(df[by], df["n_boxes"].clip(upper=3), normalize="index").items():
        out[f"n_boxes={v}{'+' if v == 3 else ''}_%"] = s * 100
    return pd.DataFrame(out).T.round(2)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=paths.SPLIT_FILE)
    ap.add_argument("--force", action="store_true", help="overwrite an existing split file that differs")
    args = ap.parse_args()
    meta = load_metadata()
    _, group_col = groups(meta)
    split = make_split(meta, args.seed)
    check_split(meta, split)
    if args.out.exists() and not args.force:
        old = pd.read_csv(args.out).set_index("patientId").reindex(split["patientId"])
        n_diff = int((old["split"].to_numpy() != split["split"].to_numpy()).sum()
                     + (old["cv_fold"].to_numpy() != split["cv_fold"].to_numpy()).sum())
        if n_diff:
            raise SystemExit(f"{args.out} exists and differs in {n_diff} fields (grouped by {group_col}); "
                             "refusing to overwrite the committed split. Use --force to replace it.")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    split.to_csv(args.out, index=False)
    pd.set_option("display.width", 160)
    print(f"grouped by {group_col}; seed {args.seed}; wrote {args.out}")
    print(summary(meta, split)[list(SPLITS)].to_string())
    tr = split[split["split"] == "train"]
    print("\nCV folds inside train:")
    print(summary(meta[meta["patientId"].isin(tr["patientId"])], tr, by="cv_fold").to_string())
    print("\nOK: zero group overlap across splits and folds")


if __name__ == "__main__":
    main()
