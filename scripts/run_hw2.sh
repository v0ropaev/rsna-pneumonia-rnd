#!/usr/bin/env bash
# HW2: train the 2x2 factorial (baseline from HW1 + b_aug, b_cls, full) and derive the post-hoc variants, all on VAL.
# Queue order puts the most informative runs first: full s0, b_cls s0, b_aug s0, full s1, b_cls s1, b_aug s1, full s2
# (baseline_s0..2 come from scripts/run_baseline.sh). Resumable: every step is skipped when its output exists; a run
# dir without meta.json (crashed / interrupted training) is retrained with --overwrite.
# Per run, after training:
#   evaluate val -> posthoc tune box_scale (run's own score_mode; two-sided default grid, + cross-fitted gain) ->
#   variant "tuned" (VAL-tuned box_scale, the primary result) -> runs with a cls head: "no_gating" (score_mode heatmap,
#   box_scale tuned separately for it) and "no_boxscale" (box_scale 1.0) -> paired val comparisons vs baseline_s<seed>
#   (when that run exists): as trained vs B for every config (box_scale 1.0 on both sides: the trained factors only),
#   plus full:tuned vs B (the headline Full − B, which includes I3; its val Δ also includes the box_scale selection).
#   B = HW1 baseline as trained (box_scale 1.0) by design; rsna.report's 2x2 uses the as-trained tables of all cells.
# Then val summaries + rsna.report + the §7 error/mechanism analyses (scripts/plot_hw2_errors.py,
# scripts/analyze_hw2_mechanism.py; val only). TEST only with EVAL_TEST=1 (once, at the very end): every run and variant incl.
# baseline seeds, test summaries, paired test Full vs B per seed, report --with-test. Nothing is selected on test.
# Env: SEEDS="0 1 2" (keep only queue items with these seeds), QUEUE="full:0 b_cls:0 ..." (replace the queue),
#      BASELINE_SEEDS="0 1 2", EVAL_TEST=0|1, DRY_RUN=0|1 (print the plan, run nothing), RSNA_DEVICE (cpu|mps|cuda).
# Logs: logs/run_hw2_<timestamp>.log (everything) + logs/<run>.train.log (gitignored); copies cited by reports/HW2.md
# are kept, with relative paths, in results/logs/ (versioned). Run from anywhere.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src  # always this checkout's code (the venv may be shared between checkouts)
PY=.venv/bin/python
QUEUE=${QUEUE:-"full:0 b_cls:0 b_aug:0 full:1 b_cls:1 b_aug:1 full:2"}
SEEDS=${SEEDS:-"0 1 2"}
BASELINE_SEEDS=${BASELINE_SEEDS:-"0 1 2"}
EVAL_TEST=${EVAL_TEST:-0}
DRY_RUN=${DRY_RUN:-0}
PRIMARY=tuned
mkdir -p logs
LOG="logs/run_hw2_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1

if [ "$DRY_RUN" != 1 ]; then  # one writer at a time: two copies would retrain the same run names
  mkdir logs/run_hw2.lock 2>/dev/null || { echo "logs/run_hw2.lock exists: another run_hw2.sh is running (or remove it)"; exit 1; }
  trap 'rmdir logs/run_hw2.lock' EXIT
fi

say() { echo "[hw2 $(date +%H:%M:%S)] $*"; }
run() {  # run a command (or only print it with DRY_RUN=1), with timing
  say "\$ $*"
  if [ "$DRY_RUN" = 1 ]; then return 0; fi
  local t0=$SECONDS
  "$@"
  say "  done in $(( (SECONDS - t0) / 60 )) min $(( (SECONDS - t0) % 60 )) s"
}
skip() { say "skip ($1 exists)"; }
step() {  # step MARKER CMD...: run CMD unless the output file MARKER already exists (resumability)
  local marker=$1; shift
  if [ -f "$marker" ]; then skip "$marker"; else run "$@"; fi
}
has_cls() { grep -Eq '^ *cls_head: *true' "$1"; }  # $1 = config.yaml

