#!/usr/bin/env bash
# HW1 baseline: trivial reference baselines + CenterNet-lite (configs/baseline.yaml) for 3 seeds, all on VAL.
# Test is touched only with EVAL_TEST=1 (final, once the protocol is frozen). Run from anywhere.
# Env: SEEDS="0 1 2", CONFIG=configs/baseline.yaml, EVAL_TEST=0|1, OVERWRITE=0|1 (retrain existing run names)
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
CONFIG=${CONFIG:-configs/baseline.yaml}
SEEDS=${SEEDS:-"0 1 2"}
NAME=$(basename "$CONFIG" .yaml)
OW=""; if [ "${OVERWRITE:-0}" = 1 ]; then OW=--overwrite; fi

$PY -m rsna.baselines --split val   # results/baseline_trivial/{empty,prior_boxes,prior_boxes_ap}/

runs=()
for s in $SEEDS; do
  run="results/${NAME}_s${s}"
  $PY -m rsna.train --config "$CONFIG" --seed "$s" --run-name "${NAME}_s${s}" $OW
  $PY -m rsna.evaluate --run "$run" --split val
  $PY -m rsna.evaluate compare --a "$run" --b results/baseline_trivial/prior_boxes_ap --split val
  runs+=("$run")
done
$PY -m rsna.evaluate summarize --runs "${runs[@]}" --split val --out "results/${NAME}_summary"

if [ "${EVAL_TEST:-0}" = 1 ]; then
  $PY -m rsna.baselines --split test
  for run in "${runs[@]}"; do $PY -m rsna.evaluate --run "$run" --split test; done
  $PY -m rsna.evaluate summarize --runs "${runs[@]}" --split test --out "results/${NAME}_summary"
fi
