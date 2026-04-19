#!/usr/bin/env bash
# Idempotent Clerk + Supabase setup without browser clicks (where APIs exist).
#
# 1) Clerk JWT template "supabase" — needs CLERK_SECRET_KEY in apps/web/.env.local
# 2) Supabase third-party Clerk (OIDC + JWKS) — needs SUPABASE_ACCESS_TOKEN in .env.local
#
# DB migration is separate: run infra/supabase/migrations/*.sql once in SQL Editor or via supabase db push.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> 1/2 Clerk JWT template 'supabase'"
./scripts/ensure_clerk_jwt_template_supabase.sh

echo "==> 2/2 Supabase third-party auth (Management API)"
ENV_LOCAL="$ROOT/apps/web/.env.local"
if [[ -f "$ENV_LOCAL" ]] && grep -qE '^SUPABASE_ACCESS_TOKEN=.+' "$ENV_LOCAL"; then
  python3 "$ROOT/scripts/ensure_supabase_clerk_third_party.py"
else
  echo "Skipped: add SUPABASE_ACCESS_TOKEN to apps/web/.env.local (PAT from https://supabase.com/dashboard/account/tokens )"
  echo "Then run: python3 scripts/ensure_supabase_clerk_third_party.py"
fi

echo "Done."
