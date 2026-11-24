"""HW3 code: split variants (synthetic metadata), input perturbations, seed-pooled group metrics."""
import numpy as np
import pandas as pd
import pytest

from rsna import hw3, split_variants
from rsna.perturb import lung_field, perturb
from rsna.split import make_split

from test_split import synthetic_meta


# ----------------------------------------------------------------------------- split variants

@pytest.fixture(scope="module")
def base() -> tuple[pd.DataFrame, pd.DataFrame]:
    meta = synthetic_meta(n_groups=900, seed=1)
    return meta, make_split(meta, seed=42)


def _groups(meta: pd.DataFrame, sp: pd.DataFrame, s: str) -> set:
    return set(meta.loc[sp["split"].to_numpy() == s, "nih_patient"])


def test_train_subsets_are_nested_grouped_and_keep_val_test(base) -> None:
    meta, sp0 = base
    subs = split_variants.train_subsets(meta, sp0)
    prev = None
    for pct in sorted(subs):  # 10, 20, 50
        sp = subs[pct]
        split_variants.check_variant(meta, sp0, sp)
        assert ((sp["split"] == "val") == (sp0["split"] == "val")).all()
        tr = set(sp.loc[sp["split"] == "train", "patientId"])
        assert tr <= set(sp0.loc[sp0["split"] == "train", "patientId"])
        if prev is not None:
            assert prev <= tr, "subsets must be nested"
        prev = tr
        share = len(tr) / (sp0["split"] == "train").sum()
        assert abs(share - pct / 100) < 0.06
        # a patient is either fully used or fully unused
        g = meta.assign(split=sp["split"].to_numpy())
        g = g[sp0["split"].to_numpy() == "train"]
        assert (g.groupby("nih_patient")["split"].nunique() == 1).all()


def test_resplit_keeps_test_and_protocol(base) -> None:
    meta, sp0 = base
    sp = split_variants.resplit(meta, sp0, seed=1)
    split_variants.check_variant(meta, sp0, sp)
    assert not (_groups(meta, sp, "train") & _groups(meta, sp, "val"))
    val_share = (sp["split"] == "val").sum() / (sp["split"] != "test").sum()
    assert abs(val_share - 3 / 17) < 0.03
    assert (sp["split"] != (sp0["split"])).any()  # it is a different partition


def test_leaky_split_moves_half_of_some_patients_and_keeps_train_size(base) -> None:
    meta, sp0 = base
    sp, roles = split_variants.leaky_split(meta, sp0, seed=0)
    split_variants.check_variant(meta, sp0, sp, allow_val_train_groups=True)
    assert (sp["split"] == "train").sum() == (sp0["split"] == "train").sum()
    r = roles.set_index("patientId")["role"]
    donors = r.index[r == "donor"]
    assert (sp.set_index("patientId").loc[donors, "split"] == "train").all()
    leaked_pat = set(roles.loc[roles["role"] == "leaked_eval", "nih_patient"])
    assert leaked_pat == set(roles.loc[roles["role"] == "donor", "nih_patient"])
    assert leaked_pat <= _groups(meta, sp, "train")          # leaked patients now have train images
    clean = set(roles.loc[roles["role"].isin(["clean_multi", "clean_single"]), "nih_patient"])
    assert not (clean & _groups(meta, sp, "train"))          # the control group stays clean
    with pytest.raises(AssertionError):
        split_variants.check_variant(meta, sp0, sp)          # the leak is visible to the default check


# ----------------------------------------------------------------------------- perturbations

def test_perturb_shapes_identity_and_monotone_noise() -> None:
    rng = np.random.default_rng(0)
    x = rng.integers(0, 256, (3, 64, 64)).astype(np.uint8)
    assert (perturb(x, "clean", None) == x).all()
    for fam, lvl in [("noise", 0.05), ("blur", 1.0), ("lowres", 32), ("jpeg", 20), ("contrast", 0.7), ("gamma", 1.4)]:
        y = perturb(x, fam, lvl)
        assert y.shape == x.shape and y.dtype == np.uint8
    d1 = np.abs(perturb(x, "noise", 0.01).astype(int) - x).mean()
    d2 = np.abs(perturb(x, "noise", 0.10).astype(int) - x).mean()
    assert d1 < d2
    assert (perturb(x, "noise", 0.05, seed=3) == perturb(x, "noise", 0.05, seed=3)).all()  # paired across models
    assert (perturb(x, "contrast", 1.0) == x).all() and (perturb(x, "lowres", 64) == x).all()


