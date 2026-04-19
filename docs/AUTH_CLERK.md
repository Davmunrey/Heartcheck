# Clerk authentication

HeartScan uses [Clerk](https://clerk.com) for **users** and **Organizations** (multi-tenant companies).

## JWT template `supabase`

Create a JWT template named **`supabase`** in the Clerk dashboard so the Supabase client can pass a token that includes RLS claims:

- `org_id` — active Clerk Organization ID (required for row-level security)
- `org_role` — optional role string
- `org_slug` — optional slug

The Next.js helper [`apps/web/lib/supabase/server.ts`](../apps/web/lib/supabase/server.ts) calls `getToken({ template: 'supabase' })`.

## ML API (FastAPI)

The same **session JWT** can be sent to `POST /api/v1/analyze` as `Authorization: Bearer …`.

If the session token does not embed `org_id`, the server action also sends:

- `X-Organization-Id` — active org (from Clerk `auth()`)
- `X-Internal-Token` — must match `HEARTSCAN_ML_INTERNAL_TOKEN` / `ML_API_INTERNAL_TOKEN` when set

Configure the ML API with:

- `HEARTSCAN_CLERK_JWKS_URL` — Clerk JWKS URL
- `HEARTSCAN_CLERK_ISSUER` — issuer URL (optional, strengthens validation)

See [`DEPLOYMENT.md`](DEPLOYMENT.md).

## Webhooks

`POST /api/webhooks/clerk` in the Next.js app verifies **Svix** signatures using `CLERK_WEBHOOK_SECRET` and is the hook for syncing organizations into Supabase (implement service-role upserts there).
