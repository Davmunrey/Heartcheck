# Contributing

## ML API (FastAPI)

```bash
cd apps/ml-api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
ruff check app tests
pytest
```

Variables de entorno: copiar [`apps/ml-api/.env.example`](apps/ml-api/.env.example) a `apps/ml-api/.env` y ajustar para desarrollo. **Nunca** dejar valores por defecto en producción: `app.main._refuse_insecure_production_defaults` aborta el arranque si detecta JWT débil, API key por defecto con auth legacy activa, o CORS `*`.

## Web Next.js (`apps/web`)

Desde la **raíz del repo** (workspaces npm):

```bash
npm install
npm run dev          # arranca @heartscan/web (Turborepo)
```

Variables: [`apps/web/.env.example`](apps/web/.env.example) → `.env.local` (Clerk, Supabase, `ML_API_URL`).

## Mobile (Flutter)

Requires Flutter SDK. From `apps/mobile/`:

```bash
flutter pub get
flutter gen-l10n
flutter analyze
flutter test
```

Use `--dart-define=HEARTSCAN_API_BASE=http://...`, `HEARTSCAN_API_KEY=...` (o `HEARTSCAN_ACCESS_TOKEN=...`) cuando apuntes a una API distinta a la default.

## Reglas no negociables

- **Tests verdes**: `pytest` en `apps/ml-api/` antes de subir.
- **Documentación en el master index**: toda la documentación del repo
  vive bajo [`docs/`](docs/) y debe estar enlazada desde
  [`docs/MASTER_DOCS.md`](docs/MASTER_DOCS.md). Cualquier PR que cree o
  modifique un `*.md` también edita el índice maestro. La regla está
  formalizada en [`.cursor/rules/master-docs.mdc`](.cursor/rules/master-docs.mdc).
  Excepciones únicas (READMEs de subpaquete) listadas en la sección 8 del
  master index.
- **Seguridad por defecto**: ningún PR puede introducir secretos en el
  repo, defaults débiles, ni `eval`/deserialización insegura. Cargar
  checkpoints siempre con `weights_only=True` (ver
  [`apps/ml-api/app/services/inference.py`](apps/ml-api/app/services/inference.py)).
  Para cambios sensibles, leer [`docs/SECURITY_PROGRAM.md`](docs/SECURITY_PROGRAM.md)
  antes de empezar.
- **Disclaimer médico**: el producto es informativo/educativo. No
  introducir copy con pretensión diagnóstica. Ver
  [`docs/WHEN_NOT_TO_USE.md`](docs/WHEN_NOT_TO_USE.md).
- **Accesibilidad**: contraste AA, foco visible, objetivos táctiles
  ≥44px en cualquier UI nueva. Ver [`docs/UI_DESIGN_SYSTEM.md`](docs/UI_DESIGN_SYSTEM.md).
