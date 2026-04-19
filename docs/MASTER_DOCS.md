# HeartScan — Master docs index

> **Single source of truth** for every piece of project documentation.
> If you write or change docs and they aren't linked from here, they
> don't exist for the team. The rule that enforces this lives in
> [`.cursor/rules/master-docs.mdc`](../.cursor/rules/master-docs.mdc).

The repository keeps **all** narrative documentation under [`docs/`](.).
Sub-directory `README.md` files are allowed only for *package-local* setup
notes (Flutter app, ML package, weights folder, etc.) and must link back to
this index.

## Quick start

| If you want to… | Read |
|---|---|
| Get the project running locally | [`../README.md`](../README.md) |
| Contribute / open a PR | [`../CONTRIBUTING.md`](../CONTRIBUTING.md) |
| Understand the system at a glance | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Know when **not** to use HeartScan | [`WHEN_NOT_TO_USE.md`](WHEN_NOT_TO_USE.md) |

## 1. Product, scope and onboarding

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — components, data flow, public endpoints.
- [`SAAS_WEB_ROADMAP.md`](SAAS_WEB_ROADMAP.md) — long-term SaaS plan.
- [`CANONICAL_PROJECT_PATH.md`](CANONICAL_PROJECT_PATH.md) — repo location convention.
- [`E2E_CLIENTS.md`](E2E_CLIENTS.md) — running web SPA, web static and mobile against the same backend.
- [`API_PARITY.md`](API_PARITY.md) — FastAPI vs `heartscan_ml` response contract.
- [`REPORTING.md`](REPORTING.md) — server-side PDF report endpoint.
- [`i18n.md`](i18n.md) — Spanish/English handling across clients and API.

## 2. ML pipeline and evaluation

- [`ML_STANDALONE_PIPELINE.md`](ML_STANDALONE_PIPELINE.md) — `ml/` package overview.
- [`ml_eval.md`](ml_eval.md) — evaluation harness, metrics, release gate.
- [`algorithms/quality_gate.md`](algorithms/quality_gate.md) — extraction quality v1 + v2 thresholds.
- [`MODEL_CARD.md`](MODEL_CARD.md) — model card (Mitchell et al. format).
- [`AUTONOMOUS_TRAINING.md`](AUTONOMOUS_TRAINING.md) — one-command training orchestrator + cron template.

## 3. Datasets and labels

- [`DATASHEET_SYNTH.md`](DATASHEET_SYNTH.md) — synthetic eval set (`synth_v1`).
- [`DATASHEET_TRAINING.md`](DATASHEET_TRAINING.md) — every public dataset HeartScan can train against.
- [`LABEL_HARMONIZATION.md`](LABEL_HARMONIZATION.md) — SCP-ECG / SNOMED-CT / CinC → 3-class HeartScan mapping.
- [`RESTRICTED_DATASETS.md`](RESTRICTED_DATASETS.md) — UK Biobank / CODE full / MIMIC access procedure.

## 4. UX and design system

- [`UI_DESIGN_SYSTEM.md`](UI_DESIGN_SYSTEM.md) — dual-skin doctrine (lab dark vs SaaS light) and tokens.

## 5. Operations and beta

- [`DEPLOYMENT.md`](DEPLOYMENT.md) — Vercel + Fly.io + Supabase + Clerk env matrix and checklists.
- [`OBSERVABILITY.md`](OBSERVABILITY.md) — logs, metrics, alerts.
- [`BETA_SHIPPING.md`](BETA_SHIPPING.md) — TestFlight / Play closed testing checklist.
- [`INFRA_STAGING_PROD.md`](INFRA_STAGING_PROD.md) — staging vs prod infra notes.
- [`QA_LOAD_I18N.md`](QA_LOAD_I18N.md) — load + i18n QA.
- [`runbooks/incident.md`](runbooks/incident.md) — on-call runbook.

## 6. Security, privacy and compliance

- [`SECURITY_PROGRAM.md`](SECURITY_PROGRAM.md) — threat model + applied controls.
- [`SECURITY_CVE.md`](SECURITY_CVE.md) — CVE process, exceptions, secret rotation.
- [`PRIVACY.md`](PRIVACY.md) — internal privacy posture and user rights.
- [`legal/DRAFT_NOTICE.md`](legal/DRAFT_NOTICE.md) — disclaimer for draft legal artifacts.

## 7. Architecture decisions (ADRs)

- [`adr/0001-record-architecture-decisions.md`](adr/0001-record-architecture-decisions.md)
- [`adr/001-auth-jwt-sqlite-postgres.md`](adr/001-auth-jwt-sqlite-postgres.md)
- [`adr/002-stripe-billing-plan.md`](adr/002-stripe-billing-plan.md)
- [`adr/003-monorepo-pnpm-turbo.md`](adr/003-monorepo-pnpm-turbo.md) — pnpm workspaces + Turborepo layout.
- [`adr/004-clerk-orgs-as-tenant.md`](adr/004-clerk-orgs-as-tenant.md) — Clerk Organizations as tenant boundary.
- [`adr/005-split-vercel-fly.md`](adr/005-split-vercel-fly.md) — Next.js on Vercel, ML API on Fly.io.

## 8. Sub-package READMEs (allowed exceptions)

Package-local READMEs that document setup or licence specifics. They must
link back here and must not duplicate content already in `docs/`.

- [`../apps/mobile/README.md`](../apps/mobile/README.md) — Flutter client.
- [`../ml/README.md`](../ml/README.md) — `ml/` standalone package.
- [`../apps/ml-api/weights/README.md`](../apps/ml-api/weights/README.md) — checkpoint storage.
- [`../data/real_eval/README.md`](../data/real_eval/README.md) — real-photo eval set protocol.
- [`../references/README.md`](../references/README.md) — third-party reference code.

## 9. How to add a new document

1. Place the file under [`docs/`](.) (use the existing sub-folder if it
   matches: `algorithms/`, `runbooks/`, `legal/`, `adr/`, `prometheus/`,
   `grafana/`).
2. Link it from the relevant section of this index in the same PR. PRs
   that touch documentation **must** also touch this file.
3. If the document is package-local (Flutter, ML, etc.), add it under the
   corresponding `README.md` instead and reference it from section 8.
4. Don't park docs in chat exports, Notion, Google Docs, or random
   sub-folders. The repo is the source of truth.

## 10. Multi-tenant SaaS (Clerk + Supabase + Vercel)

- [`DEPLOYMENT.md`](DEPLOYMENT.md) — environments, secrets, Vercel/Fly wiring.
- [`AUTH_CLERK.md`](AUTH_CLERK.md) — Clerk + JWT template `supabase`, webhooks.
- [`TENANCY.md`](TENANCY.md) — organizations, roles, invitations.
- [`SUPABASE_SCHEMA.md`](SUPABASE_SCHEMA.md) — tables, RLS, storage policies.

The [Cursor rule](../.cursor/rules/master-docs.mdc) makes this enforceable
when working through Cursor; for plain Git contributors the same rule is
duplicated under `.github/PULL_REQUEST_TEMPLATE.md` (when it exists).
