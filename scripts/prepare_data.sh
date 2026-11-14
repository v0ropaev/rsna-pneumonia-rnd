#!/usr/bin/env bash
# Build processed data (caches + metadata), the fixed split, and EDA figures. Run from repo root.
set -euo pipefail
# NIH patient mapping (for patient-grouped split) is optional: data/external/nih_mapping.csv
cd "$(dirname "$0")/.."
PY=.venv/bin/python
SIZES=${SIZES:-"256 384"}
WORKERS=${WORKERS:-8}

test "$(find data/raw/stage_2_train_images -name '*.dcm' | wc -l | tr -d ' ')" = 26684 \
  || { echo "raw DICOMs missing: run scripts/download_data.sh" >&2; exit 1; }

# shellcheck disable=SC2086
$PY -m rsna.prepare --sizes $SIZES --workers "$WORKERS"
$PY -m rsna.split   # merges NIH ids into metadata.csv; writes data/splits/split_v1.csv (committed, deterministic)
$PY -m rsna.eda     # writes reports/figures/eda_*.png + reports/eda_stats.json
