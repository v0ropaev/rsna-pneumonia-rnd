"""HW3 split variants derived from the committed split_v1.csv (robustness checks + the leakage experiment).

Every variant keeps the v1 TEST rows untouched (they stay "test" and are never read in HW3) and follows the v1
protocol: groups = NIH patient, strata = cls x min(n_boxes, 3) x view x sex (rsna.split.strata).
Rows that a variant removes from training get split = "unused" (rsna.dataset / rsna.evaluate ignore them).

1. train subsets (R1, train size):   data/splits/hw3/train_frac{50,20,10}.csv
   v1 train is cut into 10 stratified, patient-grouped chunks (StratifiedGroupKFold(10, shuffle, seed=0));
   10 % = chunk 0, 20 % = chunks 0-1, 50 % = chunks 0-4, so the subsets are NESTED. val and test == v1.
2. re-splits (R2, split variability):  data/splits/hw3/resplit_s{1,2,3}.csv
   the non-test pool (v1 train + val) is re-cut into 17 stratified, patient-grouped chunks with another seed;
   3 chunks -> val (= 3/17 of the pool = 15 % of all images, as in v1), 14 -> train. test == v1.
3. controlled leakage (L, RQ2):       data/splits/hw3/leak_s0.csv + leak_s0_roles.csv
   among v1-val NIH patients with >= 2 val images, a random half ("leaked" patients) donate floor(k/2) of their
   k val images to train; the rest of their images stay in val ("leaked_eval": their patient is now in train).
   The other multi-image val patients keep all their images in val ("clean_multi", the control group);
   single-image val patients are "clean_single". To keep the train size equal to v1, as many random v1-train
   images are set to "unused". Leakage effect = difference-in-differences of mAP (leaky model − v1 model)
   between leaked_eval and clean_multi images (scripts/analyze_hw3_leakage.py).

CLI: python -m rsna.split_variants [--out data/splits/hw3] [--force]
     (deterministic; refuses to overwrite a differing committed file unless --force)
"""
from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from . import paths
from .split import groups, load_metadata, strata

OUT = paths.SPLITS / "hw3"
FRACTIONS = {50: 5, 20: 2, 10: 1}  # percent of v1 train -> number of 10 %-chunks
SUBSET_SEED, N_SUBSET_CHUNKS = 0, 10
RESPLIT_SEEDS, N_POOL_CHUNKS, VAL_POOL_CHUNKS = (1, 2, 3), 17, (0, 1, 2)
LEAK_SEED = 0
SPLIT_VALUES = ("train", "val", "test", "unused")


