#!/usr/bin/env bash
# Idempotent: ensures Clerk JWT template "supabase" exists (org_id for RLS).
# Requires: apps/web/.env.local with CLERK_SECRET_KEY=sk_test_...
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/apps/web/.env.local"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE — copy from apps/web/.env.example" >&2
  exit 1
fi
CLERK_SECRET_KEY="$(grep -E '^CLERK_SECRET_KEY=' "$ENV_FILE" | cut -d= -f2-)"
if [[ -z "$CLERK_SECRET_KEY" ]]; then
  echo "CLERK_SECRET_KEY empty in $ENV_FILE" >&2
  exit 1
fi
EXISTING="$(curl -sS "https://api.clerk.com/v1/jwt_templates" -H "Authorization: Bearer $CLERK_SECRET_KEY")"
if echo "$EXISTING" | grep -q '"name":"supabase"'; then
  echo 'Clerk JWT template "supabase" already exists.'
  exit 0
fi
curl -sS -X POST "https://api.clerk.com/v1/jwt_templates" \
  -H "Authorization: Bearer $CLERK_SECRET_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "supabase",
    "lifetime": 3600,
    "allowed_clock_skew": 5,
    "custom_signing_key": false,
    "claims": {
      "org_id": "{{org.id}}",
      "org_role": "{{org.role}}",
      "org_slug": "{{org.slug}}"
    }
  }' | python3 -m json.tool
echo 'Created JWT template "supabase".'
