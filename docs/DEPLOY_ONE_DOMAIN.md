# Deploy — one domain

Axis runs as a **single public domain** (the Next.js app). The FastAPI ML
backend is an **internal service**, never exposed to users directly.

```
                ┌─────────────────────── ONE PUBLIC DOMAIN ───────────────────────┐
   browser ───▶ │  Next.js (apps/web)                                              │
                │   • landing, pricing, copilot, login, dashboard, /analyze        │
                │   • server actions  ── ML_API_URL ──▶  FastAPI (internal)        │
                │   • /ml-api/*  ── Next rewrite ──▶  FastAPI (same origin, no CORS)│
                └──────────────────────────────────────────────────────────────────┘
                                                         │
                                  ┌──────────────────────▼───────────────────────┐
                                  │  FastAPI (apps/ml-api) — PRIVATE               │
                                  │   • /api/v1/analyze/signal (27-class model)    │
                                  │   • /api/v1/meta, /docs                        │
                                  └────────────────────────────────────────────────┘
```

## How the two talk

| Path | Mechanism |
|------|-----------|
| `/analyze` upload | Next **server action** → `fetch(${ML_API_URL}/api/v1/analyze/signal)` (server-to-server, Clerk JWT + optional internal token) |
| Browser → ML API | `GET /ml-api/api/v1/*` → Next **rewrite** → `${ML_API_URL}/api/v1/*` (same origin, no CORS) |

`ML_API_URL` defaults to `http://localhost:8000` for local dev; set it to the
**private** backend address in prod (internal DNS / service URL / sidecar).

## Local dev (one command each)

```bash
# 1. ML backend (private), serves the 27-class model by default
cd apps/ml-api && HEARTSCAN_API_KEY=dev-key .venv/bin/uvicorn app.main:app --port 8000

# 2. The app (the domain) — talks to :8000 via ML_API_URL
cd apps/web && ML_API_URL=http://localhost:8000 npm run dev   # http://localhost:3000
```

Everything users touch is under `http://localhost:3000`. `:8000` is internal.

## Prod

- Deploy `apps/web` to the public domain (Vercel/host). Set `ML_API_URL` to the
  private FastAPI URL + `ML_API_INTERNAL_TOKEN`.
- Deploy `apps/ml-api` privately (no public ingress). It still enforces auth.
- **`web_public/`** (the FastAPI-served static site) is a legacy/standalone
  surface — not the public face when the Next app is deployed.