def load_base(split_file: Path = paths.SPLIT_FILE) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(metadata in row order, v1 split aligned to it)."""
    meta = load_metadata()
    base = pd.read_csv(split_file, dtype={"patientId": str}).set_index("patientId").loc[meta["patientId"]].reset_index()
    return meta, base


def _sgkf_chunks(meta: pd.DataFrame, rows: np.ndarray, n: int, seed: int) -> np.ndarray:
    """Chunk id (0..n-1) for every row index in `rows`: stratified (rsna.split.strata), grouped by NIH patient."""
    y = strata(meta).to_numpy()[rows]
    g = groups(meta)[0].to_numpy()[rows]
    out = np.empty(len(rows), dtype=int)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", "The least populated class", UserWarning)
        for k, (_, te) in enumerate(StratifiedGroupKFold(n, shuffle=True, random_state=seed).split(np.zeros(len(y)), y, g)):
            out[te] = k
    return out


def _frame(meta: pd.DataFrame, split: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame({"patientId": meta["patientId"].to_numpy(), "split": split, "cv_fold": -1})


def train_subsets(meta: pd.DataFrame, base: pd.DataFrame, seed: int = SUBSET_SEED) -> dict[int, pd.DataFrame]:
    tr = np.flatnonzero(base["split"].to_numpy() == "train")
    chunk = _sgkf_chunks(meta, tr, N_SUBSET_CHUNKS, seed)
    out = {}
    for pct, k in FRACTIONS.items():
        split = base["split"].to_numpy().copy()
        split[tr[chunk >= k]] = "unused"
        out[pct] = _frame(meta, split)
    return out


def resplit(meta: pd.DataFrame, base: pd.DataFrame, seed: int) -> pd.DataFrame:
    split = base["split"].to_numpy().copy()
    pool = np.flatnonzero(split != "test")
    chunk = _sgkf_chunks(meta, pool, N_POOL_CHUNKS, seed)
    split[pool] = np.where(np.isin(chunk, VAL_POOL_CHUNKS), "val", "train")
    return _frame(meta, split)


def leaky_split(meta: pd.DataFrame, base: pd.DataFrame, seed: int = LEAK_SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(split, roles of the v1-val images: leaked_eval | donor | clean_multi | clean_single)."""
    rng = np.random.default_rng(seed)
    split = base["split"].to_numpy().copy()
    g = groups(meta)[0].to_numpy()
    val = np.flatnonzero(split == "val")
    vg = pd.Series(g[val], index=val)
    sizes = vg.value_counts()
    multi = np.sort(sizes.index[sizes >= 2].to_numpy())
    leaked = set(rng.choice(multi, len(multi) // 2, replace=False))
    role = pd.Series("clean_single", index=val, dtype=object)
    role[vg.isin(set(multi))] = "clean_multi"
    donors = []
    for p in sorted(leaked):
        rows = vg.index[vg == p].to_numpy()
        rows = rows[rng.permutation(len(rows))]
        k = len(rows) // 2
        donors.extend(rows[:k])
        role[rows[:k]] = "donor"
        role[rows[k:]] = "leaked_eval"
    donors = np.sort(np.array(donors, dtype=int))
    split[donors] = "train"
    tr = np.flatnonzero(base["split"].to_numpy() == "train")
    split[np.sort(rng.choice(tr, len(donors), replace=False))] = "unused"  # keep the train size of v1
    roles = pd.DataFrame({"patientId": meta["patientId"].to_numpy()[val], "nih_patient": g[val], "role": role.to_numpy()})
    return _frame(meta, split), roles


def check_variant(meta: pd.DataFrame, base: pd.DataFrame, sp: pd.DataFrame, allow_val_train_groups: bool = False) -> None:
    """Test rows unchanged; values valid; no NIH patient shared between train and val (unless the leak variant)."""
    assert (sp["patientId"].to_numpy() == meta["patientId"].to_numpy()).all()
    assert sp["split"].isin(SPLIT_VALUES).all()
    assert ((sp["split"] == "test").to_numpy() == (base["split"] == "test").to_numpy()).all(), "test rows changed"
    g = groups(meta)[0].to_numpy()
    sets = {s: set(g[sp["split"].to_numpy() == s]) for s in ("train", "val", "test")}
    assert not (sets["test"] & (sets["train"] | sets["val"])), "test patients leak into train/val"
    if not allow_val_train_groups:
        assert not (sets["train"] & sets["val"]), "train/val patient overlap"


def describe(meta: pd.DataFrame, sp: pd.DataFrame) -> dict:
    df = meta.assign(split=sp["split"].to_numpy())
    out = {}
    for s in ("train", "val", "unused"):
        d = df[df["split"] == s]
        if len(d):
            out[s] = {"n_images": len(d), "n_patients": int(d["nih_patient"].nunique()), "pos_%": round(100 * d["target"].mean(), 2),
                      "AP_%": round(100 * (d["view"] == "AP").mean(), 2),
                      "not_normal_%": round(100 * (d["cls"] == "No Lung Opacity / Not Normal").mean(), 2)}
    return out


def write(df: pd.DataFrame, path: Path, force: bool) -> None:
    if path.exists() and not force:
        old = pd.read_csv(path, dtype=str)
        if not old.equals(df.astype(str)):
            raise SystemExit(f"{path} exists and differs; refusing to overwrite (use --force)")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def build(out: Path = OUT, force: bool = False) -> dict:
    meta, base = load_base()
    summary: dict = {"base": "data/splits/split_v1.csv", "v1": describe(meta, base)}
    for pct, sp in train_subsets(meta, base).items():
        check_variant(meta, base, sp)
        assert ((sp["split"] == "val") == (base["split"] == "val")).all()
        write(sp, out / f"train_frac{pct}.csv", force)
        summary[f"train_frac{pct}"] = describe(meta, sp)
    for s in RESPLIT_SEEDS:
        sp = resplit(meta, base, s)
        check_variant(meta, base, sp)
        write(sp, out / f"resplit_s{s}.csv", force)
        d = describe(meta, sp)
        d["val_overlap_with_v1_val_%"] = round(100 * float(((sp["split"] == "val") & (base["split"] == "val")).sum()
                                                         / (sp["split"] == "val").sum()), 2)
        summary[f"resplit_s{s}"] = d
    sp, roles = leaky_split(meta, base)
    check_variant(meta, base, sp, allow_val_train_groups=True)
    write(sp, out / f"leak_s{LEAK_SEED}.csv", force)
    write(roles, out / f"leak_s{LEAK_SEED}_roles.csv", force)
    d = describe(meta, sp)
    rc = roles.merge(meta[["patientId", "target"]], on="patientId")
    d["roles"] = {r: {"n_images": int((rc["role"] == r).sum()), "n_patients": int(rc.loc[rc["role"] == r, "nih_patient"].nunique()),
                      "pos_%": round(100 * rc.loc[rc["role"] == r, "target"].mean(), 2)} for r in sorted(rc["role"].unique())}
    summary[f"leak_s{LEAK_SEED}"] = d
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    print(json.dumps(build(a.out, a.force), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
