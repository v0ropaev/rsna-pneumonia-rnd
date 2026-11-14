#!/usr/bin/env bash
# Download the RSNA Pneumonia Detection Challenge data into data/raw/ and the RSNA->NIH mapping into
# data/external/ (needed for the patient-grouped split). Run from anywhere; idempotent (skips what is present).
#
# Official path: Kaggle CLI (needs ~/.kaggle/kaggle.json or KAGGLE_USERNAME/KAGGLE_KEY and the competition
# rules accepted on kaggle.com). Fallback: public Hugging Face mirror of the same zip.
# Env: FORCE_MIRROR=1 skips Kaggle; KEEP_ZIP=1 keeps the 3.7 GB zip after unzipping.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
RAW=data/raw
EXT=data/external
COMP=rsna-pneumonia-detection-challenge
ZIP="$RAW/$COMP.zip"
MIRROR="https://huggingface.co/datasets/kellly/RSNA-Pneumonia-Detection/resolve/main/$COMP.zip"
NIH_URL="s3.amazonaws.com/east1.public.rsna.org/AI/2018/pneumonia-challenge-dataset-mappings_2018.json"
NIH_JSON="$EXT/pneumonia-challenge-dataset-mappings_2018.json"
NIH_SHA256=803ce79e3bc9c66d3631738e91e62e1175730e98ad1415e8dc4d6292ba10bf27
N_TRAIN=26684
mkdir -p "$RAW" "$EXT"

count_dcm() { find "$RAW/stage_2_train_images" -name '*.dcm' 2>/dev/null | wc -l | tr -d ' '; }
sha256() { shasum -a 256 "$1" 2>/dev/null | cut -d' ' -f1 || sha256sum "$1" | cut -d' ' -f1; }

# ---- 1. competition data -------------------------------------------------------------------------
if [ "$(count_dcm)" = "$N_TRAIN" ] && [ -f "$RAW/stage_2_train_labels.csv" ]; then
  echo "[download] $RAW already has $N_TRAIN train DICOMs, skipping"
else
  if [ ! -f "$ZIP" ]; then
    if [ "${FORCE_MIRROR:-0}" != 1 ] && command -v kaggle >/dev/null \
       && { [ -f ~/.kaggle/kaggle.json ] || [ -n "${KAGGLE_KEY:-}" ]; } \
       && kaggle competitions download -c "$COMP" -p "$RAW"; then
      echo "[download] got $ZIP via Kaggle CLI"
    else
      echo "[download] Kaggle CLI unavailable or failed -> mirror $MIRROR"
      curl -fL --retry 5 -C - -o "$ZIP.part" "$MIRROR"
      mv "$ZIP.part" "$ZIP"
    fi
  fi
  echo "[download] unzipping $ZIP"
  unzip -q -o "$ZIP" -d "$RAW"
  [ "${KEEP_ZIP:-0}" = 1 ] || rm -f "$ZIP"
fi
n=$(count_dcm)
[ "$n" = "$N_TRAIN" ] || { echo "[download] expected $N_TRAIN train DICOMs, found $n" >&2; exit 1; }
for f in stage_2_train_labels.csv stage_2_detailed_class_info.csv; do
  [ -f "$RAW/$f" ] || { echo "[download] missing $RAW/$f" >&2; exit 1; }
done
echo "[download] OK: $n train DICOMs, $(find "$RAW/stage_2_test_images" -name '*.dcm' | wc -l | tr -d ' ') test DICOMs (unlabelled, unused)"

# ---- 2. RSNA -> NIH ChestX-ray14 mapping (RSNA 2018 challenge datasets page) ------------------------
if [ ! -f "$NIH_JSON" ] || [ "$(sha256 "$NIH_JSON")" != "$NIH_SHA256" ]; then
  # HTTPS to this S3 bucket fails with an SSL error from some networks; plain HTTP is verified by SHA-256 below
  curl -fsSL --retry 3 -o "$NIH_JSON" "https://$NIH_URL" || curl -fsSL --retry 3 -o "$NIH_JSON" "http://$NIH_URL"
fi
[ "$(sha256 "$NIH_JSON")" = "$NIH_SHA256" ] || { echo "[download] NIH mapping SHA-256 mismatch" >&2; exit 1; }
# patientId,nih_image,nih_patient for every train image, in first-appearance order of stage_2_train_labels.csv
"$PY" - "$NIH_JSON" "$RAW/stage_2_train_labels.csv" "$EXT/nih_mapping.csv" <<'EOF'
import json, sys
import pandas as pd
src, labels, out = sys.argv[1:]
m = pd.DataFrame(json.load(open(src)))[["subset_img_id", "img_id"]]
m.columns = ["patientId", "nih_image"]
m["nih_patient"] = m["nih_image"].str.split("_").str[0]
ids = pd.read_csv(labels, usecols=["patientId"])["patientId"].drop_duplicates()
df = pd.DataFrame({"patientId": ids}).merge(m, on="patientId", how="left", validate="one_to_one")
assert df["nih_patient"].notna().all(), "train images missing in the NIH mapping"
df.to_csv(out, index=False)
print(f"[download] {out}: {len(df)} images, {df['nih_patient'].nunique()} NIH patients")
EOF
