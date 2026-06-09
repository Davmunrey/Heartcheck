#!/usr/bin/env bash
# Download CODE-15% (Ribeiro et al.) — the large-corpus ECG dataset for
# pretraining the deep backbone (ECGResNetDeep1D) before fine-tuning on the
# 12-lead diagnostic blend. 345,779 exams / 233,770 patients, 12-lead @ 400 Hz,
# stored (N, 4096, 12). CC-BY-4.0. ~50.6 GB across 18 zip parts + exams.csv.
#
# Zenodo record: https://zenodo.org/records/4916206  (DOI 10.5281/zenodo.4916206)
#
# Usage:
#   scripts/download_code15.sh                 # -> ~/heartscan_data/code_15pct
#   DEST=/path scripts/download_code15.sh
#
# Resumable (wget -c). Unzips each part after download. Safe to re-run.
set -euo pipefail

DEST="${DEST:-$HOME/heartscan_data/code_15pct}"
BASE="https://zenodo.org/records/4916206/files"
mkdir -p "$DEST"
cd "$DEST"

echo "[code15] downloading exams.csv + 18 parts into $DEST (~50 GB, resumable)"
wget -c "$BASE/exams.csv?download=1" -O exams.csv

for i in $(seq 0 17); do
  f="exams_part${i}.zip"
  echo "[code15] $f"
  wget -c "$BASE/${f}?download=1" -O "$f"
  # Each zip holds exams_part${i}.hdf5; unzip then drop the zip to save space.
  if command -v unzip >/dev/null 2>&1; then
    unzip -o "$f" && rm -f "$f"
  fi
done

echo "[code15] done. HDF5 parts + exams.csv in $DEST"
echo "[code15] register/manifest: see ml/datasets/code_15pct.py (dataset 'code_15pct')"
