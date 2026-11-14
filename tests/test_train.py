"""Tests for train.py run bookkeeping (step plan, run-dir reuse), the experiments ledger and git_revision."""
from __future__ import annotations

import csv
import subprocess
from pathlib import Path

import pytest

from rsna import utils
from rsna.tracking import LEDGER_COLUMNS, append_ledger
from rsna.train import plan_steps, prepare_dirs


def test_plan_steps_max_steps_is_exact() -> None:
    assert plan_steps(64, 16, 6, None) == (4, 24, 6)
    assert plan_steps(64, 16, 6, 150) == (4, 150, 38)  # more than epochs * spe: epochs grow
    assert plan_steps(1000, 16, 6, 10) == (62, 10, 1)
    with pytest.raises(ValueError, match="batch_size"):
        plan_steps(10, 16, 6, 5)


def test_prepare_dirs_refuses_reuse_and_overwrite_wipes(tmp_path: Path) -> None:
    out, run = tmp_path / "results" / "r", tmp_path / "runs" / "r"
    prepare_dirs(out, run, overwrite=False)  # fresh name
    assert out.is_dir() and not run.exists()
    prepare_dirs(out, run, overwrite=False)  # empty dir is fine
    (out / "test_metrics.json").write_text("{}")
    run.mkdir(parents=True)
    (run / "best.pt").write_text("old")
    with pytest.raises(FileExistsError):
        prepare_dirs(out, run, overwrite=False)
    assert (out / "test_metrics.json").exists()
    prepare_dirs(out, run, overwrite=True)
    assert out.is_dir() and not any(out.iterdir()) and not run.exists()


def test_ledger_records_overrides_and_migrates_old_header(tmp_path: Path) -> None:
    path = tmp_path / "experiments.csv"
    old_cols = [c for c in LEDGER_COLUMNS if c != "overrides"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=old_cols)
        w.writeheader()
        w.writerow({"run_name": "old", "seed": 0})
    append_ledger({"run_name": "abl", "config": "configs/baseline.yaml", "overrides": "aug.hflip=true;train.lr=1e-3",
                   "seed": 1}, path)
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert reader.fieldnames == LEDGER_COLUMNS
    assert [r["run_name"] for r in rows] == ["old", "abl"]
    assert rows[0]["overrides"] == "" and rows[1]["overrides"] == "aug.hflip=true;train.lr=1e-3"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=repo, check=True,
                   capture_output=True)


def test_git_revision_sees_staged_and_untracked_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(utils, "ROOT", tmp_path)
    assert utils.git_revision() == "nogit"
    _git(tmp_path, "init", "-q")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x = 1\n")
    assert utils.git_revision() == "nocommit-dirty"
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "init")
    clean = utils.git_revision()
    assert clean and "dirty" not in clean and clean not in ("nogit", "nocommit")
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "out.csv").write_text("run output\n")  # outputs do not make the code dirty
    assert utils.git_revision() == clean
    (tmp_path / "src" / "a.py").write_text("x = 2\n")
    _git(tmp_path, "add", "src/a.py")  # staged only: `git diff --quiet` would miss this
    assert utils.git_revision() == clean + "-dirty"
    _git(tmp_path, "commit", "-qm", "c2")
    (tmp_path / "src" / "new.py").write_text("")  # untracked code
    assert utils.git_revision().endswith("-dirty")


@pytest.mark.parametrize("cfg_name", ["configs/baseline.yaml", "configs/hw2/full.yaml"])
def test_validate_logs_no_gating_map_only_for_cls_models(cfg_name: str) -> None:
    """cls models also report the epoch's val mAP WITHOUT gating (to size the no_gating epoch-selection bias);
    baseline validation is unchanged (no extra key)."""
    from types import SimpleNamespace

    import numpy as np
    import pandas as pd
    import torch

    from rsna.model import build_model
    from rsna.train import load_config, validate

    cfg = load_config(Path(__file__).resolve().parents[1] / cfg_name)
    cfg = {**cfg, "model": {**cfg["model"], "pretrained": False}}
    torch.manual_seed(0)
    model = build_model(cfg)
    n = 6
    meta = pd.DataFrame({"patientId": [f"i{k}" for k in range(n)], "target": [1, 0, 1, 0, 1, 0]})
    data = SimpleNamespace(meta=meta, images=torch.randint(0, 255, (n, 64, 64), dtype=torch.uint8))
    gt = {f"i{k}": (np.array([[300.0, 300.0, 300.0, 300.0]]) if k % 2 == 0 else np.zeros((0, 4))) for k in range(n)}
    v = validate(model, data, np.arange(n), cfg, torch.device("cpu"), gt)
    assert ("val_map_heatmap" in v) == bool(cfg["model"]["cls_head"])
    if "val_map_heatmap" in v:
        assert 0.0 <= v["val_map_heatmap"] <= 1.0
