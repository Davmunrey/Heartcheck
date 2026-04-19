# HeartScan ML (ECG)

Pipeline de **entrenamiento** (PTB-XL + CNN1D), **inferencia** WFDB o **foto de papel**, **BPM** (SleepECG), **guardrails** y **API HTTP** (FastAPI).

## Requisitos

- Python 3.10+
- Para entrenar: [PTB-XL](https://physionet.org/content/ptb-xl/) y `PTBXL_DIR` apuntando a la raíz (`ptbxl_database.csv`, `records100/` / `records500/`).

## Instalación

```bash
cd ml
pip install -e ".[dev,api]"
```

Solo entrenamiento (sin API): `pip install -e ".[dev]"`.

## Entrenar

```bash
export PTBXL_DIR=/ruta/a/ptb-xl
heartscan-train --epochs 20 --device cpu
```

Checkpoints: `checkpoints/cnn1d_best.pt`.

## Evaluar (fold 10)

```bash
heartscan-eval --checkpoint checkpoints/cnn1d_best.pt --ptbxl-dir "$PTBXL_DIR"
```

## Inferencia WFDB (JSON completo)

```bash
heartscan-infer --record "$PTBXL_DIR/records100/00000/00001_lr"
```

## API HTTP (foto)

Arranca el servicio (carga el checkpoint si existe; si no, modelo sin entrenar):

```bash
export HEARTSCAN_CHECKPOINT=checkpoints/cnn1d_best.pt
heartscan-serve
```

Variables útiles: `HEARTSCAN_HOST`, `HEARTSCAN_PORT`, `HEARTSCAN_DEVICE`, `HEARTSCAN_CORS_ORIGINS` (lista separada por comas).

Probar:

```bash
curl -s -X POST "http://127.0.0.1:8000/v1/analyze" -F "file=@/ruta/imagen.png"
```

- `GET /health` — estado
- `GET /v1/meta` — versión de pipeline y modelo
- `POST /v1/analyze` — `multipart/form-data` campo `file` (PNG/JPEG)

## Docker

Desde el directorio `ml/`:

```bash
docker build -t heartscan-ml .
docker run --rm -p 8000:8000 -v "$PWD/checkpoints:/app/checkpoints" heartscan-ml
```

## Tests

```bash
pytest -q
```

## Interfaz web (React)

La app está en [`../web`](../web). Desde `../web`: `npm run dev:stack` (API + Vite con proxy `/api`). Ver [`docs/ML_STANDALONE_PIPELINE.md`](../docs/ML_STANDALONE_PIPELINE.md).

## Nota clínica

Uso investigación / educación; no sustituye valoración médica.
