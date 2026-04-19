from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.clerk import verify_clerk_bearer
from app.core.config import Settings, get_settings
from app.core.security import decode_token
from app.db.models import User
from app.db.session import get_session_factory
from app.services.usage_service import get_user_by_id


def _api_key_matches(provided: str | None, configured: str) -> bool:
    if not provided or not configured:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), configured.encode("utf-8"))


def get_db() -> Session:
    sf = get_session_factory()
    db = sf()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "MISSING_BEARER", "message": "Authorization Bearer token required"},
        )
    token = authorization[7:].strip()
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_TOKEN", "message": "Invalid or expired token"},
        ) from None
    uid = payload.get("uid")
    if uid is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_TOKEN", "message": "Invalid token payload"},
        )
    user = get_user_by_id(db, int(uid))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "USER_NOT_FOUND", "message": "User no longer exists"},
        )
    return user


class AnalyzeAuth:
    __slots__ = ("company_id", "clerk_user_id", "legacy_api_key", "legacy_user_id")

    def __init__(
        self,
        *,
        company_id: str | None,
        clerk_user_id: str | None = None,
        legacy_api_key: bool = False,
        legacy_user_id: int | None = None,
    ) -> None:
        self.company_id = company_id
        self.clerk_user_id = clerk_user_id
        self.legacy_api_key = legacy_api_key
        self.legacy_user_id = legacy_user_id


def _internal_token_ok(settings: Settings, x_internal_token: str | None) -> bool:
    if not settings.ml_internal_token:
        return True
    if not x_internal_token:
        return False
    return hmac.compare_digest(
        x_internal_token.encode("utf-8"),
        settings.ml_internal_token.encode("utf-8"),
    )


async def require_analyze_auth(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header()] = None,
    x_internal_token: Annotated[str | None, Header()] = None,
    x_organization_id: Annotated[str | None, Header()] = None,
) -> AnalyzeAuth:
    rid = getattr(request.state, "request_id", "")

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        if settings.clerk_jwks_url:
            try:
                claims = verify_clerk_bearer(token, settings)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error_code": "INVALID_TOKEN",
                        "message": "Invalid Clerk token",
                        "request_id": rid,
                    },
                ) from None
            org = claims.org_id
            if not org and x_organization_id and x_organization_id.strip():
                if not _internal_token_ok(settings, x_internal_token):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail={
                            "error_code": "INVALID_INTERNAL_TOKEN",
                            "message": "X-Internal-Token required for X-Organization-Id",
                            "request_id": rid,
                        },
                    )
                org = x_organization_id.strip()
            if not org:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error_code": "ORG_REQUIRED",
                        "message": "Active Clerk Organization required (JWT org_id or X-Organization-Id)",
                        "request_id": rid,
                    },
                )
            if settings.ml_internal_token and not _internal_token_ok(settings, x_internal_token):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error_code": "INVALID_INTERNAL_TOKEN",
                        "message": "X-Internal-Token required or invalid",
                        "request_id": rid,
                    },
                )
            return AnalyzeAuth(
                company_id=org,
                clerk_user_id=claims.user_id,
                legacy_api_key=False,
                legacy_user_id=None,
            )
        try:
            payload = decode_token(token)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error_code": "INVALID_TOKEN",
                    "message": "Invalid or expired token",
                    "request_id": rid,
                },
            ) from None
        uid = payload.get("uid")
        if uid is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error_code": "INVALID_TOKEN", "message": "Invalid token", "request_id": rid},
            )
        user = get_user_by_id(db, int(uid))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error_code": "USER_NOT_FOUND", "message": "User not found", "request_id": rid},
            )
        return AnalyzeAuth(
            company_id=f"legacy:{user.id}",
            clerk_user_id=None,
            legacy_api_key=False,
            legacy_user_id=user.id,
        )

    if settings.allow_legacy_api_key and _api_key_matches(x_api_key, settings.api_key):
        return AnalyzeAuth(
            company_id="api-key",
            legacy_api_key=True,
            legacy_user_id=None,
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error_code": "AUTH_REQUIRED",
            "message": "Bearer token or valid X-API-Key (if legacy enabled) required",
            "request_id": rid,
        },
    )


async def require_api_key(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    """Legacy: shared API key only (reports PDF). Prefer Bearer for new integrations."""
    if not _api_key_matches(x_api_key, settings.api_key):
        rid = getattr(request.state, "request_id", "")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_API_KEY",
                "message": "Invalid or missing X-API-Key",
                "request_id": rid,
            },
        )
