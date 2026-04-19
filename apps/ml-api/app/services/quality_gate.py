"""Compute extraction quality + image-quality reasons.

Two functions are exposed:

- :func:`extraction_quality_score` — legacy 1D-signal quality (kept for
  backward compatibility).
- :func:`quality_gate_v2` — combines signal quality with photo-quality signals
  (blur, glare, contrast, tilt, grid confidence) and returns a structured
  result with a reason code that callers can localise.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.services.photo_geometry import GridCalibration, PhotoQuality

# Reason codes are stable ids shipped to clients (i18n at the edge).
REASON_BLUR = "PHOTO_BLURRY"
REASON_GLARE = "PHOTO_GLARE"
REASON_TILT = "PHOTO_TILT"
REASON_LOW_CONTRAST = "PHOTO_LOW_CONTRAST"
REASON_NO_GRID = "PHOTO_NO_GRID_DETECTED"
REASON_NO_SIGNAL = "SIGNAL_EXTRACTION_POOR"


@dataclass
class GateResult:
    score: float  # in [0, 1]
    reasons: dict[str, str]  # reason_code -> human-readable English
    reportable: bool  # False -> caller should abstain or downgrade


def extraction_quality_score(
    y_signal: np.ndarray,
    peak_count: int,
    min_peaks_expected: int = 2,
) -> float:
    """Higher when more columns have valid trace and enough peaks for rhythm analysis."""
    y = np.asarray(y_signal, dtype=np.float64)
    finite = np.isfinite(y)
    cov = float(np.mean(finite)) if y.size else 0.0
    var = float(np.nanvar(y)) if np.any(finite) else 0.0
    var_score = min(1.0, var / (var + 1.0))
    peak_score = min(1.0, peak_count / max(min_peaks_expected * 2, 1))
    q = 0.45 * cov + 0.35 * var_score + 0.20 * peak_score
    return float(max(0.0, min(1.0, q)))


def quality_gate_v2(
    signal_score: float,
    photo: PhotoQuality,
    grid: GridCalibration,
    *,
    blur_min: float = 0.20,
    glare_max: float = 0.10,
    contrast_min: float = 0.08,
    tilt_max_deg: float = 25.0,
    score_min: float = 0.30,
) -> GateResult:
    """Combine signal + photo + grid signals into a structured gate result."""
    reasons: dict[str, str] = {}
    if photo.blur < blur_min:
        reasons[REASON_BLUR] = "Photo appears too blurry for reliable extraction."
    if photo.glare > glare_max:
        reasons[REASON_GLARE] = "Strong glare detected; retake without reflections."
    if photo.contrast < contrast_min:
        reasons[REASON_LOW_CONTRAST] = "Image contrast is low; ensure even lighting."
    if photo.tilt_deg is not None and abs(photo.tilt_deg) > tilt_max_deg:
        reasons[REASON_TILT] = "Photo is heavily tilted; align the strip horizontally."
    if grid.pitch_x_px is None or grid.confidence < 0.10:
        reasons[REASON_NO_GRID] = "ECG grid not detected; BPM falls back to assumed paper speed."
    if signal_score < score_min:
        reasons[REASON_NO_SIGNAL] = "Could not extract a clean trace from the photo."

    # Aggregate score: harmonic-ish combination so a single bad axis pulls down.
    components = [
        signal_score,
        photo.blur,
        max(0.0, 1.0 - photo.glare * 4.0),
        photo.contrast * 5.0,
        max(0.0, 1.0 - (abs(photo.tilt_deg or 0.0) / 45.0)),
        grid.confidence if grid.pitch_x_px else 0.3,
    ]
    components = [max(0.0, min(1.0, c)) for c in components]
    score = float(np.clip(np.mean(components), 0.0, 1.0))

    # Reportable when no critical reasons (signal+blur+contrast) and score above floor.
    critical = {REASON_NO_SIGNAL, REASON_BLUR, REASON_LOW_CONTRAST}
    reportable = score >= score_min and not (set(reasons) & critical)
    return GateResult(score=score, reasons=reasons, reportable=reportable)
