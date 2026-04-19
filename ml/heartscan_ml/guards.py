"""Abstention rules: avoid absurd BPM / low confidence / bad extraction (product API)."""

from __future__ import annotations

from dataclasses import dataclass

from heartscan_ml.config import GuardConfig, default_guard_config


@dataclass
class GuardResult:
    reportable: bool
    non_reportable_reason: str | None
    bpm: float | None
    confidence_score: float
    adjusted_status: str | None


def apply_guards(
    raw_bpm: float | None,
    model_confidence: float,
    extraction_quality: int,
    predicted_class: str,
    cfg: GuardConfig | None = None,
) -> GuardResult:
    cfg = cfg or default_guard_config()
    reason: str | None = None
    reportable = True

    if extraction_quality < cfg.min_extraction_quality:
        reportable = False
        reason = "LOW_EXTRACTION_QUALITY"

    if model_confidence < cfg.min_confidence:
        reportable = False
        reason = reason or "LOW_MODEL_CONFIDENCE"

    if raw_bpm is not None:
        if raw_bpm > cfg.max_bpm_human_plausible or raw_bpm < cfg.min_bpm_human_plausible:
            reportable = False
            reason = reason or "IMPLAUSIBLE_BPM"

    status = None
    if not reportable:
        status = "unknown"

    return GuardResult(
        reportable=reportable,
        non_reportable_reason=reason,
        bpm=raw_bpm if reportable else None,
        confidence_score=model_confidence,
        adjusted_status=status,
    )
