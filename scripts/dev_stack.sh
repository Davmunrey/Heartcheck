#!/usr/bin/env bash
# Arranque local: ML API (FastAPI) + Next.js (Clerk). Requiere:
#   - ./scripts/install_backend.sh (una vez)
#   - apps/web/.env.local con NEXT_PUBLIC_CLERK_* y ML_API_URL=http://127.0.0.1:8000
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

UVI=""
if [[ -x "$ROOT/apps/ml-api/.venv/bin/uvicorn" ]]; then
  UVI="$ROOT/apps/ml-api/.venv/bin/uvicorn"
elif command -v uvicorn >/dev/null 2>&1; then
  UVI="uvicorn"
else
  echo "No hay uvicorn. Ejecuta: ./scripts/install_backend.sh"
  exit 1
fi

export HEARTSCAN_API_KEY="${HEARTSCAN_API_KEY:-dev-key-change-me}"
export HEARTSCAN_ALLOW_LEGACY_API_KEY="${HEARTSCAN_ALLOW_LEGACY_API_KEY:-true}"

cleanup() {
  if [[ -n "${API_PID:-}" ]] && kill -0 "$API_PID" 2>/dev/null; then
    kill "$API_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

(
  cd "$ROOT/apps/ml-api"
  exec $UVI app.main:app --reload --host 0.0.0.0 --port 8000
) &
API_PID=$!

echo "API → http://127.0.0.1:8000  (pid $API_PID)"
echo "Web → Next.js (puerto 3000 por defecto)"
sleep 1

cd "$ROOT"
npm run dev
cleanup