# ----------------------------------------------------------------------------- queue
items=()
for it in $QUEUE; do
  for s in $SEEDS; do
    if [ "${it#*:}" = "$s" ]; then items+=("$it"); fi
  done
done
say "log $LOG; queue: ${items[*]:-<empty>}; device: ${RSNA_DEVICE:-auto}; EVAL_TEST=$EVAL_TEST DRY_RUN=$DRY_RUN"

post_val() {  # $1 = run name, $2 = config file, $3 = seed
  local name=$1 cfg=$2 seed=$3 r="results/$1"
  step "$r/val_metrics.json" $PY -m rsna.evaluate --run "$r" --split val
  step "$r/posthoc/box_scale.json" $PY -m rsna.posthoc tune --run "$r"
  step "$r/posthoc/$PRIMARY/val_metrics.json" $PY -m rsna.posthoc variant --run "$r" --name "$PRIMARY" --box-scale tuned --score-mode keep
  if has_cls "$cfg"; then
    step "$r/posthoc/box_scale_heatmap.json" $PY -m rsna.posthoc tune --run "$r" --score-mode heatmap
    step "$r/posthoc/no_gating/val_metrics.json" $PY -m rsna.posthoc variant --run "$r" --name no_gating --box-scale tuned --score-mode heatmap
    step "$r/posthoc/no_boxscale/val_metrics.json" $PY -m rsna.posthoc variant --run "$r" --name no_boxscale --box-scale 1.0 --score-mode keep
  fi
  if [ -f "results/baseline_s$seed/meta.json" ]; then
    step "results/comparisons/${name}__vs__baseline_s${seed}__val.json" \
      $PY -m rsna.evaluate compare --a "$r" --b "results/baseline_s$seed" --split val
    if [ "${name%_s*}" = full ]; then
      step "results/comparisons/${name}@${PRIMARY}__vs__baseline_s${seed}__val.json" \
        $PY -m rsna.evaluate compare --a "$r:$PRIMARY" --b "results/baseline_s$seed" --split val
    fi
  else
    say "no results/baseline_s$seed yet: val comparison vs baseline skipped"
  fi
}

