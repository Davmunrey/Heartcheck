# Clerk authentication

Axis uses [Clerk](https://clerk.com) for **users**, and optionally **Organizations**
(multi-tenant companies). Organizations are required only when
`HEARTSCAN_REQUIRE_ORGANIZATION=true` (prod B2B); in single-tenant mode the
tenant is derived per-user. See [`TENANCY.md`](TENANCY.md).

## JWT template `supabase`

Create a JWT template named **`supabase`** so the Supabase client can pass a token that includes RLS claims.

**From the repo (idempotent):** run `./scripts/ensure_clerk_jwt_template_supabase.sh` from the monorepo root (requires `CLERK_SECRET_KEY` in `apps/web/.env.local`). Or create the template manually in the [Clerk JWT templates](https://dashboard.clerk.com/~/jwt-templates) UI with the same name and claims below.

Claims to include:

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

- `HEARTSCAN_CLERK_JWKS_URL` — Clerk JWKS URL (e.g.
  `https://<instance>.clerk.accounts.dev/.well-known/jwks.json`; the instance
  domain is base64-encoded inside the `pk_*` publishable key)
- `HEARTSCAN_CLERK_ISSUER` — issuer URL (optional, strengthens validation)
- `HEARTSCAN_ML_INTERNAL_TOKEN` — shared secret, must equal `ML_API_INTERNAL_TOKEN`
  in the web app (authorizes the trusted `X-Organization-Id` header)
- `HEARTSCAN_REQUIRE_ORGANIZATION` — `true` (B2B) or `false` (single-tenant;
  tenant becomes `clerk-user:<sub>`)

When `JWKS_URL` is set the ML API verifies Bearer tokens as Clerk RS256 JWTs;
a valid token with no org returns `403 ORG_REQUIRED` only in org-required mode.
See [`DEPLOYMENT.md`](DEPLOYMENT.md) and [`DEPLOY_ONE_DOMAIN.md`](DEPLOY_ONE_DOMAIN.md).

## Webhooks

`POST /api/webhooks/clerk` in the Next.js app verifies **Svix** signatures using `CLERK_WEBHOOK_SECRET` and is the hook for syncing organizations into Supabase (implement service-role upserts there).
