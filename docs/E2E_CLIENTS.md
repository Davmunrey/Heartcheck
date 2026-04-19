# E2E multi-cliente: web SPA, web estática y mobile contra el mismo backend

Tres superficies de cliente convergen en el mismo API FastAPI ([`apps/ml-api/app/main.py`](../apps/ml-api/app/main.py)):

1. **Next.js (prod/dev)** — [`apps/web/`](../apps/web/), Clerk + server actions → `ML_API_URL/api/v1/analyze`.
2. **Web estática** — [`web_public/app.html`](../web_public/app.html), servida por FastAPI bajo `/app` (legacy).
3. **Mobile Flutter** — [`apps/mobile/`](../apps/mobile/), apunta al backend con `--dart-define=HEARTSCAN_API_BASE=...`.

## Arranque del backend con cuotas/JWT activos

```bash
./scripts/install_backend.sh   # primera vez
./scripts/run_local.sh         # uvicorn :8000 con .env (HEARTSCAN_API_KEY=dev-key-change-me)
```

Variables relevantes ya documentadas en [`apps/ml-api/.env.example`](../apps/ml-api/.env.example).

## Next.js (`apps/web`)

```bash
# desde la raíz del monorepo
npm install
npm run dev
```

- Variables: [`apps/web/.env.example`](../apps/web/.env.example) → `.env.local` (`ML_API_URL`, Clerk, Supabase).
- El análisis usa `Authorization: Bearer` (sesión Clerk) + `X-Organization-Id` + `X-Internal-Token` (opcional).

## Web estática (servida por el propio backend)

- Abrir `http://127.0.0.1:8000/app` con el backend en marcha.
- Tiene su propio formulario de registro/login que usa los endpoints `/api/v1/auth/*` y guarda el JWT en `localStorage`.
- La generación de PDF (`POST /api/v1/reports/pdf`) reutiliza ese token.

## Mobile (Flutter)

```bash
cd apps/mobile
flutter pub get
flutter run \
  --dart-define=HEARTSCAN_API_BASE=http://10.0.2.2:8000 \   # Android emulator → host loopback
  --dart-define=HEARTSCAN_API_KEY=dev-key-change-me
```

- iOS simulator: usar `http://localhost:8000`.
- Producción: pasar `HEARTSCAN_ACCESS_TOKEN` en lugar de la API key (cliente cambia la cabecera automáticamente; ver [`apps/mobile/lib/core/api_client.dart`](../apps/mobile/lib/core/api_client.dart)).

## Flujo verificado end-to-end

1. Registrar cuenta en cualquier superficie → `POST /api/v1/auth/register` → 201.
2. Login → `POST /api/v1/auth/login` → 200 con `access_token`.
3. Subir imagen → `POST /api/v1/analyze` con `Authorization: Bearer <token>` o `X-API-Key` → 200 con `AnalysisResponse`.
4. Solicitar PDF → `POST /api/v1/reports/pdf` con el JSON anterior → archivo PDF.
5. Revisar cuota: `Settings.beta_daily_analysis_quota`; al excederse, `429 QUOTA_EXCEEDED` (ver [`apps/ml-api/app/api/routes/analyze.py`](../apps/ml-api/app/api/routes/analyze.py)).

## Reproducible en Docker

```bash
docker compose -f infra/docker-compose.yml up --build
```

Igual que arriba, pero el backend escucha en :8000 contra Postgres (servicio `postgres`). Las superficies cliente apuntan a ese puerto.

## Test de contrato (humo manual)

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/api/v1/meta
curl -s -X POST http://127.0.0.1:8000/api/v1/analyze \
  -H "X-API-Key: dev-key-change-me" \
  -H "Accept-Language: es" \
  -F "file=@web_public/static/sample_ecg.png"
```
