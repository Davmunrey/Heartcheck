# Stack HeartDiagnosis (React + `ml/`) en este repo

Tras ejecutar [`scripts/unify_and_delete_heartdiagnosis.sh`](../scripts/unify_and_delete_heartdiagnosis.sh), **todo el código fuente** de lo que antes estaba en `Proposal-Engine/src/HeartDiagnosis` vive aquí, en **`HeartDiagnosis/`** (esta carpeta).

Esto **no es un archivo muerto ni solo lectura**: es el árbol de trabajo normal. Edítalo, versiona los cambios en Git desde `/Users/mac/Desktop/Heartcheck`, instala dependencias y ejecuta el stack desde aquí. El objetivo de la migración es **poder borrar por completo** el directorio antiguo en Proposal-Engine.

## Después de copiar (obligatorio la primera vez)

El `rsync` **no** trae `node_modules`, `.venv`, `dist`, etc. (para no duplicar gigas). Regenera entornos en el destino:

```bash
cd /Users/mac/Desktop/Heartcheck/references/HeartDiagnosis/web
npm install
# según el README de ese subproyecto, p. ej.:
# npm run dev

cd /Users/mac/Desktop/Heartcheck/references/HeartDiagnosis/ml
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[api]"   # o lo que indique el README de ml/
```

Lee el [`HeartDiagnosis/README.md`](HeartDiagnosis/README.md) de esta carpeta para los comandos exactos.

## Relación con HeartScan

- **HeartScan** (FastAPI + Flutter + `web_public`) sigue en la raíz del mismo repo: `apps/ml-api/`, `apps/mobile/`, `web_public/`.
- **HeartDiagnosis** es otro stack (React + Python `ml/`) que convive en `references/HeartDiagnosis/` como proyecto hermano, no como “anexo de solo lectura”.

Solo volver a sincronizar **sin** borrar el origen (p. ej. otra máquina): `scripts/sync_references_from_proposal_engine.sh`.
