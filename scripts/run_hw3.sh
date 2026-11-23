#!/usr/bin/env bash
# HW3: robustness retrainings of the HW2 solution (configs/hw2/full.yaml, unchanged) + the val-only analyses.
# Only ONE factor changes per check, via --set data.split_file=... (the config is otherwise identical to Full):
#   R1 train size  : hw3_frac{50,20,10}_s{0,1}  data/splits/hw3/train_frac{50,20,10}.csv (nested patient-grouped subsets
#                    of v1 train; val == v1 val); reference = full_s{0,1} (100 %) from HW2
#   R2 re-split    : hw3_resplit{1,2,3}_s0       data/splits/hw3/resplit_s{1,2,3}.csv (non-test pool re-cut with the v1
#                    protocol; test untouched); reference = full_s0 on split_v1
#   L  leakage     : hw3_leak_s{0,1}             data/splits/hw3/leak_s0.csv (controlled patient leakage, RQ2);
#                    reference = full_s{0,1} on the same eval images
# Every run is tracked in MLflow experiment "rsna-pneumonia-hw3" (--set meta.experiment=...). Names start with hw3_,
# so the HW2 report (rsna.report) ignores them. After training, per run: evaluate val -> posthoc tune box_scale ->
# variant "tuned" (the HW2 primary pipeline; box_scale tuned on the run's OWN val). TEST is never read in HW3.
# Then the analyses (val only; each skips what is not trained yet), see reports/HW3.md:
#   scripts/analyze_hw3_errors.py      (§1 typical errors, §2 slices: Full s0-s2 @tuned on v1 val)
#   scripts/analyze_hw3_shortcut.py    (§2.4 / RQ3 view shortcut: masking outside the lung field, inference only)
#   scripts/analyze_hw3_noise.py       (§3.3 input perturbations at inference: Full s0-s2 checkpoints)
#   scripts/analyze_hw3_robustness.py  (§3.1 train size, §3.2 re-split)
#   scripts/analyze_hw3_leakage.py     (§4.4 / RQ2 controlled leakage)
# Env: QUEUE="frac20:0 ..." (replace the queue), DRY_RUN=0|1, TRAIN=0 (analyses only), RSNA_DEVICE (cpu|mps|cuda),
#      ANALYSIS_DEVICE (device of the inference-only analyses; default cpu, so they can run next to training).
# Logs: logs/run_hw3_<timestamp>.log + logs/<run>.train.log (gitignored); copies in results/logs/hw3/. Resumable.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src
PY=.venv/bin/python
CFG=configs/hw2/full.yaml
QUEUE=${QUEUE:-"frac20:0 frac50:0 resplit1:0 leak:0 frac10:0 frac20:1 frac50:1 leak:1 resplit2:0 frac10:1 resplit3:0"}
DRY_RUN=${DRY_RUN:-0}
TRAIN=${TRAIN:-1}
ANALYSIS_DEVICE=${ANALYSIS_DEVICE:-cpu}
PRIMARY=tuned
mkdir -p logs results/logs/hw3
LOG="logs/run_hw3_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1

if [ "$DRY_RUN" != 1 ]; then
  mkdir logs/run_hw3.lock 2>/dev/null || { echo "logs/run_hw3.lock exists: another run_hw3.sh is running (or remove it)"; exit 1; }
  trap 'rmdir logs/run_hw3.lock' EXIT
fi

say() { echo "[hw3 $(date +%H:%M:%S)] $*"; }
run() {
  say "\$ $*"
  if [ "$DRY_RUN" = 1 ]; then return 0; fi
  local t0=$SECONDS
  "$@"
  say "  done in $(( (SECONDS - t0) / 60 )) min $(( (SECONDS - t0) % 60 )) s"
}
skip() { say "skip ($1 exists)"; }
step() { local marker=$1; shift; if [ -f "$marker" ]; then skip "$marker"; else run "$@"; fi; }

split_of() {  # queue key -> split file
  case $1 in
    frac50|frac20|frac10) echo "data/splits/hw3/train_${1}.csv" ;;
    resplit1|resplit2|resplit3) echo "data/splits/hw3/resplit_s${1#resplit}.csv" ;;
    leak) echo "data/splits/hw3/leak_s0.csv" ;;
    *) echo "unknown queue key $1" >&2; exit 1 ;;
  esac
}

step "data/splits/hw3/summary.json" $PY -m rsna.split_variants  # deterministic; refuses to change committed files
say "log $LOG; queue: $QUEUE; device: ${RSNA_DEVICE:-auto}; analyses on $ANALYSIS_DEVICE; DRY_RUN=$DRY_RUN TRAIN=$TRAIN"

if [ "$TRAIN" = 1 ]; then
  for it in $QUEUE; do
    k=${it%%:*} s=${it#*:}
    name="hw3_${k}_s${s}" sf=$(split_of "$k")
    say "=== $name ($CFG, data.split_file=$sf) ==="
    if [ -f "results/$name/meta.json" ]; then
      skip "results/$name/meta.json"
    else
      ow=()
      if [ -e "results/$name" ] || [ -e "runs/$name" ]; then ow=(--overwrite); say "unfinished $name: retraining with --overwrite"; fi
      say "\$ $PY -m rsna.train --config $CFG --seed $s --run-name $name --set data.split_file=$sf --set meta.experiment=rsna-pneumonia-hw3 ${ow[*]+"${ow[*]}"}"
      if [ "$DRY_RUN" != 1 ]; then
        t0=$SECONDS
        $PY -m rsna.train --config "$CFG" --seed "$s" --run-name "$name" --set "data.split_file=$sf" \
          --set meta.experiment=rsna-pneumonia-hw3 ${ow[@]+"${ow[@]}"} 2>&1 | tee "logs/$name.train.log"
        sed "s#$(pwd)/##g" "logs/$name.train.log" > "results/logs/hw3/$name.train.log"  # relative paths only
        say "  trained in $(( (SECONDS - t0) / 60 )) min"
      fi
    fi
    r="results/$name"
    step "$r/val_metrics.json" $PY -m rsna.evaluate --run "$r" --split val
    step "$r/posthoc/box_scale.json" $PY -m rsna.posthoc tune --run "$r"
    step "$r/posthoc/$PRIMARY/val_metrics.json" $PY -m rsna.posthoc variant --run "$r" --name "$PRIMARY" --box-scale tuned --score-mode keep
  done
fi

# ----------------------------------------------------------------------------- analyses (val only)
say "=== analyses (val only) ==="
for sc in analyze_hw3_errors analyze_hw3_shortcut analyze_hw3_noise analyze_hw3_robustness analyze_hw3_leakage; do
  if [ -f "scripts/$sc.py" ]; then
    RSNA_DEVICE=$ANALYSIS_DEVICE run $PY "scripts/$sc.py"
  fi
done
if [ "$DRY_RUN" != 1 ]; then sed "s#$(pwd)/##g" "$LOG" > "results/logs/hw3/$(basename "$LOG")"; fi
say "finished; log $LOG"
