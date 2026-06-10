#!/usr/bin/env bash
# ONE-COMMAND cloud pretraining of the deep ECG backbone on CODE-15%.
#
# Run this on a fresh cloud GPU box (Colab / Lambda / RunPod / Vast / EC2).
# It installs minimal deps, downloads CODE-15 (~50 GB to the cloud disk),
# pretrains ECGResNetDeep1D, and produces a small backbone.pt (~27 MB) that you
# bring back to the laptop for the local fine-tune (which needs the local
# PTB-XL + CinC2020 blend). CUDA is auto-detected.
#
#   git clone https://github.com/Davmunrey/Heartcheck && cd Heartcheck
#   bash scripts/cloud_pretrain_code15.sh
#
# Tunables (env):
#   EPOCHS (10)  BATCH (128)  LR (1e-3)  WORKERS (8)
#   CODE15_ROOT (./data/code_15pct)  OUT (runs/cloud/code15_pretrain)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
CODE15_ROOT="${CODE15_ROOT:-$ROOT/data/code_15pct}"
OUT="${OUT:-$ROOT/runs/cloud/code15_pretrain}"
EPOCHS="${EPOCHS:-10}"; BATCH="${BATCH:-128}"; LR="${LR:-1e-3}"; WORKERS="${WORKERS:-8}"
PY="${PY:-python3}"

echo "[0/3] env"
"$PY" -c "import sys; print('python', sys.version.split()[0])"
# Fast multi-connection downloader (turns ~15h of Zenodo throttling into <1h).
command -v aria2c >/dev/null 2>&1 || (command -v apt-get >/dev/null 2>&1 && sudo apt-get -qq update && sudo apt-get -qq install -y aria2) || true
# Minimal deps for pretraining only (NOT the full ml-api). torch is preinstalled
# on GPU images. --no-deps on ml/ avoids dragging pandas/wfdb/etc. (and the
# pandas-version conflict with the host image); pretrain only needs numpy+h5py.
"$PY" -c "import torch" 2>/dev/null || "$PY" -m pip install -q torch
"$PY" -m pip install -q numpy h5py
"$PY" -m pip install -q --no-deps -e ml/   # installs heartscan_ml package only
"$PY" -c "import torch; print('CUDA:', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only')"

echo "[1/3] download CODE-15 -> $CODE15_ROOT (~50 GB, resumable)"
DEST="$CODE15_ROOT" bash scripts/download_code15.sh

echo "[2/3] pretrain deep backbone ($EPOCHS epochs, batch $BATCH)"
"$PY" -m ml.training.pretrain_code15 \
  --data-root "$CODE15_ROOT" --out "$OUT" \
  --epochs "$EPOCHS" --batch-size "$BATCH" --lr "$LR" --workers "$WORKERS"

echo "[3/3] done"
echo "  Backbone: $OUT/backbone.pt"
ls -lh "$OUT/backbone.pt" 2>/dev/null || true
echo
echo "  >>> Bring this ONE file back to the laptop, then fine-tune locally:"
echo "      scp <cloud>:$OUT/backbone.pt runs/local/code15_pretrain/backbone.pt"
echo "      FT_OUT=runs/local/deep_code15_ft \\"
echo "        PRETRAIN_OUT=runs/local/code15_pretrain \\"
echo "        scripts/pretrain_finetune_code15.sh   # skips re-pretraining if backbone.pt exists"
