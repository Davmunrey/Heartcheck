#!/usr/bin/env bash
# Tier 2: CODE-15% (Brazilian, ~50 GB) + MIMIC-IV-ECG (~95 GB).
#
# CODE-15% is CC BY 4.0 but ships on Zenodo as multiple HDF5 chunks; the
# loader prints download instructions instead of fetching automatically
# because the Zenodo file list changes occasionally.
#
# MIMIC-IV-ECG is ODbL + clinical content rights and requires PhysioNet
# credentialed access (CITI training).
#
# Run only after legal sign-off. Disable any datasets not approved by editing
# the DATASETS env var.
set -euo pipefail

ROOT="${ROOT:-data/raw}"
PY="${PY:-apps/ml-api/.venv/bin/python}"
DATASETS="${DATASETS:-code_15pct mimic_iv_ecg}"

if [[ ! -x "$PY" ]]; then
  echo "[abort] Python venv not found at $PY." >&2
  exit 2
fi

cat <<'BANNER'
============================================================
TIER 2 download — large + license-sensitive datasets.
- CODE-15%   : ~50 GB, CC BY 4.0 (commercial OK with attribution)
- MIMIC-IV-ECG: ~95 GB, ODbL + clinical content rights
                requires PhysioNet credentialed access (CITI)
                consult legal before training a commercial model.
============================================================
BANNER

read -r -p "Type CONFIRM to proceed: " ack
if [[ "$ack" != "CONFIRM" ]]; then
  echo "[abort] confirmation not provided." >&2
  exit 2
fi

for ds in $DATASETS; do
  target="$ROOT/$ds"
  echo "============================================================"
  echo "[$ds] -> $target"
  echo "============================================================"
  "$PY" -m ml.datasets.cli download "$ds" --target "$target"
done

echo
echo "[done] tier 2 instructions/downloads finished."
echo "[next] document license clearance in docs/DATASHEET_TRAINING.md before training."