def test_mask_keeps_lung_field_and_fills_median() -> None:
    x = np.full((2, 256, 256), 50, np.uint8)
    x[:, :10, :10] = 255  # a "marker" in the corner
    y = perturb(x, "mask", (256, 256, 768, 768))  # 1024-px coords -> 64..192 on 256 px
    assert (y[:, 64:192, 64:192] == x[:, 64:192, 64:192]).all()
    assert (y[:, :10, :10] == 50).all()
    b = np.array([[100, 100, 200, 300], [500, 150, 250, 350], [10, 20, 30, 40]], float)
    x0, y0, x1, y1 = lung_field(b, q=0.0)
    assert (x0, y0, x1, y1) == (10, 20, 750, 500)


# ----------------------------------------------------------------------------- seed-pooled metrics

def _tab(ap, target, has, score, pid=None) -> pd.DataFrame:
    n = len(ap)
    return pd.DataFrame({"ap": ap, "target": target, "has_box": has, "cls_prob": score},
                        index=pd.Index(pid or [f"i{k}" for k in range(n)], name="patientId"))


def test_metric_terms_match_direct_computation(monkeypatch) -> None:
    monkeypatch.setattr(hw3, "patient_groups", lambda *a, **k: None)
    target = np.array([1, 1, 0, 0, 0, 1])
    has = np.array([True, False, True, False, False, True])
    ap = np.array([0.5, 0.0, 0.0, np.nan, np.nan, 1.0])  # negatives without a box are not scored
    t = _tab(ap, target, has, np.linspace(0, 1, 6))
    allm = np.ones(6, bool)
    r = hw3.masked_metric([t, t], allm, "map", n_boot=200)
    assert r["est"] == pytest.approx(np.nanmean(ap))
    assert hw3.masked_metric([t], allm, "fp_rate", n_boot=50)["est"] == pytest.approx(1 / 3)
    assert hw3.masked_metric([t], allm, "sens", n_boot=50)["est"] == pytest.approx(2 / 3)
    pi = 0.25
    std = hw3.masked_metric([t], allm, "std_map", n_boot=50, pi=pi)["est"]
    mp, fp = np.mean([0.5, 0.0, 1.0]), 1 / 3
    assert std == pytest.approx(pi * mp / (pi + (1 - pi) * fp))
    # at the group's own prevalence the standardized mAP equals the RSNA mAP of the group exactly
    own = hw3.masked_metric([t], allm, "std_map", n_boot=50, pi=0.5)["est"]
    assert own == pytest.approx(np.nanmean(ap))
    # zero events: an exact one-sided bound instead of a degenerate [0, 0]
    z = hw3.masked_metric([t], np.array([False, False, False, True, True, False]), "fp_rate", n_boot=50)
    assert z["est"] == 0 and z["lo"] == 0 and z["hi"] == pytest.approx(1 - 0.025 ** (1 / 2))
    d = hw3.paired_unit_diff([t], [t], allm, "map", n_boot=100)
    assert d["diff"] == 0 and d["lo"] == 0 and d["hi"] == 0


def test_group_table_and_diff(monkeypatch) -> None:
    monkeypatch.setattr(hw3, "patient_groups", lambda *a, **k: None)
    rng = np.random.default_rng(0)
    n = 400
    target = rng.random(n) < 0.3
    g = np.where(rng.random(n) < 0.5, "A", "B")
    has = np.where(target, rng.random(n) < np.where(g == "A", 0.8, 0.4), rng.random(n) < 0.1)
    ap = np.where(target, np.where(has, 0.6, 0.0), np.where(has, 0.0, np.nan))
    t = _tab(ap, target.astype(int), has, rng.random(n))
    t["grp"] = g
    tab = hw3.group_table([t], "grp", n_boot=200)
    assert list(tab["value"]) == ["A", "B"] and tab["n"].sum() == n
    a = tab.set_index("value")
    assert a.loc["A", "sens"] > a.loc["B", "sens"]
    d = hw3.group_diff([t], g == "A", g == "B", "sens", n_boot=300)
    assert d["diff"] == pytest.approx(a.loc["A", "sens"] - a.loc["B", "sens"])
    assert d["lo"] > 0
    # a difference-in-differences of identical model sets is exactly 0
    r = hw3.combo([(1.0, [t], g == "A", "map"), (-1.0, [t], g == "A", "map"), (-1.0, [t], g == "B", "map"),
                   (1.0, [t], g == "B", "map")], n_boot=100)
    assert r["est"] == pytest.approx(0) and r["lo"] == pytest.approx(0) and r["hi"] == pytest.approx(0)
