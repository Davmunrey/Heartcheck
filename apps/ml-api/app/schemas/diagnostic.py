"""Response schema for the 12-lead diagnostic (signal) wedge."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DiagnosticFinding(BaseModel):
    code: str = Field(description="PTB-XL superclass code (NORM, MI, STTC, CD, HYP).")
    label: str = Field(description="Human-readable, non-diagnostic label.")
    probability: float = Field(ge=0.0, le=1.0)
    positive: bool = Field(description="probability >= calibrated per-class threshold.")
    threshold: float = Field(ge=0.0, le=1.0)


class DiagnosticResponse(BaseModel):
    abnormal: bool = Field(description="Any non-NORM superclass flagged positive.")
    findings: list[DiagnosticFinding]
    n_leads: int
    sampling_rate_hz: int
    model_version: str
    pipeline_version: str
    request_id: str
    disclaimer: str
    analysis_limit: list[str] = Field(default_factory=list)
