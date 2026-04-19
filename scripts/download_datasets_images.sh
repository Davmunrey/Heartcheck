#!/usr/bin/env bash
# Download HeartScan image-domain datasets:
#   - ECG-Image-Database (PhysioNet 2024 challenge, ~60 GB)
#   - PTB-XL-Image-17K   (synthetic with grid + masks, ~20 GB)
#
# These are the datasets that close the foto-vs-señal gap. They are large; run
# on a workstation with at least 100 GB free disk and a stable connection.
#
# Both are CC BY 4.0 (commercial-safe).
set -euo pipefail

ROOT="${ROOT:-data/raw}"
PY="${PY:-apps/ml-api/.venv/bin/python}"
DATASETS="${DATASETS:-ecg_image_database ptb_xl_image_17k}"

if [[ ! -x "$PY" ]]; then
  echo "[abort] Python venv not found at $PY. Run scripts/install_backend.sh first." >&2
  exit 2
fi

echo "[plan] downloading: $DATASETS"
echo "[plan] target root: $ROOT"
echo "[plan] estimated total size: ~80 GB"
echo "[plan] press Ctrl-C within 5s to abort"
sleep 5

for ds in $DATASETS; do
  target="$ROOT/$ds"
  echo "============================================================"
  echo "[$ds] -> $target"
  echo "============================================================"
  "$PY" -m ml.datasets.cli download "$ds" --target "$target"
done

echo
echo "[done] image datasets downloaded."
echo "[next] build a unified manifest (image + signal):"
echo "  $PY -m ml.datasets.cli manifest --root $ROOT \\"
echo "      --datasets ptb_xl chapman_shaoxing cinc2017 ecg_image_database ptb_xl_image_17k \\"
echo "      --out data/manifests/all.parquet"
