#!/usr/bin/env bash
# Instala dependencias Python del API en apps/ml-api/.venv y genera imagen de ejemplo.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/apps/ml-api"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/generate_sample_ecg_image.py
echo ""
echo "Listo. Arranca el servidor con:  $ROOT/scripts/run_local.sh"
