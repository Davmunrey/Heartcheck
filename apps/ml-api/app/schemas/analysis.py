from typing import Literal

from pydantic import BaseModel, Field


class AnalyzeErrorBody(BaseModel):
    error_code: str
    message: str
    request_id: str


class AnalysisResponse(BaseModel):
    status: Literal["green", "yellow", "red"]
    bpm: float | None = Field(description="Beats per minute when traceable; null if not.")
    message: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    rhythm_regularity: Literal["regular", "irregular", "unknown"]
    class_label: Literal["normal", "arrhythmia", "noise"]
    disclaimer: str
    pipeline_version: str
    model_version: str
    extraction_quality: float = Field(ge=0.0, le=1.0)
    request_id: str
    non_reportable_reason: dict[str, str] | None = None
    analysis_limit: list[str] | None = None
    supported_findings: list[str] | None = None
    measurement_basis: str | None = Field(
        default=None,
        description="When bpm is set, basis e.g. ASSUMED_UNIFORM_TIME_AXIS or GRID_CALIBRATED.",
    )
    education_topic_ids: list[str] = Field(default_factory=list)

    # ---- Plan v2 — precision-focused additions (all optional for backward compat) ----
    prediction_set: list[str] | None = Field(
        default=None,
        description="Conformal prediction set (covers true class with target probability).",
    )
    calibrated_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Calibrated probability of the predicted class (post temperature scaling).",
    )
    quality_reasons: list[str] | None = Field(
        default=None,
        description="Stable codes describing why a photo failed quality gate (e.g. PHOTO_BLURRY).",
    )
    lead_count_detected: int | None = Field(
        default=None,
        ge=1,
        description="Approximate count of horizontal lead strips detected in the photo.",
    )


class EducationTopic(BaseModel):
    id: str
    title: str
    summary: str


class ReportPdfRequest(BaseModel):
    """Payload for server-side PDF generation (no raw image)."""

    analysis: AnalysisResponse
    app_version: str = "0.1.0"
    locale: str = "es"
