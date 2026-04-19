# HeartScan — Deployment (Vercel + Fly.io + Supabase + Clerk)

This document defines **three environments**, required **secrets**, and how services connect.  
Clerk handles **users and Organizations** (companies). Supabase provides **Postgres + Storage** with **RLS** scoped by `org_id` in the JWT. The **ML API** (FastAPI + PyTorch) runs **outside** Vercel on Fly.io (or Render).

## Environments

| Environment | Purpose | Web | ML API | Supabase | Clerk |
|-------------|---------|-----|--------|----------|-------|
| **development** | Local dev | `pnpm dev` in `apps/web` | `uvicorn` in `apps/ml-api` | Local or Supabase dev project | Clerk dev instance |
| **preview** | PR previews on Vercel | Vercel Preview URL | Staging ML API URL | Supabase branch / dev DB | Clerk dev keys |
| **production** | Live users | Custom domain on Vercel | `api.*` on Fly.io | Supabase production | Clerk production |

## Variable matrix

### Next.js (`apps/web`) — public + server

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Yes | Clerk publishable key |
| `CLERK_SECRET_KEY` | Yes | Clerk secret (server only) |
| `CLERK_WEBHOOK_SECRET` | Yes (prod) | Svix secret for Clerk webhooks |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase anon key (RLS with user JWT) |
| `SUPABASE_SERVICE_ROLE_KEY` | Server actions / webhooks only | Bypass RLS for admin writes — **never** expose to browser |
| `ML_API_URL` | Yes | Base URL of FastAPI ML service (e.g. `https://api.example.com`) |
| `ML_API_INTERNAL_TOKEN` | Recommended | Shared secret: Next.js sends `X-Internal-Token`; ML API verifies |

Optional:

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_APP_URL` | Canonical site URL (redirects, emails) |

### Clerk JWT template for Supabase

Create a JWT template named **`supabase`** in the Clerk dashboard with claims that Supabase RLS expects, for example:

- `org_id` — active Clerk Organization ID
- `org_role` — member role in that org
- `org_slug` — optional slug

See [AUTH_CLERK.md](AUTH_CLERK.md) for the exact claim names used by this repo.

### ML API (`apps/ml-api`) — FastAPI

| Variable | Required | Description |
|----------|----------|-------------|
| `HEARTSCAN_ENV` | Yes in prod | `production` or `development` |
| `HEARTSCAN_CLERK_ISSUER` | Yes | Clerk Frontend API URL / issuer for JWT validation |
| `HEARTSCAN_CLERK_AUDIENCE` | Optional | Expected `aud` if you set one on tokens |
| `HEARTSCAN_JWKS_URL` | Yes | Clerk JWKS URL (often `https://<clerk-domain>/.well-known/jwks.json`) |
| `HEARTSCAN_DATABASE_URL` | Yes | Supabase **pooler** Postgres URL (for quotas, analyses insert) |
| `HEARTSCAN_SUPABASE_SERVICE_ROLE_KEY` | If ML uses admin Supabase client | Service role for server-side DB from ML API |
| `HEARTSCAN_ML_INTERNAL_TOKEN` | Recommended | Must match `ML_API_INTERNAL_TOKEN` from Vercel |
| `HEARTSCAN_MODEL_PATH` | Optional | Path to classifier checkpoint |
| `HEARTSCAN_CORS_ORIGINS` | Yes in prod | Vercel app origin(s), comma-separated — **not** `*` |

Legacy (deprecated): `HEARTSCAN_JWT_SECRET_KEY`, `HEARTSCAN_API_KEY` — removed when Clerk-only auth is enforced.

### Vercel project settings

- **Root directory**: repository root (monorepo) or `apps/web` if the project is scoped.
- **Install**: `pnpm install`
- **Build**: `pnpm exec turbo run build --filter=web`
- **Output**: Next.js default (`.next`)

Link environment variables per environment (Preview vs Production).

### Fly.io (ML API)

- Use the Dockerfile under `apps/ml-api` (or repo root if single Dockerfile).
- Set secrets via `fly secrets set KEY=value`.
- Attach at least **2 GB** RAM for PyTorch + OpenCV workloads.

## Network flow

1. Browser loads Next.js from Vercel; Clerk session established.
2. Server Actions / Route Handlers call Supabase with the user’s JWT (`getToken({ template: 'supabase' })`).
3. Analyze flow: Next.js uploads image to Supabase Storage, then `POST` to `ML_API_URL/api/v1/analyze` with `Authorization: Bearer <Clerk session JWT>` and `X-Internal-Token`.
4. ML API validates JWT via **JWKS**, checks internal token, runs inference, writes quota/usage to Postgres using service role or pooled connection.

## Checklist before production

- [ ] No default JWT secrets or `CORS_ORIGINS=*` with production env.
- [ ] `ML_API_INTERNAL_TOKEN` set and identical on Vercel and Fly.
- [ ] Clerk **Organizations** enabled; JWT template `supabase` deployed.
- [ ] Supabase RLS policies tested (`infra/supabase/tests/rls.sql`).
- [ ] Webhook endpoints use **Svix** verification only.

## See also

- [AUTH_CLERK.md](AUTH_CLERK.md) — Clerk + Supabase integration
- [TENANCY.md](TENANCY.md) — companies and roles
- [SUPABASE_SCHEMA.md](SUPABASE_SCHEMA.md) — tables and RLS
