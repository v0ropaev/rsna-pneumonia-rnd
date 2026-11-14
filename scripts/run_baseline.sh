#!/usr/bin/env bash
# HW1 baseline: trivial reference baselines + CenterNet-lite (configs/baseline.yaml) for 3 seeds, all on VAL.
# Test is touched only with EVAL_TEST=1 (final, once the protocol is frozen). Run from anywhere.
# Env: SEEDS="0 1 2", CONFIG=configs/baseline.yaml, EVAL_TEST=0|1,
#      OVERWRITE=0|1 (1 = retrain every seed from scratch; 0 = a run that already has results/<run>/meta.json is NOT
#      retrained, its metrics are recomputed from the stored val predictions, so a fresh clone only re-evaluates).
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src  # always this checkout's code (the venv may be shared between checkouts)
PY=.venv/bin/python
CONFIG=${CONFIG:-configs/baseline.yaml}
SEEDS=${SEEDS:-"0 1 2"}
NAME=$(basename "$CONFIG" .yaml)
OVERWRITE=${OVERWRITE:-0}

$PY -m rsna.baselines --split val   # results/baseline_trivial/{empty,prior_boxes,prior_boxes_ap}/
$PY -m rsna.evaluate compare --a results/baseline_trivial/prior_boxes_ap --b results/baseline_trivial/prior_boxes --split val

runs=()
for s in $SEEDS; do
  run="results/${NAME}_s${s}"
  if [ "$OVERWRITE" = 1 ]; then
    $PY -m rsna.train --config "$CONFIG" --seed "$s" --run-name "${NAME}_s${s}" --overwrite
  elif [ -f "$run/meta.json" ]; then
    echo "[baseline] $run is already trained: re-evaluating its stored val predictions (OVERWRITE=1 retrains)"
  else
    $PY -m rsna.train --config "$CONFIG" --seed "$s" --run-name "${NAME}_s${s}"
  fi
  $PY -m rsna.evaluate --run "$run" --split val
  $PY -m rsna.evaluate compare --a "$run" --b results/baseline_trivial/prior_boxes_ap --split val
  runs+=("$run")
done
$PY -m rsna.evaluate summarize --runs "${runs[@]}" --split val --out "results/${NAME}_summary"
# seed-to-seed noise floor (RQ4): paired Δ between two seeds of the same config on the same val images
for ((i = 0; i < ${#runs[@]}; i++)); do
  for ((j = i + 1; j < ${#runs[@]}; j++)); do
    $PY -m rsna.evaluate compare --a "${runs[$j]}" --b "${runs[$i]}" --split val
  done
done
$PY scripts/plot_hw1_summary.py

if [ "${EVAL_TEST:-0}" = 1 ]; then
  for run in "${runs[@]}"; do  # test predictions need the checkpoint (gitignored: present only where it was trained)
    if [ ! -f "$run/test_predictions.csv" ] && [ ! -f "runs/$(basename "$run")/best.pt" ]; then
      echo "[baseline] runs/$(basename "$run")/best.pt missing: retrain with OVERWRITE=1 before EVAL_TEST=1"; exit 1
    fi
  done
  $PY -m rsna.baselines --split test
  for run in "${runs[@]}"; do $PY -m rsna.evaluate --run "$run" --split test; done
  $PY -m rsna.evaluate summarize --runs "${runs[@]}" --split test --out "results/${NAME}_summary"
fi
