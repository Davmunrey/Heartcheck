#!/usr/bin/env bash
# CODE-15 pretrain -> blend fine-tune for the deep ECG backbone.
#
# The real lever past the served champion's 0.608 macro-F1: pretrain the 6.8M
# ECGResNetDeep1D on CODE-15% (345k records) so it isn't data-starved, then
# transfer the backbone and fine-tune the 5-superclass head on the PTB-XL +
# CinC2020 blend. See docs/MODEL_CARD.md.
#
# Prereqs:
#   - CODE-15 for pretrain: scripts/download_code15.sh (~50 GB), OR bring back a
#     cloud backbone.pt into $PRETRAIN_OUT (then pretrain is skipped).
#   - Blend data (ptb_xl + cinc2020, ~6 GB) under $DATA_ROOT. If the 500Hz blend
#     split is missing it is built automatically (download -> manifest -> split);
#     pass DOWNLOAD=1 to fetch the datasets when they aren't on disk yet.
#
# Usage:
#   scripts/pretrain_finetune_code15.sh                       # data already local
#   DOWNLOAD=1 scripts/pretrain_finetune_code15.sh            # fresh GPU box
#   PRETRAIN_EPOCHS=8 FT_EPOCHS=20 scripts/pretrain_finetune_code15.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/apps/ml-api/.venv/bin/python"
CODE15_ROOT="${CODE15_ROOT:-$HOME/heartscan_data/code_15pct}"
PRETRAIN_OUT="${PRETRAIN_OUT:-$ROOT/runs/local/code15_pretrain}"
FT_OUT="${FT_OUT:-$ROOT/runs/local/deep_code15_ft}"
BLEND_SPLIT="${BLEND_SPLIT:-$ROOT/runs/local/deep500/manifest_split.parquet}"
DATA_ROOT="${DATA_ROOT:-$HOME/heartscan_data}"            # holds one subfolder per dataset
BLEND_DATASETS="${BLEND_DATASETS:-ptb_xl cinc2020}"       # 5-superclass fine-tune blend
DOWNLOAD="${DOWNLOAD:-0}"                                 # 1 = fetch blend data if absent
PRETRAIN_EPOCHS="${PRETRAIN_EPOCHS:-8}"
FT_EPOCHS="${FT_EPOCHS:-20}"

# Build the 500Hz blend split if it is missing — a fresh GPU box has nothing.
# Mirrors scripts/train_photo.sh: (optional) download -> manifest -> split.
if [[ ! -f "$BLEND_SPLIT" ]]; then
  echo "[0/2] blend split missing -> building 500Hz manifest from [$BLEND_DATASETS]"
  BLEND_DIR="$(dirname "$BLEND_SPLIT")"
  mkdir -p "$BLEND_DIR" "$DATA_ROOT"
  for d in $BLEND_DATASETS; do
    if [[ ! -d "$DATA_ROOT/$d" ]]; then
      if [[ "$DOWNLOAD" == "1" ]]; then
        echo "[0/2] downloading $d -> $DATA_ROOT/$d"
        "$PY" -m ml.datasets.cli download "$d" --target "$DATA_ROOT/$d" --confirm
      else
        echo "[abort] dataset '$d' not at $DATA_ROOT/$d — re-run with DOWNLOAD=1 to fetch it, or set DATA_ROOT to where it lives." >&2
        exit 2
      fi
    fi
  done
  # PTBXL_USE_HR=1 routes the ptb_xl loader to the 500Hz records (records500),
  # matching the --target-fs 500 fine-tune below. CinC2020 is already 500Hz.
  PTBXL_USE_HR=1 "$PY" -m ml.datasets.cli manifest \
    --root "$DATA_ROOT" --datasets $BLEND_DATASETS \
    --out "$BLEND_DIR/manifest.parquet"
  "$PY" -m ml.datasets.splits \
    --manifest "$BLEND_DIR/manifest.parquet" --out "$BLEND_SPLIT"
fi

# If a pretrained backbone is already present (e.g. brought back from the cloud
# run), skip the expensive pretraining step and go straight to fine-tune.
if [[ -f "$PRETRAIN_OUT/backbone.pt" ]]; then
  echo "[1/2] backbone already present at $PRETRAIN_OUT/backbone.pt — skipping pretrain"
else
  if [[ ! -f "$CODE15_ROOT/exams.csv" ]]; then
    if [[ "$DOWNLOAD" == "1" ]]; then
      echo "[1/2] CODE-15 missing -> downloading to $CODE15_ROOT (~50 GB, resumable)"
      DEST="$CODE15_ROOT" bash "$ROOT/scripts/download_code15.sh"
    else
      echo "[abort] no backbone.pt and CODE-15 not at $CODE15_ROOT — re-run with DOWNLOAD=1, run scripts/download_code15.sh, or bring back the cloud backbone" >&2
      exit 2
    fi
  fi
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
