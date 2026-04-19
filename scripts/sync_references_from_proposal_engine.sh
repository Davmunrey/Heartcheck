#!/usr/bin/env bash
# Copia el árbol HeartDiagnosis a references/HeartDiagnosis/ (mismo uso que tras unify: es código
# editable en destino; reinstala npm/pip allí). Sin borrar el origen.
set -euo pipefail
SRC="${1:-/Users/mac/Proposal-Engine/src/HeartDiagnosis}"
DEST="/Users/mac/Desktop/Heartcheck/references/HeartDiagnosis"
if [[ ! -d "$SRC" ]]; then
  echo "No existe: $SRC" >&2
  exit 1
fi
mkdir -p "$(dirname "$DEST")"
rsync -a \
  --exclude 'node_modules' \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '.venv' \
  --exclude 'dist' \
  --exclude 'build' \
  "$SRC/" "$DEST/"
echo "Sincronizado: $DEST"
