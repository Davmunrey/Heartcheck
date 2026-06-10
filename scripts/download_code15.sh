#!/usr/bin/env bash
# Download CODE-15% (Ribeiro et al.) — the large-corpus ECG dataset for
# pretraining the deep backbone (ECGResNetDeep1D) before fine-tuning on the
# 12-lead diagnostic blend. 345,779 exams / 233,770 patients, 12-lead @ 400 Hz,
# stored (N, 4096, 12). CC-BY-4.0. ~50.6 GB across 18 zip parts + exams.csv.
#
# Zenodo record: https://zenodo.org/records/4916206  (DOI 10.5281/zenodo.4916206)
#
# Speed: Zenodo throttles a single connection to ~0.6-1 MB/s (~15 h for 50 GB).
# This script uses aria2c with 16 connections per file when available (often
# 10-50x faster); falls back to wget -c. Both are resumable.
#
# Usage:
#   scripts/download_code15.sh                      # all 18 parts -> ~/heartscan_data/code_15pct
#   DEST=/path scripts/download_code15.sh
#   CODE15_PARTS=6 scripts/download_code15.sh       # only first 6 parts (~115k ECGs, fits small disks)
#
# Env: DEST, CODE15_PARTS (default 18), ARIA_CONN (default 16)
set -euo pipefail

DEST="${DEST:-$HOME/heartscan_data/code_15pct}"
BASE="https://zenodo.org/records/4916206/files"
PARTS="${CODE15_PARTS:-18}"
CONN="${ARIA_CONN:-16}"
mkdir -p "$DEST"
cd "$DEST"

# Pick the fastest available downloader. aria2c -x/-s open multiple connections
# per file, which bypasses Zenodo's per-connection throttle.
fetch() {  # $1=url  $2=outfile
  if command -v aria2c >/dev/null 2>&1; then
    aria2c -c -x "$CONN" -s "$CONN" -k 1M --file-allocation=none \
      --console-log-level=warn --summary-interval=10 -o "$2" "$1"
  else
    wget -c "$1" -O "$2"
  fi
}

if ! command -v aria2c >/dev/null 2>&1; then
  echo "[code15] NOTE: aria2c not found -> using slow single-connection wget."
  echo "         Install it for 10-50x faster downloads:  apt-get install -y aria2  (or brew install aria2)"
fi

echo "[code15] downloading exams.csv + $PARTS part(s) into $DEST (resumable)"
fetch "$BASE/exams.csv?download=1" exams.csv

last=$((PARTS - 1))
for i in $(seq 0 "$last"); do
  f="exams_part${i}.zip"
  hdf5="exams_part${i}.hdf5"
  if [[ -f "$hdf5" ]]; then echo "[code15] $hdf5 already extracted — skip"; continue; fi
  echo "[code15] $f"
  fetch "$BASE/${f}?download=1" "$f"
  # Each zip holds exams_part${i}.hdf5; unzip then drop the zip to save space.
  if command -v unzip >/dev/null 2>&1; then
    unzip -o "$f" && rm -f "$f"
  fi
done

echo "[code15] done. HDF5 parts + exams.csv in $DEST"
echo "[code15] pretrain trains on whatever parts are present — see ml/datasets/code_15pct.py."
