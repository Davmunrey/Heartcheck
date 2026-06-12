# Axis

**Ruta canónica del monorepo (abre siempre esta carpeta en el IDE):** `~/dev/Heartcheck`.
> ⚠️ La copia en `~/Desktop/Heartcheck` vive en iCloud Drive y quedó *evicted/dataless*
> (archivos sin contenido local) — **no la uses**: cuelga servidores y entrenamientos.
> Detalle: [`docs/CANONICAL_PROJECT_PATH.md`](docs/CANONICAL_PROJECT_PATH.md).

Monorepo: **`apps/ml-api`** (FastAPI + OpenCV + PyTorch CNN-1D), **`apps/mobile`** (Flutter), **`apps/web`** (Next.js + Clerk + Supabase), y **`ml/`** (pipeline de entrenamiento standalone).

Documentación del stack ML standalone: [`docs/ML_STANDALONE_PIPELINE.md`](docs/ML_STANDALONE_PIPELINE.md).

## Requisitos

- Python 3.11+
- Flutter SDK 3.16+ (para `flutter pub get` / ejecutar la app)

## Arranque rápido

### 1) Instalar API (una vez)

Instala FastAPI, OpenCV, PyTorch, etc. en `apps/ml-api/.venv` y genera `web_public/static/sample_ecg.png`:

```bash
./scripts/install_backend.sh
```

### 2) Una sola URL: la app Next.js (:3000)

Axis vive bajo **una única URL de cara al usuario**: la app Next.js
(`http://localhost:3000`) = landing + producto + análisis. El ML API (:8000) es
un **servicio interno**; con `HEARTSCAN_WEB_APP_URL` configurado, `:8000/` y
`:8000/app` hacen **307 redirect** a `:3000`. (La consola estática heredada
`web_public/` queda retirada como superficie de usuario.)

Arranca back interno + front de una vez (`npm install` una vez):

```bash
npm run dev:stack   # FastAPI :8000 (interno) + Next.js :3000 (la URL)
# o por separado:
cd apps/ml-api && .venv/bin/uvicorn app.main:app --port 8000   # interno
cd apps/web && npm run dev                                      # http://localhost:3000
```

- **App (todo):** http://localhost:3000
- **API interna / OpenAPI:** http://localhost:8000/docs · http://localhost:8000/api/v1/meta

Variables:
- ML API: copia [`apps/ml-api/.env.example`](apps/ml-api/.env.example) → `apps/ml-api/.env`.
  Dev local: Clerk JWKS/issuer, `HEARTSCAN_ML_INTERNAL_TOKEN` (== el de la web),
  `HEARTSCAN_WEB_APP_URL=http://localhost:3000`, `HEARTSCAN_REQUIRE_ORGANIZATION=false`.
- Web: copia `apps/web/.env.example` → `apps/web/.env.local`
  (Clerk + Supabase + `ML_API_URL` + `ML_API_INTERNAL_TOKEN`).

El análisis se ejecuta en un **server action** del Next.js que llama al ML API
con el JWT de Clerk. Tenancy (org-opcional) y despliegue una-URL:
[`docs/TENANCY.md`](docs/TENANCY.md), [`docs/AUTH_CLERK.md`](docs/AUTH_CLERK.md),
[`docs/DEPLOY_ONE_DOMAIN.md`](docs/DEPLOY_ONE_DOMAIN.md),
[`docs/E2E_CLIENTS.md`](docs/E2E_CLIENTS.md).

### Mobile

```bash
cd apps/mobile
flutter pub get
flutter run
```

Configurar URL del API (por defecto Android emulator: `10.0.2.2:8000`, iOS simulator: `localhost:8000`).

### Docker

```bash
docker compose -f infra/docker-compose.yml up --build
```

### Entrenar el clasificador con datasets públicos

Axis ships untrained; cargar pesos reales requiere descargar uno o varios
de los datasets catalogados en [`docs/DATASHEET_TRAINING.md`](docs/DATASHEET_TRAINING.md).

**Modo autónomo** — un único comando que descarga, entrena, calibra, evalúa y
promociona si bate al campeón. Idempotente, apto para cron / CI; ver
[`docs/AUTONOMOUS_TRAINING.md`](docs/AUTONOMOUS_TRAINING.md):

```bash
MODEL_VERSION="ecg-resnet1d-$(date +%Y%m%d)" scripts/train_autonomous.sh
# Con imágenes:
IMAGE_DATASETS="ecg_image_database,ptb_xl_image_17k" \
  MODEL_VERSION="ecg-resnet1d-img-$(date +%Y%m%d)" \
  scripts/train_autonomous.sh
```

**Modo manual** (cuando se quiere control fino sobre cada paso) en una sola GPU:

```bash
# Listar todos los datasets soportados (licencias incluidas)
apps/ml-api/.venv/bin/python -m ml.datasets.cli list

# Tier 1 (CC BY 4.0, ~6 GB): PTB-XL + Chapman + CinC 2017 + BUT QDB
scripts/download_datasets_tier1.sh
# Imágenes (~80 GB) cuando haya disco
scripts/download_datasets_images.sh

# Manifest unificado + splits patient-stratified
apps/ml-api/.venv/bin/python -m ml.datasets.cli manifest \
  --root data/raw --datasets ptb_xl chapman_shaoxing cinc2017 \
  --out data/manifests/tier1.parquet
apps/ml-api/.venv/bin/python -m ml.datasets.splits \
  --manifest data/manifests/tier1.parquet --out data/manifests/tier1_split.parquet

# Pretrain → calibrar → manifest YAML
apps/ml-api/.venv/bin/python -m ml.training.pretrain \
  --manifest data/manifests/tier1_split.parquet --out runs/pretrain_v1 --epochs 10
apps/ml-api/.venv/bin/python -m ml.training.calibrate \
  --logits runs/pretrain_v1/val_logits.npz \
  --checkpoint runs/pretrain_v1/checkpoint.pt --report runs/pretrain_v1/calibration.json
apps/ml-api/.venv/bin/python -m ml.training.emit_manifest \
  --checkpoint runs/pretrain_v1/checkpoint.pt \
  --training-summary runs/pretrain_v1/training_summary.json \
  --calibration runs/pretrain_v1/calibration.json \
  --datasets ptb_xl chapman_shaoxing cinc2017 \
  --model-version ecg-resnet1d-1.0.0

# Apuntar el backend al checkpoint
export HEARTSCAN_MODEL_PATH=runs/pretrain_v1/checkpoint.pt
./scripts/run_local.sh
```

## Documentación

Toda la documentación vive bajo [`docs/`](docs/) e indexada en
[`docs/MASTER_DOCS.md`](docs/MASTER_DOCS.md). Empieza por ese archivo:
contiene secciones por área (arquitectura, ML, datasets, UX, ops,
seguridad, ADRs) y la regla operativa para añadir nuevos documentos.

> Regla del repo: cualquier doc nueva o modificada se enlaza desde
> `docs/MASTER_DOCS.md`. La regla está formalizada en
> [`.cursor/rules/master-docs.mdc`](.cursor/rules/master-docs.mdc).

## Aviso

Axis es un producto **informativo/educativo**. No sustituye valoración médica ni un electrocardiograma clínico completo.
