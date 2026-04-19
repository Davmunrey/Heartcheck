# Entrenamiento autónomo

> Cómo dejar que HeartScan se reentrene solo cuando aparezcan datos nuevos
> o caduquen los pesos actuales, sin que un humano tenga que orquestar
> cada paso.

## Qué es "autónomo" aquí

Un solo comando que encadena las 9 etapas del plan de datasets:

```mermaid
flowchart LR
  A[descarga] --> B[manifest]
  B --> C[splits]
  C --> D[pretrain]
  D --> E[fine-tune imagen]
  E --> F[calibrate]
  F --> G[eval]
  G --> H[emit YAML]
  H --> I[promote]
```

Implementación: [`ml/training/run_full_pipeline.py`](../ml/training/run_full_pipeline.py).
Wrapper bash: [`scripts/train_autonomous.sh`](../scripts/train_autonomous.sh).

Cada etapa es **idempotente**: si la salida ya existe, se salta. Reintentar
con el mismo `RUN_ID` reanuda donde se rompió (útil con crons que pueden
reintentar al día siguiente sin reempezar desde el download).

## Uso típico

### Primera vez (manual)

```bash
# 1) instala backend (CITI no necesario para tier 1)
./scripts/install_backend.sh

# 2) corre el pipeline completo con tier 1 (CC BY 4.0, ~6 GB)
./scripts/train_autonomous.sh
```

Resultado: `runs/<run_id>/` con el checkpoint, manifest YAML, calibración y
reporte de eval. Sin `PROMOTE=1`, no toca `apps/ml-api/weights/`.

### Promover automáticamente cuando mejora

```bash
PROMOTE=1 BASELINE=eval/baselines/synth_v1.json ./scripts/train_autonomous.sh
```

El orquestador compara el F1 macro nuevo contra `BASELINE` y solo copia el
checkpoint a `apps/ml-api/weights/<model_version>.pt(+.yaml)` si supera la
mejora mínima (`--promote-min-delta`, por defecto 0.02).

Cuando no existe baseline aún, el primer run exitoso lo crea.

### Cron diario

Plantilla en [`scripts/train_autonomous_cron.example`](../scripts/train_autonomous_cron.example):

```cron
30 3 * * * cd /opt/heartscan && RUN_ID="nightly_$(date -u +\%Y\%m\%d)" \
    EPOCHS=10 PROMOTE=1 BASELINE=eval/baselines/synth_v1.json \
    scripts/train_autonomous.sh \
    >> runs/cron/nightly_$(date -u +\%Y\%m\%d).log 2>&1
```

### En CI / GitHub Actions

`PROMOTE=0` (no tocar pesos desde CI). El job sirve como gate de regresión:
si el `make eval` interno falla, el PR se bloquea. Reusa el cache de
PhysioNet entre runs si el runner persiste `data/raw/`.

## Variables de entorno

| Variable | Default | Qué controla |
|---|---|---|
| `RUN_ID` | `auto_<UTC ts>` | Carpeta única bajo `runs/`. Reusar para resumir. |
| `RUNS_DIR` | `runs` | Raíz para artefactos. |
| `RAW_DIR` | `data/raw` | Dónde viven (o se descargan) los datasets. |
| `DATASETS` | `ptb_xl chapman_shaoxing cinc2017 but_qdb` | Lista tier 1. |
| `IMAGE_DATASETS` | `(vacío)` | Añade `ecg_image_database ptb_xl_image_17k` para fine-tune. |
| `EPOCHS` | `5` | Épocas de pretrain. |
| `BATCH_SIZE` | `64` | – |
| `WORKERS` | `2` | DataLoader. |
| `PROMOTE` | `0` | `1` para copiar a `apps/ml-api/weights/`. |
| `BASELINE` | `(vacío)` | JSON eval previo para comparar antes de promover. |
| `MODEL_VERSION` | `(vacío)` | Sobrescribe el `model_version` del manifest YAML. |
| `SKIP_DOWNLOAD` | `0` | `1` si ya tienes los datasets en `RAW_DIR`. |

## Auditoría

Cada run escribe `runs/<run_id>/state.json` con:

```json
{
  "started_at": "2026-04-19T...",
  "config": { ... },
  "steps": {
    "download": {"status": "ok", "ts": "...", "datasets": [...]},
    "manifest": {"status": "ok", "ts": "...", "path": "..."},
    "pretrain": {"status": "ok", "ts": "...", "checkpoint": "..."},
    "calibrate": {"status": "ok", "ts": "...", "report": "..."},
    "eval": {"status": "ok", "f1_macro": 0.81, "ece": 0.04, "p95_ms": 180},
    "emit_manifest": {"status": "ok", "path": "..."},
    "promote": {"status": "ok", "delta": 0.025, ...},
    "__finished_at": {"ts": "...", "elapsed_s": 7234.2}
  }
}
```

Logs detallados (uno por etapa) en `runs/<run_id>/pipeline.log`.

## Lo que el orquestador NO hace por ti

- **Datasets restringidos**: CODE completo, MIMIC-IV-ECG, UK Biobank requieren
  credenciales / aprobación. Ver [`docs/RESTRICTED_DATASETS.md`](RESTRICTED_DATASETS.md).
- **Decisión de licencia**: si activas Icentia11k (NC), el orquestador no
  bloquea; el manifiesto YAML registra `license_class: non_commercial` y
  un revisor humano debe vetarlo antes de producción.
- **Compute**: pretrain en CPU sobre tier 1 lleva horas; en GPU minutos.
- **Hyperparam search**: el pipeline corre los defaults del plan; un
  sweep cuesta N × tiempo. Mejor ejecutarlo aparte y traer el ganador con
  `MODEL_VERSION=...` para que el manifest lo registre.
- **Verificación clínica**: por encima del gate cuantitativo, un revisor
  cardiólogo debe sign-off antes de promover a producción.

## Ejecución mínima reproducible (sin descargar nada real)

Para validar el orquestador sin tocar PhysioNet, basta con un manifest
falso:

```bash
apps/ml-api/.venv/bin/python - <<'PY'
import numpy as np, pyarrow as pa, pyarrow.parquet as pq
from pathlib import Path
root = Path("runs/dryrun"); root.mkdir(parents=True, exist_ok=True)
rows = []
rng = np.random.default_rng(0)
for i in range(60):
    cls = i % 3
    p = root / f"{i:03d}.npy"; np.save(p, rng.standard_normal(1024).astype(np.float32))
    rows.append({
        "patient_id": f"p{i:03d}", "record_id": f"r{i}",
        "label": ["normal","arrhythmia","noise"][cls], "label_id": cls,
        "source_dataset": "dryrun", "source_label": "x",
        "file_path": str(p),
        "sampling_rate_hz": 100, "n_leads": 1, "duration_s": 10.0,
        "split": "train" if i < 48 else "val",
    })
pq.write_table(pa.Table.from_pylist(rows), root / "manifest_split.parquet")
PY

# saltar download/manifest/splits y arrancar desde pretrain manualmente
```

Pero el flujo recomendado es siempre `scripts/train_autonomous.sh` con tier 1
real, aunque sea con `EPOCHS=1` para una primera pasada.
