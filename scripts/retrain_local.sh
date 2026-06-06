#!/usr/bin/env bash
# Local focal-loss fine-tune of the 12-lead diagnostic model, using datasets
# already downloaded to a NON-iCloud path (default ~/heartscan_data).
#
# Why this exists: the repo's iCloud copy evicts data files (dataless), so we
# re-download to a local root and train there. This wraps the project's own
# pipeline (manifest -> splits -> train -> calibrate -> evaluate) and targets
# the known weak class (HYP) with focal loss, fine-tuning from the current
# champion. It does NOT auto-promote: review metrics, then point the API at the
# new checkpoint via HEARTSCAN_DIAGNOSTIC_MODEL_PATH.
#
# Usage:
#   scripts/retrain_local.sh                       # PTB-XL only (sufficient, all 5 superclasses)
#   DATASETS="ptb_xl georgia12" scripts/retrain_local.sh
#   EPOCHS=12 LOSS=focal scripts/retrain_local.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/apps/ml-api/.venv/bin/python"
DATA_ROOT="${DATA_ROOT:-$HOME/heartscan_data}"
DATASETS="${DATASETS:-ptb_xl}"
EPOCHS="${EPOCHS:-10}"
LOSS="${LOSS:-focal}"
OUT="${OUT:-$ROOT/runs/local/focal_from_champion}"
CHAMPION="${CHAMPION:-$ROOT/runs/auto/ptbxl_georgia_full/finetune_12e_from_8857/checkpoint.pt}"
MANIFEST_DIR="$ROOT/runs/local"

[[ -x "$PY" ]] || { echo "[abort] venv missing at $PY (run scripts/install_backend.sh in the clone)"; exit 2; }

# Guard against zero-stub training on a half-downloaded dataset.
expected=21799
have="$(/usr/bin/find "$DATA_ROOT/ptb_xl/records100" -name '*.dat' 2>/dev/null | wc -l | tr -d ' ')"
echo "[check] PTB-XL records present: $have / $expected"
if [[ "$have" -lt $((expected * 95 / 100)) ]]; then
  echo "[warn] < 95% of PTB-XL downloaded. Missing records become zero stubs and"
  echo "       degrade training. Set ALLOW_PARTIAL=1 to proceed anyway."
  [[ "${ALLOW_PARTIAL:-0}" == "1" ]] || exit 3
fi

mkdir -p "$MANIFEST_DIR"
echo "[1/5] manifest ($DATASETS) from $DATA_ROOT"
"$PY" -m ml.datasets.cli manifest --root "$DATA_ROOT" --datasets $DATASETS \
  --out "$MANIFEST_DIR/manifest.parquet"

echo "[2/5] patient-stratified split"
"$PY" -m ml.datasets.splits --manifest "$MANIFEST_DIR/manifest.parquet" \
  --out "$MANIFEST_DIR/manifest_split.parquet"

echo "[3/5] $LOSS fine-tune from champion ($EPOCHS epochs)"
"$PY" -m ml.training.train_multilabel \
  --manifest "$MANIFEST_DIR/manifest_split.parquet" \
  --out "$OUT" \
  --init-checkpoint "$CHAMPION" \
  --loss "$LOSS" --threshold-metric f1 --monitor tuned_macro_f1 \
  --epochs "$EPOCHS" --batch-size 128 --lr 3e-5 --workers 0

echo "[4/5] calibrate"
"$PY" -m ml.training.calibrate \
  --logits "$OUT/val_logits.npz" \
  --checkpoint "$OUT/checkpoint.pt" \
  --report "$OUT/calibration.json" || echo "[warn] calibrate step skipped/failed (non-fatal)"

echo "[5/5] evaluate on held-out test"
"$PY" -m ml.training.evaluate_multilabel \
  --manifest "$MANIFEST_DIR/manifest_split.parquet" \
  --checkpoint "$OUT/checkpoint.pt" --split test --workers 0 \
  --out "$OUT/eval_test.json"

echo
echo "[done] new checkpoint: $OUT/checkpoint.pt"
echo "       review $OUT/eval_test.json (esp. MI/HYP recall) before promoting."
echo "       to serve it:  export HEARTSCAN_DIAGNOSTIC_MODEL_PATH=$OUT/checkpoint.pt"
