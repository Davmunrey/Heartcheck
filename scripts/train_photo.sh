#!/usr/bin/env bash
#
# Photo model training pipeline — replace the heuristic photo path with a
# trained 3-class screen (normal / arrhythmia / noise) via Axis's OWN extractor.
# See docs/PHOTO_MODEL_PLAN.md.
#
# Idempotent. Configurable via env vars (with defaults). Needs the ml-api venv
# (torch) + the image dataset(s). GPU optional (uses whatever torch device).
#
#   DOWNLOAD=1 ./scripts/train_photo.sh          # download datasets first
#   EPOCHS=8 PRETRAINED=runs/local/full27/checkpoint.pt ./scripts/train_photo.sh
#
set -euo pipefail
cd "$(dirname "$0")/.."   # repo root

PY="${PY:-apps/ml-api/.venv/bin/python}"
# Strip-level, PTB-XL-coded image datasets mapped to 3 classes by map_ptbxl_codes.
# NOT the local beat-level ECG_Image_data (6 AAMI classes, wrong granularity).
DATASETS="${PHOTO_DATASETS:-ecg_image_database}"   # e.g. "ecg_image_database ptb_xl_image_17k"
DATA_ROOT="${DATA_ROOT:-data/raw}"
MANIFEST_DIR="${MANIFEST_DIR:-data/manifests}"
OUT="${OUT_DIR:-runs/local/photo_ft}"
PRETRAINED="${PRETRAINED:-}"   # optional warm-start checkpoint (backbone)
EPOCHS="${EPOCHS:-5}"
DOWNLOAD="${DOWNLOAD:-0}"

echo "[photo] py=$PY datasets='$DATASETS' epochs=$EPOCHS out=$OUT"
mkdir -p "$MANIFEST_DIR" "$DATA_ROOT"

# 1. (optional) download datasets (PhysioNet / zip). Skip if already present.
if [ "$DOWNLOAD" = "1" ]; then
  for d in $DATASETS; do
    echo "[photo] downloading $d -> $DATA_ROOT/$d"
    "$PY" -m ml.datasets.cli download "$d" --target "$DATA_ROOT/$d" --confirm
  done
fi

# 2. Unified manifest. label_id ∈ {0:normal,1:arrhythmia,2:noise} via
#    ml.datasets.labels.map_ptbxl_codes (documented, auditable).
echo "[photo] building manifest"
"$PY" -m ml.datasets.cli manifest --root "$DATA_ROOT" --datasets $DATASETS \
  --out "$MANIFEST_DIR/photo.parquet"

# 3. Patient-disjoint split — NON-NEGOTIABLE. Splitting by image (not patient)
#    is what inflated the prior beat-image F1 (0.994). Do not skip.
echo "[photo] patient-disjoint split"
"$PY" -m ml.datasets.splits --manifest "$MANIFEST_DIR/photo.parquet" \
  --out "$MANIFEST_DIR/photo_split.parquet"

# 4. Fine-tune ECGResNet1D on the images ROUTED THROUGH the production extractor
#    (trains on the same noisy 1D signal seen at inference — closes foto↔señal).
echo "[photo] fine-tuning (finetune_image)"
"$PY" -m ml.training.finetune_image \
  --manifest "$MANIFEST_DIR/photo_split.parquet" \
  --out "$OUT" --epochs "$EPOCHS" \
  ${PRETRAINED:+--pretrained "$PRETRAINED"}

# 5. Evaluate on the patient-disjoint TEST split. Report AUROC + per-class
#    (raw F1 across splits is not comparable — see MODEL_CARD).
echo "[photo] evaluating on patient-disjoint test"
"$PY" -m ml.training.evaluate_checkpoint \
  --manifest "$MANIFEST_DIR/photo_split.parquet" \
  --checkpoint "$OUT/checkpoint.pt" --split test --out "$OUT/eval_test.json"

cat <<EOF

[photo] done. Review $OUT/eval_test.json (AUROC, per-class, calibration).

Promote ONLY if it beats the heuristic on this patient-disjoint test:
  1. local:  add HEARTSCAN_MODEL_PATH=$OUT/checkpoint.pt to apps/ml-api/.env
  2. prod:   set the same as a Render secret
  3. /api/v1/meta then reports checkpoint_loaded:true + the real model_version.
Keep the photo path SECONDARY to the 12-lead signal model, behind the
quality-gate + conformal abstention. If it can't clear a safety bar, keep the
heuristic and the "cribado" label.
EOF
