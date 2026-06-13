"""Unit tests for the org-optional tenancy branch in require_analyze_auth.

Mocks verify_clerk_bearer so no JWKS network/keys are needed.
"""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.deps import AnalyzeAuth, require_analyze_auth
from app.core.clerk import ClerkClaims
from app.core.config import Settings

_JWKS = "https://example.clerk.accounts.dev/.well-known/jwks.json"


def _request() -> SimpleNamespace:
    return SimpleNamespace(state=SimpleNamespace(request_id="rid-test"))


def _patch_clerk(monkeypatch, *, org_id: str | None) -> None:
    monkeypatch.setattr(
        "app.api.deps.verify_clerk_bearer",
        lambda token, settings: ClerkClaims(user_id="user_x", org_id=org_id, org_role=None),
    )


def test_org_optional_derives_user_tenant(monkeypatch) -> None:
    _patch_clerk(monkeypatch, org_id=None)
    settings = Settings(clerk_jwks_url=_JWKS, ml_internal_token="tok", require_organization=False)
    auth = asyncio.run(
        require_analyze_auth(
            _request(), settings, None, authorization="Bearer x", x_internal_token="tok"
        )
    )
    assert isinstance(auth, AnalyzeAuth)
    assert auth.company_id == "clerk-user:user_x"
    assert auth.clerk_user_id == "user_x"


def test_org_required_rejects_when_no_org(monkeypatch) -> None:
    _patch_clerk(monkeypatch, org_id=None)
    settings = Settings(clerk_jwks_url=_JWKS, ml_internal_token="tok", require_organization=True)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            require_analyze_auth(
                _request(), settings, None, authorization="Bearer x", x_internal_token="tok"
            )
        )
    assert exc.value.status_code == 403
    assert exc.value.detail["error_code"] == "ORG_REQUIRED"


def test_org_from_trusted_header(monkeypatch) -> None:
    _patch_clerk(monkeypatch, org_id=None)
    settings = Settings(clerk_jwks_url=_JWKS, ml_internal_token="tok", require_organization=True)
    auth = asyncio.run(
        require_analyze_auth(
            _request(),
            settings,
            None,
            authorization="Bearer x",
            x_internal_token="tok",
            x_organization_id="org_42",
        )
    )
    assert auth.company_id == "org_42"


def test_jwt_alone_is_sufficient_without_internal_token(monkeypatch) -> None:
    # A valid Clerk JWT (no internal token, no org header) is enough — enables
    # direct browser upload. Tenant comes from the verified user id.
    _patch_clerk(monkeypatch, org_id=None)
    settings = Settings(clerk_jwks_url=_JWKS, ml_internal_token="tok", require_organization=False)
    auth = asyncio.run(
        require_analyze_auth(_request(), settings, None, authorization="Bearer x")
    )
    assert auth.company_id == "clerk-user:user_x"


def test_org_header_rejected_without_valid_internal_token(monkeypatch) -> None:
    # The out-of-band X-Organization-Id header is still only trusted with a
    # matching internal token (defense for the server-to-server path).
    _patch_clerk(monkeypatch, org_id=None)
    settings = Settings(clerk_jwks_url=_JWKS, ml_internal_token="tok", require_organization=True)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            require_analyze_auth(
                _request(),
                settings,
                None,
                authorization="Bearer x",
                x_internal_token="WRONG",
                x_organization_id="org_42",
            )
        )
    assert exc.value.status_code == 401
