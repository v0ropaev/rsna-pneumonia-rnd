"""Split tests: synthetic data (always run) + the committed split_v1.csv (skipped if data is absent)."""
import numpy as np
import pandas as pd
import pytest

from rsna import paths
from rsna.split import check_split, make_split, strata


def synthetic_meta(n_groups: int = 600, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    sizes = rng.integers(1, 8, n_groups)  # several images per patient, like NIH
    g = np.repeat(np.arange(n_groups), sizes).astype(str)
    n = len(g)
    n_boxes = rng.choice([0, 1, 2, 3], n, p=[0.75, 0.1, 0.13, 0.02])
    cls = np.where(n_boxes > 0, "Lung Opacity", rng.choice(["Normal", "No Lung Opacity / Not Normal"], n))
    sex = np.repeat(rng.choice(["M", "F"], n_groups), sizes)
    return pd.DataFrame({"patientId": [f"p{i}" for i in range(n)], "target": (n_boxes > 0).astype(int),
                         "cls": cls, "n_boxes": n_boxes, "view": rng.choice(["AP", "PA"], n), "sex": sex,
                         "age": rng.integers(1, 90, n), "nih_patient": g})


@pytest.fixture(scope="module")
def meta() -> pd.DataFrame:
    return synthetic_meta()


def test_no_group_leakage(meta: pd.DataFrame) -> None:
    sp = make_split(meta, seed=42)
    check_split(meta, sp)  # asserts groups disjoint across splits and CV folds
    df = meta.merge(sp, on="patientId")
    sets = {s: set(df.loc[df["split"] == s, "nih_patient"]) for s in ("train", "val", "test")}
    assert not (sets["train"] & sets["val"]) and not (sets["train"] & sets["test"]) and not (sets["val"] & sets["test"])


def test_check_split_detects_leak(meta: pd.DataFrame) -> None:
    sp = make_split(meta, seed=42)
    df = meta.merge(sp, on="patientId")
    multi = df.groupby("nih_patient").filter(lambda x: len(x) > 1).index[0]
    sp.loc[multi, "split"] = "val" if sp.loc[multi, "split"] != "val" else "test"
    sp.loc[multi, "cv_fold"] = -1
    with pytest.raises(AssertionError):
        check_split(meta, sp)


def test_proportions(meta: pd.DataFrame) -> None:
    df = meta.merge(make_split(meta, seed=42), on="patientId")
    share = df["split"].value_counts(normalize=True)
    assert abs(share["train"] - 0.70) < 0.02 and abs(share["val"] - 0.15) < 0.02 and abs(share["test"] - 0.15) < 0.02
    pos = df.groupby("split")["target"].mean()
    assert pos.max() - pos.min() < 0.03
    tr = df[df["split"] == "train"]
    assert set(tr["cv_fold"]) == set(range(5)) and (df.loc[df["split"] != "train", "cv_fold"] == -1).all()


def test_deterministic(meta: pd.DataFrame) -> None:
    pd.testing.assert_frame_equal(make_split(meta, seed=42), make_split(meta, seed=42))
    assert not make_split(meta, seed=42)["split"].equals(make_split(meta, seed=1)["split"])


def test_falls_back_to_patient_id(meta: pd.DataFrame) -> None:
    m = meta.drop(columns="nih_patient")
    check_split(m, make_split(m, seed=42))


@pytest.mark.skipif(not (paths.SPLIT_FILE.exists() and paths.METADATA.exists()), reason="data not prepared")
def test_committed_split_v1() -> None:
    meta = pd.read_csv(paths.METADATA, dtype={"nih_patient": str})
    sp = pd.read_csv(paths.SPLIT_FILE)
    assert list(sp.columns) == ["patientId", "split", "cv_fold"] and len(sp) == len(meta) == 26684
    check_split(meta, sp)
    df = meta.merge(sp, on="patientId")
    share = df["split"].value_counts(normalize=True)
    assert abs(share["train"] - 0.70) < 0.005 and abs(share["val"] - 0.15) < 0.005
    for col in ("target", "view", "sex"):
        rates = pd.crosstab(df["split"], df[col], normalize="index")
        assert (rates.max() - rates.min()).max() < 0.01, col  # within 1pp across splits
    st = pd.crosstab(df["split"], strata(df), normalize="index")
    assert (st.max() - st.min()).max() < 0.01
    # regenerating with the same seed reproduces the committed file exactly
    pd.testing.assert_frame_equal(make_split(meta, seed=42), sp, check_dtype=False)
