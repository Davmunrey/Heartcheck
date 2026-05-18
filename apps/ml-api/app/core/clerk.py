"""Verify Clerk session JWTs via JWKS (RS256)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

from app.core.config import Settings


@dataclass(frozen=True)
class ClerkClaims:
    user_id: str
    org_id: str | None
    org_role: str | None


_jwk_client_cache: dict[str, Any] = {"client": None, "url": None, "fetched_at": 0.0}
_JWKS_TTL_SEC = 3600


def _get_jwk_client(jwks_url: str) -> PyJWKClient:
    """Return a cached PyJWKClient for the given JWKS URL."""
    now = time.time()
    if (
        _jwk_client_cache["client"] is not None
        and _jwk_client_cache["url"] == jwks_url
        and now - float(_jwk_client_cache["fetched_at"]) < _JWKS_TTL_SEC
    ):
        return _jwk_client_cache["client"]
    client = PyJWKClient(jwks_url, cache_keys=True, lifespan=_JWKS_TTL_SEC)
    _jwk_client_cache["client"] = client
    _jwk_client_cache["url"] = jwks_url
    _jwk_client_cache["fetched_at"] = now
    return client


def verify_clerk_bearer(token: str, settings: Settings) -> ClerkClaims:
    """Validate Authorization Bearer token issued by Clerk."""
    if not settings.clerk_jwks_url:
        raise ValueError("Clerk JWKS URL not configured")
    client = _get_jwk_client(settings.clerk_jwks_url)
    try:
        signing_key = client.get_signing_key_from_jwt(token)
    except PyJWTError as e:
        raise ValueError("invalid token header") from e
    except Exception as e:  # JWKS fetch / network errors
        raise ValueError("unable to resolve signing key") from e

    decode_kw: dict[str, Any] = {
        "algorithms": ["RS256"],
        "options": {"verify_aud": True, "require": ["exp", "sub"]},
    }
    if settings.clerk_issuer:
        decode_kw["issuer"] = settings.clerk_issuer
    if settings.clerk_audience:
        decode_kw["audience"] = settings.clerk_audience
    else:
        # No audience configured: cannot verify `aud`. Disable the aud check
        # explicitly instead of silently trusting any audience.
        decode_kw["options"]["verify_aud"] = False
    try:
        payload = jwt.decode(token, signing_key.key, **decode_kw)
    except PyJWTError as e:
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
