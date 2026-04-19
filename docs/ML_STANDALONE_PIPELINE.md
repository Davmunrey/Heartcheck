# Pipeline ML standalone (`ml/` + `web/`)

Stack opcional en la raíz del monorepo: **Python** [`ml/`](../ml/) (entrenamiento PTB-XL + FastAPI `heartscan_ml`) y **React/Vite** [`web/`](../web/) (subida de imagen y resultados vía proxy `/api`).

Es independiente del **backend** principal en `apps/ml-api/` (producto SaaS). Sirve para entrenar modelos, experimentar y levantar un API mínimo sin la app FastAPI grande.

## Arranque conjunto (API + Vite)

Desde la raíz del repo Heartcheck:

```bash
cd web
npm install
pip install -e "../ml[api]"   # una vez: dependencias del paquete heartscan-ml
npm run dev:stack
```

Esto levanta el **API en :8000** y la **web en :5174** con proxy `/api` → API.

## Solo backend (paquete `heartscan_ml`)

```bash
cd ml && pip install -e ".[api]" && heartscan-serve
```

## Solo frontend (API ya en marcha)

```bash
cd web && npm install && npm run dev
```

## Producción

1. Build estático: `cd web && npm run build` → `web/dist/`.
2. Sirve `dist` con nginx (u otro) y proxy inverso `location /api/ { proxy_pass http://127.0.0.1:8000/; }`.
3. O define al construir `VITE_HEARTSCAN_API=https://tu-api.example.com` (sin barra final).

## Docker (solo API del paquete `ml/`)

```bash
cd ml && docker build -t heartscan-api . && docker run --rm -p 8000:8000 -v "$PWD/checkpoints:/app/checkpoints" heartscan-api
```

Compose de referencia en la raíz: [`docker-compose.heartscan-ml.yml`](../docker-compose.heartscan-ml.yml).
