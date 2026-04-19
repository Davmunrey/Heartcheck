# Ruta canónica del proyecto

**La raíz de trabajo unificada es:**

```text
/Users/mac/Desktop/Heartcheck
```

Abre esta carpeta en el IDE. Aquí está el monorepo **HeartScan** (`apps/ml-api/`, `apps/mobile/`, `web_public/`) y, tras migrar, el stack **HeartDiagnosis** completo en `references/HeartDiagnosis/` (código editable, no una copia “de archivo”).

## Migrar HeartDiagnosis y borrar el origen

Si aún tienes `Proposal-Engine/src/HeartDiagnosis`, ejecuta **en tu Mac**:

```bash
bash /Users/mac/Desktop/Heartcheck/scripts/unify_and_delete_heartdiagnosis.sh
```

Eso copia **todo el fuente** (excluyendo solo artefactos pesados: `node_modules`, `.venv`, `dist`, etc.) a `references/HeartDiagnosis/` y elimina la carpeta antigua. Luego reinstala dependencias en el destino (ver [`references/README.md`](../references/README.md)).

Solo copiar sin borrar el origen: `scripts/sync_references_from_proposal_engine.sh`.

## Comprobar HeartScan

```bash
test -f /Users/mac/Desktop/Heartcheck/apps/mobile/pubspec.yaml \
  && test -f /Users/mac/Desktop/Heartcheck/apps/ml-api/app/main.py \
  && echo "OK: HeartScan"
```
