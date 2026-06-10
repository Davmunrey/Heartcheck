#!/usr/bin/env bash
# CODE-15 pretrain -> blend fine-tune for the deep ECG backbone.
#
# The real lever past the served champion's 0.608 macro-F1: pretrain the 6.8M
# ECGResNetDeep1D on CODE-15% (345k records) so it isn't data-starved, then
# transfer the backbone and fine-tune the 5-superclass head on the PTB-XL +
# CinC2020 blend. See docs/MODEL_CARD.md.
#
# Prereqs:
#   - CODE-15 downloaded:  scripts/download_code15.sh   (~50 GB)
#   - blend manifest built: runs/local/deep500/manifest_split.parquet (500Hz)
#     (or rebuild: PTBXL_USE_HR=1 ml.datasets.cli manifest --datasets ptb_xl cinc2020)
#
# Usage:
#   scripts/pretrain_finetune_code15.sh
#   PRETRAIN_EPOCHS=8 FT_EPOCHS=20 scripts/pretrain_finetune_code15.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/apps/ml-api/.venv/bin/python"
CODE15_ROOT="${CODE15_ROOT:-$HOME/heartscan_data/code_15pct}"
PRETRAIN_OUT="${PRETRAIN_OUT:-$ROOT/runs/local/code15_pretrain}"
FT_OUT="${FT_OUT:-$ROOT/runs/local/deep_code15_ft}"
BLEND_SPLIT="${BLEND_SPLIT:-$ROOT/runs/local/deep500/manifest_split.parquet}"
PRETRAIN_EPOCHS="${PRETRAIN_EPOCHS:-8}"
FT_EPOCHS="${FT_EPOCHS:-20}"

[[ -f "$BLEND_SPLIT" ]] || { echo "[abort] blend split missing at $BLEND_SPLIT — build the 500Hz manifest first"; exit 2; }

# If a pretrained backbone is already present (e.g. brought back from the cloud
# run), skip the expensive pretraining step and go straight to fine-tune.
if [[ -f "$PRETRAIN_OUT/backbone.pt" ]]; then
  echo "[1/2] backbone already present at $PRETRAIN_OUT/backbone.pt — skipping pretrain"
else
  [[ -f "$CODE15_ROOT/exams.csv" ]] || { echo "[abort] no backbone.pt and CODE-15 not found at $CODE15_ROOT — run scripts/download_code15.sh or bring back the cloud backbone"; exit 2; }
  echo "[1/2] pretrain deep backbone on CODE-15 ($PRETRAIN_EPOCHS epochs)"
  PYTORCH_ENABLE_MPS_FALLBACK=1 "$PY" -m ml.training.pretrain_code15 \
    --data-root "$CODE15_ROOT" --out "$PRETRAIN_OUT" \
    --epochs "$PRETRAIN_EPOCHS" --batch-size 64 --lr 1e-3 --workers 6
fi

echo "[2/2] fine-tune 5-superclass head on the blend from the pretrained backbone"
PYTORCH_ENABLE_MPS_FALLBACK=1 "$PY" -m ml.training.train_multilabel \
  --manifest "$BLEND_SPLIT" --out "$FT_OUT" \
  --arch deep --init-backbone "$PRETRAIN_OUT/backbone.pt" \
  --target-fs 500 --target-len 4096 \
  --mask-partial-labels --balanced-sampler \
  --loss focal --monitor tuned_macro_f1 \
  --warmup-epochs 3 --grad-clip 1.0 \
  --epochs "$FT_EPOCHS" --batch-size 32 --lr 3e-4 --workers 6

echo "[done] fine-tuned checkpoint: $FT_OUT/checkpoint.pt"
echo "       evaluate vs champion 0.608:  scripts/eval_cinc2020_blend.sh-style on $FT_OUT"
