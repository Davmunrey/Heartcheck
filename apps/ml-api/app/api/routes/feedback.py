"""User feedback queue (no raw images stored)."""

from __future__ import annotations

import json
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.limiter import limiter
from app.core.clerk import verify_clerk_bearer
from app.core.config import get_settings
from app.core.security import decode_token
from app.db.models import Feedback
from app.schemas.analysis import AnalysisResponse
from app.services.usage_service import get_user_by_id

router = APIRouter(prefix="/api/v1", tags=["feedback"])


class FeedbackRequest(BaseModel):
    analysis: AnalysisResponse
    suggested_class: Literal["normal", "arrhythmia", "noise"] | None = None
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    id: int
    received: bool = True


def _maybe_actor(request: Request) -> tuple[str | None, str | None, int | None]:
    """Returns (company_id, clerk_user_id, legacy_user_id_int)."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None, None, None
    token = auth[7:].strip()
    settings = get_settings()
    if settings.clerk_jwks_url:
        try:
            claims = verify_clerk_bearer(token, settings)
        except ValueError:
            return None, None, None
        return claims.org_id, claims.user_id, None
    try:
        payload = decode_token(token)
    except ValueError:
        return None, None, None
    uid = payload.get("uid")
    if uid is None:
        return None, None, None
    return f"legacy:{uid}", None, int(uid)


@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def submit_feedback(
    request: Request,
    body: FeedbackRequest,
    db: Annotated[Session, Depends(get_db)],
) -> FeedbackResponse:
    if not body.analysis.request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "MISSING_REQUEST_ID", "message": "analysis.request_id is required"},
        )

    company_id, clerk_uid, legacy_uid = _maybe_actor(request)
    legacy_user = get_user_by_id(db, legacy_uid) if legacy_uid is not None else None

    record = Feedback(
        company_id=company_id,
        clerk_user_id=clerk_uid,
        user_id=legacy_user.id if legacy_user else None,
        request_id=body.analysis.request_id,
        pipeline_version=body.analysis.pipeline_version,
        model_version=body.analysis.model_version,
        reported_class=body.analysis.class_label,
        suggested_class=body.suggested_class,
        comment=body.comment,
        analysis_json=json.dumps(body.analysis.model_dump(), ensure_ascii=False),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return FeedbackResponse(id=record.id)
