"""Rule-based classification when no neural weights are available."""

from __future__ import annotations

from app.services.rr_intervals import RRResult


def heuristic_label(rr: RRResult, extraction_quality: float) -> tuple[str, float]:
    """
    Simple screening: noise if quality low; arrhythmia if high RR variability; else normal.
    """
    if extraction_quality < 0.22:
        return "noise", 0.85
    if rr.peak_count < 2:
        return "noise", 0.75
    if rr.rr_cv is not None and rr.rr_cv > 0.2:
        return "arrhythmia", 0.55
    if rr.regularity == "irregular":
        return "arrhythmia", 0.5
    return "normal", 0.55
