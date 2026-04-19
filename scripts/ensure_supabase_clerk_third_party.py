#!/usr/bin/env python3
"""
Idempotent: register Clerk as Supabase third-party auth (OIDC issuer + JWKS).

Uses Supabase Management API:
  POST /v1/projects/{ref}/config/auth/third-party-auth

Requires a Personal Access Token (PAT) from:
  https://supabase.com/dashboard/account/tokens

Env / apps/web/.env.local:
  SUPABASE_ACCESS_TOKEN  — sbp_... (required)
  NEXT_PUBLIC_SUPABASE_URL — to derive project ref, or set SUPABASE_PROJECT_REF
  NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY — to derive Clerk issuer, or set CLERK_ISSUER_URL
"""
from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


def load_dotenv_local(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def clerk_issuer_from_publishable(pk: str) -> str:
    import base64

    parts = pk.split("_", 2)
    if len(parts) < 3:
        raise ValueError("Invalid NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY format")
    raw = parts[2]
    pad = len(raw) % 4
    if pad:
        raw += "=" * (4 - pad)
    decoded = base64.urlsafe_b64decode(raw).decode("utf-8")
    host = decoded.rstrip("$").split("$")[0].strip()
    if not host:
        raise ValueError("Could not decode Clerk host from publishable key")
    if host.startswith("http://") or host.startswith("https://"):
        return host.rstrip("/")
    return f"https://{host}".rstrip("/")


def project_ref_from_supabase_url(url: str) -> str:
    host = (urlparse(url).hostname or "").strip().lower()
    if not host.endswith(".supabase.co"):
        raise ValueError("NEXT_PUBLIC_SUPABASE_URL must be *.supabase.co")
    return host.split(".")[0]


def api_request(
    method: str,
    url: str,
    token: str,
    data: bytes | None = None,
) -> tuple[int, bytes]:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    env_file = root / "apps/web/.env.local"
    file_env = load_dotenv_local(env_file)

    token = os.environ.get("SUPABASE_ACCESS_TOKEN") or file_env.get("SUPABASE_ACCESS_TOKEN")
    if not token:
        print(
            "Missing SUPABASE_ACCESS_TOKEN.\n"
            "Create a PAT: https://supabase.com/dashboard/account/tokens\n"
            "Then export it or add SUPABASE_ACCESS_TOKEN=... to apps/web/.env.local",
            file=sys.stderr,
        )
        return 1

    ref = (
        os.environ.get("SUPABASE_PROJECT_REF")
        or file_env.get("SUPABASE_PROJECT_REF")
        or ""
    )
    supabase_url = file_env.get("NEXT_PUBLIC_SUPABASE_URL", "")
    if not ref:
        if not supabase_url:
            print("Set NEXT_PUBLIC_SUPABASE_URL or SUPABASE_PROJECT_REF.", file=sys.stderr)
            return 1
        ref = project_ref_from_supabase_url(supabase_url)

    issuer = (
        os.environ.get("CLERK_ISSUER_URL")
        or file_env.get("CLERK_ISSUER_URL")
        or file_env.get("CLERK_FRONTEND_API_URL")
        or ""
    )
    pk = file_env.get("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "")
    if not issuer:
        if not pk:
            print(
                "Set CLERK_ISSUER_URL (https://YOUR-INSTANCE.clerk.accounts.dev) "
                "or NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY.",
                file=sys.stderr,
            )
            return 1
        issuer = clerk_issuer_from_publishable(pk)

    issuer = issuer.rstrip("/")
    jwks_url = f"{issuer}/.well-known/jwks.json"

    base = f"https://api.supabase.com/v1/projects/{ref}/config/auth/third-party-auth"
    status, body = api_request("GET", base, token)
    if status != 200:
        print(f"GET third-party-auth failed: HTTP {status}", file=sys.stderr)
        print(body.decode("utf-8", errors="replace")[:2000], file=sys.stderr)
        return 1

    existing = json.loads(body.decode("utf-8"))
    for item in existing:
        o = (item.get("oidc_issuer_url") or "").rstrip("/")
        if o == issuer:
            print(f"Third-party auth already registered for issuer {issuer!r}. Nothing to do.")
            return 0

    payload = json.dumps(
        {"oidc_issuer_url": issuer, "jwks_url": jwks_url},
    ).encode("utf-8")
    status, body = api_request("POST", base, token, data=payload)
    if status in (200, 201):
        print(json.dumps(json.loads(body.decode("utf-8")), indent=2))
        print("Registered Clerk third-party auth with Supabase.")
        return 0
    print(f"POST failed: HTTP {status}", file=sys.stderr)
    print(body.decode("utf-8", errors="replace")[:4000], file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
