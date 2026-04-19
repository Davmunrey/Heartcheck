from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.services import inference as inf

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(settings: Settings = Depends(get_settings)) -> dict[str, str | bool]:
    return {
        "status": "ready",
        "pipeline_version": settings.pipeline_version,
        "model_loaded": inf.get_model() is not None,
        "model_version": inf.get_model_version(),
    }
