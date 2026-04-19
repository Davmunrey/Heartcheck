"""R-R interval analysis from 1D sampled trace."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import find_peaks, medfilt


@dataclass
class RRResult:
    mean_rr_samples: float | None
    rr_cv: float | None
    bpm: float | None
    regularity: str  # regular | irregular | unknown
    peak_count: int
    measurement_basis: str | None  # None if bpm not computed


def analyze_rr(
    y_signal: np.ndarray,
    image_width_px: int,
    assumed_strip_duration_sec: float,
    min_distance: int = 10,
) -> RRResult:
    """
    Detect approximate R peaks; compute BPM only when temporal basis is documented:
    we assume ``image_width_px`` spans ``assumed_strip_duration_sec`` seconds uniformly.
    """
    y = np.asarray(y_signal, dtype=np.float64)
    valid = np.isfinite(y)
    if not np.any(valid):
        return RRResult(None, None, None, "unknown", 0, None)

    y = np.where(valid, y, np.nanmedian(y))
    y = y - np.nanmean(y)
    if len(y) < min_distance * 3 or image_width_px <= 0:
        return RRResult(None, None, None, "unknown", 0, None)

    k = min(5, len(y) // 2 * 2 + 1)
    smooth = medfilt(np.nan_to_num(y), kernel_size=k)
    peaks, _ = find_peaks(
        -smooth,
        distance=min_distance,
        prominence=max(np.std(smooth) * 0.3, 1e-6),
    )

    if len(peaks) < 2:
        return RRResult(None, None, None, "unknown", len(peaks), None)

    rr = np.diff(peaks.astype(np.float64))
    mean_rr = float(np.mean(rr))
    cv = float(np.std(rr) / mean_rr) if mean_rr > 0 else None

    regularity = "unknown"
    if cv is not None:
        regularity = "regular" if cv < 0.2 else "irregular"

    sec_per_px = assumed_strip_duration_sec / float(image_width_px)
    mean_rr_sec = mean_rr * sec_per_px
    bpm: float | None = None
    basis: str | None = None
    if mean_rr_sec > 0:
        bpm = 60.0 / mean_rr_sec
        basis = "ASSUMED_UNIFORM_TIME_AXIS"

    return RRResult(
        mean_rr_samples=mean_rr,
        rr_cv=cv,
        bpm=bpm,
        regularity=regularity,
        peak_count=len(peaks),
        measurement_basis=basis,
    )
