# Security Audit — Axis (Heartcheck)

**Date:** 2026-06-09 · **Scope:** `apps/web` (Next.js), `apps/ml-api` (FastAPI),
`packages/*`, `web_public/` · **Type:** white-box OWASP Top-10 review +
dependency/secret/SAST scan on the developer's own repository (authorized).

## Executive summary

Overall posture is **good**. No injection sinks, no hardcoded secrets, parameter
isolation (Clerk Orgs + Supabase RLS) and webhook signature verification are in
place, and the FastAPI surface already shipped strong security headers. The audit
found and **fixed** one batch of vulnerable dependencies (incl. high-severity
Clerk auth packages) and hardened the Next.js security headers (clickjacking,
HSTS, framework fingerprinting). Residual risk is limited to three dev/build-time
moderate advisories with no safe upstream fix.

## Findings & remediation

| # | OWASP | Finding | Severity | Status |
|---|-------|---------|----------|--------|
| 1 | A06 | Vulnerable npm deps: `@clerk/{nextjs,backend,react,shared}`, `js-cookie` (high); `ws`, `svix`, `uuid`, `brace-expansion` (mod); `vitest` (critical, dev-only) | High/Crit | **Fixed** — `npm audit fix` + `vitest`→4 (10 vulns → 3) |
| 2 | A05 | No `X-Frame-Options` / CSP `frame-ancestors` on the Next app → clickjacking | Medium | **Fixed** — `X-Frame-Options: DENY` + `frame-ancestors 'none'` |
| 3 | A02/A05 | No HSTS header on the Next app | Medium | **Fixed** — `Strict-Transport-Security` 2y, `includeSubDomains; preload` |
| 4 | A05 | `X-Powered-By: Next.js` framework fingerprinting | Low | **Fixed** — `poweredByHeader: false` |
| 5 | A05 | No `Permissions-Policy` / CSP `base-uri`/`form-action` | Low | **Fixed** — added all three |

### Verified safe (no action needed)

- **A03 Injection** — no `shell=True`, `os.system`, `eval`, `pickle.load`,
  `yaml.load`, or `dangerouslySetInnerHTML`/`innerHTML` anywhere in app code.
- **A08 Deserialization** — every `torch.load` uses `weights_only=True`; the only
  unsafe fallback is gated behind `HEARTSCAN_ALLOW_UNSAFE_TORCH_LOAD` (off by
  default).
- **A02 Secrets** — no hardcoded keys/tokens in tracked source; `.env*` ignored.
- **A01 Access control** — Clerk middleware protects all non-public routes;
  `/dashboard`, `/analyze`, `/settings/billing` correctly redirect to sign-in.
  Tenant isolation via Clerk Organizations + Supabase RLS by `org_id`.
- **A08 Integrity** — Clerk (svix) and Stripe webhooks verify signatures before
  mutating; Stripe handler no-ops safely when the secret is unset.
- **A10 SSRF** — the API does not fetch user-supplied URLs.
- **API headers** — FastAPI already sends `X-Frame-Options: DENY`, HSTS, CSP with
  `frame-ancestors 'none'`, `nosniff`, `Referrer-Policy`.

## Accepted residual risk

3 **moderate, dev/build-time-only** npm advisories remain (`esbuild`, `next`,
`postcss`). Mitigations applied:

- **`postcss`** — top-level pinned to `>=8.5.10` (8.5.15, patched) via npm
  `overrides`. The advisory still flags the copy **vendored inside `next@16`**,
  which `overrides` cannot reach (Next bundles its own); npm's only listed "fix"
  is a `next` major **downgrade to a 9.x canary** that would break the framework.
  The PostCSS bug is XSS in CSS *stringify* output — only reachable if
  attacker-controlled CSS is run through the stringifier, which the Next build
  does not do with user input. **Not runtime-exploitable.**
- **`esbuild`** — overridden to `^0.27` (matches what `vite@8`/`vitest@4`
  require, and is the patched range). It is a **dev/test-only** dependency
  (vitest in `packages/api-client`), never shipped to production. The dev-server
  request advisory only applies while running the local test server.
- **`next`** — flagged transitively via the vendored `postcss` above; clears
  when Next ships a patched `postcss` in the 16.x line.

None are reachable in the deployed runtime. Tracked via `npm audit` in CI;
re-evaluate on the next Next.js / Vite minor.

## Re-run

```bash
cd apps/web && npm audit
git grep -nIE "shell=True|eval\(|pickle.load|dangerouslySetInnerHTML"   # SAST
git grep -nIE "torch\.load\(" -- apps ml | grep -v weights_only         # A08
curl -sI https://<host>/ | grep -iE "x-frame|strict-transport|content-security"
```
