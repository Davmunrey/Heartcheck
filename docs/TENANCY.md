# Multi-tenancy

The tenant of an `/analyze` request is derived from the Clerk session. There are
two modes, controlled by `HEARTSCAN_REQUIRE_ORGANIZATION` on the ML API.

## Org-required (B2B, prod default — `HEARTSCAN_REQUIRE_ORGANIZATION=true`)

Each **company** maps to a Clerk **Organization**.

- Requires the Clerk **Organizations** feature enabled on the instance.
- Users invite teammates via Clerk; roles (`admin`, `member`, …) come from Clerk.
- Data in Supabase is partitioned by `company_id` (= Clerk org id). RLS policies
  compare `company_id` to `auth.jwt() ->> 'org_id'`.
- The Next.js server action sends the active org as `X-Organization-Id`
  (trusted only when `X-Internal-Token` matches), and the ML API returns
  `403 ORG_REQUIRED` if no org is present.

## Org-optional (single-tenant — `HEARTSCAN_REQUIRE_ORGANIZATION=false`)

For setups without the Clerk Organizations feature (or single-user/dev):

- No Clerk Organization is needed. The tenant becomes `clerk-user:<sub>`
  (derived from the verified Clerk user id) in
  [`apps/ml-api/app/api/deps.py`](../apps/ml-api/app/api/deps.py).
- The Next.js `/analyze` flow does **not** require an org: it omits
  `X-Organization-Id` when none is active, and `getBillingStatus()` falls back
  to a per-user trial. The `<OrganizationSwitcher>` and the
  `create-organization` guard were removed from
  [`apps/web/app/(app)/layout.tsx`](../apps/web/app/(app)/layout.tsx) /
  [`analyze/page.tsx`](../apps/web/app/(app)/analyze/page.tsx) for this mode.

Switching to prod B2B = enable Clerk Organizations + set
`HEARTSCAN_REQUIRE_ORGANIZATION=true` (and restore the org UI).

## Service accounts

Server-to-server integrations should use **API keys** stored per tenant (table
`api_keys` in [`SUPABASE_SCHEMA.md`](SUPABASE_SCHEMA.md)), not user passwords.
