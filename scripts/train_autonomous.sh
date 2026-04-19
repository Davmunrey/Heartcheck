#!/usr/bin/env bash
# One-shot autonomous training pipeline for HeartScan.
#
# Defaults to the tier-1 commercial-safe blend (PTB-XL + Chapman + CinC2017
# + BUT QDB) and skips fine-tune unless image datasets exist on disk. Use
# environment variables to opt into more aggressive runs:
#
#   EPOCHS=20 ./scripts/train_autonomous.sh
#   IMAGE_DATASETS="ecg_image_database" ./scripts/train_autonomous.sh
#   PROMOTE=1 BASELINE=eval/baselines/synth_v1.json ./scripts/train_autonomous.sh
#
# The orchestrator is idempotent: re-running with the same RUN_ID resumes
# at the first incomplete step.
set -euo pipefail

PY="${PY:-apps/ml-api/.venv/bin/python}"
RUN_ID="${RUN_ID:-auto_$(date -u +%Y%m%dT%H%M%SZ)}"
RUNS_DIR="${RUNS_DIR:-runs}"
RAW_DIR="${RAW_DIR:-data/raw}"
DATASETS="${DATASETS:-ptb_xl chapman_shaoxing cinc2017 but_qdb}"
IMAGE_DATASETS="${IMAGE_DATASETS:-}"
EPOCHS="${EPOCHS:-5}"
BATCH_SIZE="${BATCH_SIZE:-64}"
WORKERS="${WORKERS:-2}"
PROMOTE="${PROMOTE:-0}"
BASELINE="${BASELINE:-}"
MODEL_VERSION="${MODEL_VERSION:-}"
SKIP_DOWNLOAD="${SKIP_DOWNLOAD:-0}"

if [[ ! -x "$PY" ]]; then
  echo "[abort] Python venv not found at $PY. Run scripts/install_backend.sh first." >&2
  exit 2
fi

args=(
  -m ml.training.run_full_pipeline
  --run-id "$RUN_ID"
  --runs-dir "$RUNS_DIR"
  --raw-dir "$RAW_DIR"
  --datasets $DATASETS
  --epochs "$EPOCHS"
  --batch-size "$BATCH_SIZE"
  --workers "$WORKERS"
)
if [[ -n "$IMAGE_DATASETS" ]]; then
  args+=(--image-datasets $IMAGE_DATASETS)
fi
if [[ "$SKIP_DOWNLOAD" == "1" ]]; then
  args+=(--skip-download)
fi
if [[ "$PROMOTE" == "1" ]]; then
  args+=(--promote)
fi
if [[ -n "$BASELINE" ]]; then
  args+=(--baseline "$BASELINE")
fi
if [[ -n "$MODEL_VERSION" ]]; then
  args+=(--model-version "$MODEL_VERSION")
fi

echo "[autonomous] run_id=$RUN_ID datasets=[$DATASETS] image=[$IMAGE_DATASETS] epochs=$EPOCHS"
exec "$PY" "${args[@]}"
