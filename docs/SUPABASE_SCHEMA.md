# Supabase schema (Postgres + Storage)

Authoritative SQL migration: [`infra/supabase/migrations/20250419120000_heartscan_multitenant.sql`](../infra/supabase/migrations/20250419120000_heartscan_multitenant.sql).

## Tables (`public`)

| Table | Purpose |
|-------|---------|
| `companies` | Tenant metadata (`id` = Clerk org id) |
| `memberships` | Mirror of org membership (optional cache) |
| `analyses` | Persisted analysis results + JSON payload |
| `usage_daily` | Daily request counts per org |
| `feedback` | Wrong-result feedback queue |
| `api_keys` | Hashed integration keys per org |
| `audit_log` | Security-sensitive actions |

## RLS

Policies require JWT claim `org_id` (from Clerk template `supabase`) to match `company_id` on each row.

## Storage

Bucket **`ecg-uploads`** (private). Object paths: `{org_id}/{uuid}.{ext}` — policies use the first path segment as tenant id.

## Drizzle mirror

TypeScript schema for tooling: [`packages/db/src/schema.ts`](../packages/db/src/schema.ts).
