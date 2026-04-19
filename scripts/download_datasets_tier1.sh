#!/usr/bin/env bash
# Download HeartScan training tier 1: PTB-XL, Chapman-Shaoxing, CinC 2017, BUT QDB.
# All four are CC BY 4.0 (open) — no PhysioNet credentials required.
#
# Defaults:
#   - target: ./data/raw/<name>/
#   - parallelism: serial (PhysioNet rate-limits aggressive mirroring)
#
# Usage:
#   scripts/download_datasets_tier1.sh                # default to ./data/raw
#   ROOT=/mnt/big-disk scripts/download_datasets_tier1.sh
#   DATASETS="ptb_xl cinc2017" scripts/download_datasets_tier1.sh
set -euo pipefail

ROOT="${ROOT:-data/raw}"
PY="${PY:-apps/ml-api/.venv/bin/python}"
DATASETS="${DATASETS:-ptb_xl chapman_shaoxing cinc2017 but_qdb}"

if [[ ! -x "$PY" ]]; then
  echo "[abort] Python venv not found at $PY. Run scripts/install_backend.sh first." >&2
  exit 2
fi
if ! command -v wget >/dev/null 2>&1; then
  echo "[abort] wget required for PhysioNet mirroring." >&2
  exit 2
fi

echo "[plan] downloading datasets: $DATASETS"
echo "[plan] target root: $ROOT"
echo "[plan] estimated total size: ~6 GB"
echo "[plan] press Ctrl-C within 5s to abort"
sleep 5

mkdir -p "$ROOT"
for ds in $DATASETS; do
  target="$ROOT/$ds"
  echo "============================================================"
  echo "[$ds] -> $target"
  echo "============================================================"
  "$PY" -m ml.datasets.cli download "$ds" --target "$target"
done

echo
echo "[done] tier 1 download finished."
echo "[next] build a unified manifest:"
echo "  $PY -m ml.datasets.cli manifest --root $ROOT --datasets $DATASETS --out data/manifests/tier1.parquet"
