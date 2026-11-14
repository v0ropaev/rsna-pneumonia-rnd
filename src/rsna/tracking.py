"""Experiment tracking: MLflow (sqlite store in the repo) + the flat results/experiments.csv ledger."""
from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any

from . import paths
from .utils import flatten

EXPERIMENTS_CSV = paths.RESULTS / "experiments.csv"
LEDGER_COLUMNS = ["run_name", "date", "git_sha", "config", "overrides", "seed", "hypothesis",
                  "best_epoch", "val_map", "val_thr", "val_auc", "train_min"]


class Tracker:
    """Thin MLflow wrapper; `enabled=False` turns every call into a no-op."""

    def __init__(self, cfg: dict[str, Any], run_name: str, tags: dict[str, str], enabled: bool = True) -> None:
        self.enabled = enabled
        if not enabled:
            return
        os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
        import mlflow

        self.mlflow = mlflow
        mlflow.set_tracking_uri(paths.MLFLOW_URI)
        name = cfg.get("meta", {}).get("experiment", "rsna-pneumonia")
        if mlflow.get_experiment_by_name(name) is None:  # pin artifacts to <repo>/mlruns regardless of CWD
            mlflow.create_experiment(name, artifact_location=(paths.ROOT / "mlruns").as_uri())
        mlflow.set_experiment(name)
        self.run = mlflow.start_run(run_name=run_name, tags=tags)
        params = {k: ("null" if v is None else str(v))[:500] for k, v in flatten(cfg).items() if k != "meta.hypothesis"}
        mlflow.log_params(params)
        hyp = cfg.get("meta", {}).get("hypothesis", "")
        if hyp:
            mlflow.set_tag("mlflow.note.content", hyp)
            mlflow.log_text(hyp, "hypothesis.txt")

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        if self.enabled:
            self.mlflow.log_metrics({k: float(v) for k, v in metrics.items()}, step=step)

    def log_dir(self, path: Path) -> None:
        if self.enabled:
            self.mlflow.log_artifacts(str(path))

    def end(self, status: str = "FINISHED") -> None:
        if self.enabled:
            self.mlflow.end_run(status=status)

    @property
    def run_id(self) -> str:
        return self.run.info.run_id if self.enabled else ""


def append_ledger(row: dict[str, Any], path: Path = EXPERIMENTS_CSV) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():  # migrate a ledger written with an older column set (missing columns stay empty)
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            old, header = list(reader), reader.fieldnames
        if header != LEDGER_COLUMNS:
            with open(path, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS, extrasaction="ignore")
                w.writeheader()
                w.writerows(old)
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)
