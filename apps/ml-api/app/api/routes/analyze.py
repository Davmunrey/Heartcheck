import time
from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import AnalyzeAuth, get_db, require_analyze_auth
from app.core.config import Settings, get_settings
from app.core.limiter import limiter
from app.core.metrics import (
    ANALYZE_CLASS_TOTAL,
    ANALYZE_CONFIDENCE,
    ANALYZE_GRID_CALIBRATED,
    ANALYZE_NON_REPORTABLE,
    ANALYZE_PREDICTION_SET_SIZE,
    ANALYZE_QUALITY,
    ANALYZE_STATUS_TOTAL,
    ANALYZE_TOTAL,
    REQUEST_LATENCY,
)
from app.schemas.analysis import AnalysisResponse
from app.services.analysis_pipeline import run_analysis
from app.services.usage_service import get_today_count, increment_today

router = APIRouter(prefix="/api/v1", tags=["analyze"])

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"
_WEBP_RIFF = b"RIFF"
_WEBP_FORMAT = b"WEBP"


def _looks_like_supported_image(raw: bytes) -> bool:
    """Validate magic bytes; never trust the client-provided Content-Type."""
    if len(raw) < 12:
        return False
    if raw.startswith(_PNG_MAGIC):
        return True
    if raw.startswith(_JPEG_MAGIC):
        return True
    if raw[:4] == _WEBP_RIFF and raw[8:12] == _WEBP_FORMAT:
        return True
    return False


@router.post("/analyze", response_model=AnalysisResponse)
@limiter.limit("120/minute")
async def analyze(
    request: Request,
    auth: Annotated[AnalyzeAuth, Depends(require_analyze_auth)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    file: UploadFile = File(...),
    accept_language: Annotated[str | None, Header()] = None,
) -> AnalysisResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        ANALYZE_TOTAL.labels(status="bad_request").inc()
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_CONTENT_TYPE",
                "message": "Expected an image/* content type",
                "request_id": getattr(request.state, "request_id", ""),
            },
        )

    raw = await file.read()
    if len(raw) > settings.max_upload_bytes:
        ANALYZE_TOTAL.labels(status="too_large").inc()
        raise HTTPException(
            status_code=413,
            detail={
                "error_code": "PAYLOAD_TOO_LARGE",
                "message": "Image exceeds configured limit",
                "request_id": getattr(request.state, "request_id", ""),
            },
        )

    if not _looks_like_supported_image(raw):
        ANALYZE_TOTAL.labels(status="bad_request").inc()
        raise HTTPException(
            status_code=415,
            detail={
                "error_code": "UNSUPPORTED_MEDIA_TYPE",
                "message": "Only PNG, JPEG and WebP images are supported.",
                "request_id": getattr(request.state, "request_id", ""),
            },
        )

    if auth.company_id is not None:
        used = get_today_count(db, auth.company_id)
        if used >= settings.beta_daily_analysis_quota:
            raise HTTPException(
                status_code=429,
                detail={
                    "error_code": "QUOTA_EXCEEDED",
                    "message": "Daily analysis quota exceeded for your account",
                    "request_id": getattr(request.state, "request_id", ""),
                },
            )

    rid = getattr(request.state, "request_id", "")
    t0 = time.perf_counter()
    try:
        result = run_analysis(
            raw,
            settings,
            request_id=rid,
            accept_language=accept_language or "en",
        )
        if auth.company_id is not None:
            increment_today(db, auth.company_id)
        ANALYZE_TOTAL.labels(status="ok").inc()
        ANALYZE_STATUS_TOTAL.labels(status=result.status).inc()
        ANALYZE_CLASS_TOTAL.labels(class_label=result.class_label).inc()
        ANALYZE_CONFIDENCE.observe(result.confidence_score)
        ANALYZE_QUALITY.observe(result.extraction_quality)
        ANALYZE_PREDICTION_SET_SIZE.observe(len(result.prediction_set or [result.class_label]))
        if result.measurement_basis:
            ANALYZE_GRID_CALIBRATED.labels(basis=result.measurement_basis).inc()
        for reason in (result.quality_reasons or []):
            ANALYZE_NON_REPORTABLE.labels(reason=reason).inc()
        return result
    finally:
        REQUEST_LATENCY.observe(time.perf_counter() - t0)
