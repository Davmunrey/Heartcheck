"""Verify Clerk session JWTs via JWKS (RS256)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx
from jose import jwk, jwt
from jose.exceptions import JWTError as JoseJWTError

from app.core.config import Settings


@dataclass(frozen=True)
class ClerkClaims:
    user_id: str
    org_id: str | None
    org_role: str | None


_jwks_cache: dict[str, Any] = {"keys": None, "fetched_at": 0.0}
_JWKS_TTL_SEC = 3600


def _get_jwks(jwks_url: str) -> dict[str, Any]:
    now = time.time()
    if _jwks_cache["keys"] is not None and now - float(_jwks_cache["fetched_at"]) < _JWKS_TTL_SEC:
        return _jwks_cache["keys"]
    r = httpx.get(jwks_url, timeout=15.0)
    r.raise_for_status()
    data = r.json()
    _jwks_cache["keys"] = data
    _jwks_cache["fetched_at"] = now
    return data


def verify_clerk_bearer(token: str, settings: Settings) -> ClerkClaims:
    """Validate Authorization Bearer token issued by Clerk."""
    if not settings.clerk_jwks_url:
        raise ValueError("Clerk JWKS URL not configured")
    jwks = _get_jwks(settings.clerk_jwks_url)
    try:
        headers = jwt.get_unverified_header(token)
    except JoseJWTError as e:
        raise ValueError("invalid token header") from e
    kid = headers.get("kid")
    if not kid:
        raise ValueError("missing kid")
    key_dict = None
    for k in jwks.get("keys", []):
        if k.get("kid") == kid:
            key_dict = k
            break
    if key_dict is None:
        raise ValueError("unknown signing key")
    public_key = jwk.construct(key_dict)
    decode_kw: dict[str, Any] = {
        "algorithms": ["RS256"],
        "options": {"verify_aud": False},
    }
    if settings.clerk_issuer:
        decode_kw["issuer"] = settings.clerk_issuer
    try:
        payload = jwt.decode(token, public_key, **decode_kw)
    except JoseJWTError as e:
        raise ValueError("invalid token") from e
    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise ValueError("missing sub")
    org_id = payload.get("org_id")
    if org_id is not None and not isinstance(org_id, str):
        org_id = str(org_id)
    org_role = payload.get("org_role")
    if org_role is not None and not isinstance(org_role, str):
        org_role = str(org_role)
    return ClerkClaims(user_id=sub, org_id=org_id, org_role=org_role)
