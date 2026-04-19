#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/apps/ml-api"
export HEARTSCAN_API_KEY="${HEARTSCAN_API_KEY:-dev-key-change-me}"

echo "API + web (venv: $ROOT/apps/ml-api/.venv si existe)"
echo "  Landing: http://127.0.0.1:8000/"
echo "  App:     http://127.0.0.1:8000/app  (sube foto o «Imagen de ejemplo»)"
echo "  OpenAPI: http://127.0.0.1:8000/docs"
if [[ -x "$ROOT/apps/ml-api/.venv/bin/uvicorn" ]]; then
  exec "$ROOT/apps/ml-api/.venv/bin/uvicorn" app.main:app --reload --host 0.0.0.0 --port 8000
else
  exec python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
fi