for it in ${items[@]+"${items[@]}"}; do
  c=${it%%:*} s=${it#*:}
  name="${c}_s${s}" cfg="configs/hw2/$c.yaml"
  [ -f "$cfg" ] || { say "unknown config $cfg"; exit 1; }
  say "=== $name ($cfg) ==="
  if [ -f "results/$name/meta.json" ]; then
    skip "results/$name/meta.json"
    if [ "$EVAL_TEST" = 1 ] && [ ! -f "runs/$name/best.pt" ] && [ ! -f "results/$name/test_metrics.json" ]; then
      say "WARNING: runs/$name/best.pt missing: test evaluation of $name will fail"
    fi
  else
    ow=()
    if [ -e "results/$name" ] || [ -e "runs/$name" ]; then
      say "results/$name or runs/$name exists without a finished training: retraining with --overwrite"
      ow=(--overwrite)
    fi
    say "\$ $PY -m rsna.train --config $cfg --seed $s --run-name $name ${ow[*]+"${ow[*]}"} > logs/$name.train.log"
    if [ "$DRY_RUN" != 1 ]; then
      t0=$SECONDS
      $PY -m rsna.train --config "$cfg" --seed "$s" --run-name "$name" ${ow[@]+"${ow[@]}"} 2>&1 | tee "logs/$name.train.log"
      say "  trained in $(( (SECONDS - t0) / 60 )) min"
    fi
  fi
  post_val "$name" "$cfg" "$s"
done

# ----------------------------------------------------------------------------- summaries (val)
existing() {  # existing finished runs of config $1 (in seed order)
  local found=() s
  for s in 0 1 2 3 4; do
    if [ -f "results/${1}_s$s/meta.json" ]; then found+=("results/${1}_s$s"); fi
  done
  echo "${found[@]+"${found[@]}"}"
}
summ() {  # $1 = split, $2 = out dir, $3 = suffix (":variant" or ""), rest = run dirs; needs <split>_metrics.json
  local split=$1 dest=$2 suf=$3 specs=() r d; shift 3
  for r in "$@"; do
    d=$r
    if [ -n "$suf" ]; then d="$r/posthoc/${suf#:}"; fi
    if [ -f "$d/${split}_metrics.json" ]; then specs+=("$r$suf"); fi
  done
  if [ ${#specs[@]} -ge 1 ]; then
    run $PY -m rsna.evaluate summarize --runs "${specs[@]}" --split "$split" --out "$dest"
  fi
}
summaries() {  # $1 = split
  local c runs
  for c in b_aug b_cls full; do
    runs=$(existing "$c")
    if [ -z "$runs" ]; then continue; fi
    # shellcheck disable=SC2086
    summ "$1" "results/hw2_summary/$c" "" $runs
    # shellcheck disable=SC2086
    summ "$1" "results/hw2_summary/${c}@$PRIMARY" ":$PRIMARY" $runs
    if [ "$c" != b_aug ]; then
      # shellcheck disable=SC2086
      summ "$1" "results/hw2_summary/${c}@no_gating" ":no_gating" $runs
      # shellcheck disable=SC2086
      summ "$1" "results/hw2_summary/${c}@no_boxscale" ":no_boxscale" $runs
    fi
  done
}
say "=== val summaries ==="
summaries val
run $PY -m rsna.report --primary-variant "$PRIMARY"
run $PY scripts/plot_hw2_errors.py        # §7 figure + results/hw2_summary/error_decomposition.md (val only)
run $PY scripts/analyze_hw2_mechanism.py  # §7 matched-operating-point checks -> results/hw2_summary/mechanism.md (val only)

# ----------------------------------------------------------------------------- test (final, once)
if [ "$EVAL_TEST" = 1 ]; then
  say "=== TEST (final; box_scale, score_mode and thresholds all come from val) ==="
  for s in $BASELINE_SEEDS; do
    r="results/baseline_s$s"
    if [ ! -f "$r/meta.json" ]; then say "missing $r: no test for it"; continue; fi
    step "$r/test_metrics.json" $PY -m rsna.evaluate --run "$r" --split test
  done
  for c in b_aug b_cls full; do
    for r in $(existing "$c"); do
      step "$r/test_metrics.json" $PY -m rsna.evaluate --run "$r" --split test
      for v in "$PRIMARY" no_gating no_boxscale; do
        [ -f "$r/posthoc/$v/variant.json" ] || continue
        step "$r/posthoc/$v/test_metrics.json" $PY -m rsna.evaluate --run "$r" --split test --variant "$v"
      done
    done
  done
  b_runs=()
  for s in $BASELINE_SEEDS; do
    if [ -f "results/baseline_s$s/test_metrics.json" ]; then b_runs+=("results/baseline_s$s"); fi
  done
  if [ ${#b_runs[@]} -ge 1 ]; then
    run $PY -m rsna.evaluate summarize --runs "${b_runs[@]}" --split test --out results/baseline_summary
  fi
  summaries test
  for s in $BASELINE_SEEDS; do  # the one pre-registered test contrast: Full (tuned) vs B, seed-matched
    if [ -f "results/full_s$s/posthoc/$PRIMARY/test_metrics.json" ] && [ -f "results/baseline_s$s/test_metrics.json" ]; then
      run $PY -m rsna.evaluate compare --a "results/full_s$s:$PRIMARY" --b "results/baseline_s$s" --split test
    fi
  done
  run $PY -m rsna.report --primary-variant "$PRIMARY" --with-test
fi
say "finished; log $LOG"
