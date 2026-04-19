# Multi-tenancy (Clerk Organizations)

Each **company** maps to a Clerk **Organization**.

- Users invite teammates via Clerk; roles (`admin`, `member`, …) come from Clerk.
- The active organization is selected with `<OrganizationSwitcher />` in [`apps/web/app/(app)/layout.tsx`](../apps/web/app/(app)/layout.tsx).
- Data in Supabase is partitioned by `company_id` (same value as Clerk’s org id). RLS policies compare `company_id` to `auth.jwt() ->> 'org_id'`.

If a user has no active organization, the dashboard prompts them to create one (`/onboarding/create-organization`).

## Service accounts

Server-to-server integrations should use **API keys** stored per org (table `api_keys` in [`SUPABASE_SCHEMA.md`](SUPABASE_SCHEMA.md)), not user passwords.
