# ADR 004 — Clerk Organizations as tenant boundary

## Status

Accepted

## Context

B2B SaaS requires isolation between customers without building a full custom identity system.

## Decision

- Use **Clerk Organizations** as the source of truth for companies/teams.
- Persist a mirror in Supabase (`companies`, `memberships`) updated via **Clerk webhooks** for reporting and joins.
- Row-level security keys off JWT claim **`org_id`** aligned with the active Clerk org.

## Consequences

- Users must select or create an org before features that consume org-scoped quotas/storage.
- Legacy email/password auth in the ML API remains available behind `HEARTSCAN_AUTH_LEGACY_ENABLED` for development and tests.
