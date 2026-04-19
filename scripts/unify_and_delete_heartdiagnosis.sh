#!/usr/bin/env bash
# Migra el proyecto HeartDiagnosis (React + ml/) a references/HeartDiagnosis/ como árbol de trabajo
# completo (editable). Excluye solo node_modules/.venv/dist para no copiar artefactos; hay que
# reinstalar en destino. Luego borra Proposal-Engine/src/HeartDiagnosis.
set -euo pipefail

SRC="/Users/mac/Proposal-Engine/src/HeartDiagnosis"
DEST="/Users/mac/Desktop/Heartcheck/references/HeartDiagnosis"

if [[ ! -d "$SRC" ]]; then
  echo "No existe la fuente (ya borrada o ruta distinta): $SRC" >&2
  exit 1
fi

mkdir -p "$(dirname "$DEST")"
echo "Sincronizando $SRC → $DEST ..."
rsync -a \
  --exclude 'node_modules' \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '.venv' \
  --exclude 'dist' \
  --exclude 'build' \
  "$SRC/" "$DEST/"

if [[ ! -f "$DEST/README.md" ]]; then
  echo "Fallo: no apareció README.md en destino." >&2
  exit 1
fi

echo "Copia OK. Eliminando fuente: $SRC"
rm -rf "$SRC"

if [[ -e "$SRC" ]]; then
  echo "No se pudo eliminar del todo: $SRC" >&2
  exit 1
fi

echo "Listo. Código de trabajo en: $DEST"
echo ""
echo "Siguiente paso (obligatorio): reinstalar dependencias en el DESTINO (no se copiaron node_modules/.venv):"
echo "  cd \"$DEST/web\" && npm install"
echo "  cd \"$DEST/ml\" && python3 -m venv .venv && . .venv/bin/activate && pip install -e '.[api]'"
echo "  (ajusta según README de web/ y ml/)"
echo ""
echo "Si Proposal-Engine tenía scripts apuntando a HeartDiagnosis, límpialos en ese repo."
