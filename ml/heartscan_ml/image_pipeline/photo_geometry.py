"""Photo geometry helpers: perspective rectification, grid pitch estimation,
multi-lead splitting and per-photo quality signals.

Every helper returns *deterministic* values and degrades gracefully:

- if perspective rectification fails (no rectangle found, OpenCV unhappy) the
  original image is returned and ``rectified=False`` is reported;
- if grid pitch is undetectable the result is ``None``; downstream stages must
  treat ``None`` as "no calibration available" and keep the previous behaviour.

These primitives are pure NumPy/OpenCV; no torch, no sklearn.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Rectification:
    image: np.ndarray
    rectified: bool
    tilt_deg: float | None  # estimated tilt of the detected paper


@dataclass
class GridCalibration:
    pitch_x_px: float | None  # pixels per fine 1 mm square (≈ 1 mm)
    pitch_y_px: float | None
    confidence: float  # in [0, 1]; 0 = no peak found


@dataclass
class PhotoQuality:
    blur: float  # variance of Laplacian normalised to [0, 1]; high = sharper
    glare: float  # fraction of saturated pixels in [0, 1]
    tilt_deg: float | None  # absolute tilt of the dominant paper edge
    contrast: float  # std/255 of the grayscale, in [0, 1]


# ---------------------------------------------------------------------------
# Perspective / paper detection
# ---------------------------------------------------------------------------


def _order_quad(pts: np.ndarray) -> np.ndarray:
    """Return points ordered as TL, TR, BR, BL."""
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).ravel()
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def detect_paper_quad(gray: np.ndarray) -> np.ndarray | None:
    """Return the 4 corners of the largest plausible paper quadrilateral, else None."""
    try:
        import cv2
    except ImportError:
        return None

    h, w = gray.shape
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 30, 100)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    img_area = float(h * w)
    for c in contours[:5]:
        area = cv2.contourArea(c)
        if area < img_area * 0.2:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            return _order_quad(approx.reshape(4, 2).astype(np.float32))
    return None


def correct_perspective(gray: np.ndarray) -> Rectification:
    """Rectify the largest paper-like quadrilateral. Falls back to the input
    image when no quad is found or OpenCV is missing."""
    try:
        import cv2
    except ImportError:
        return Rectification(image=gray, rectified=False, tilt_deg=None)

    quad = detect_paper_quad(gray)
    if quad is None:
        return Rectification(image=gray, rectified=False, tilt_deg=None)

    tl, tr, br, bl = quad
    width = int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
    height = int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr)))
    if width < 50 or height < 30:
        return Rectification(image=gray, rectified=False, tilt_deg=None)

    dst = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype=np.float32)
    m = cv2.getPerspectiveTransform(quad, dst)
    rect = cv2.warpPerspective(gray, m, (width, height))
    dx = float(tr[0] - tl[0])
    dy = float(tr[1] - tl[1])
    tilt = float(np.degrees(np.arctan2(dy, max(1e-6, dx))))
    return Rectification(image=rect, rectified=True, tilt_deg=tilt)


# ---------------------------------------------------------------------------
# Grid pitch estimation via 1D FFT on row/column projections
# ---------------------------------------------------------------------------


def _dominant_period_px(signal: np.ndarray, min_period: int = 4, max_period: int = 80) -> tuple[float | None, float]:
    """Return (period_px, confidence) by looking at the dominant FFT peak."""
    s = np.asarray(signal, dtype=np.float64)
    s = s - s.mean()
    if len(s) < max_period * 2:
        return None, 0.0
    spectrum = np.abs(np.fft.rfft(s * np.hanning(len(s))))
    freqs = np.fft.rfftfreq(len(s), d=1.0)
    valid = (freqs >= 1.0 / max_period) & (freqs <= 1.0 / max(1, min_period))
    if not np.any(valid):
        return None, 0.0
    sub = spectrum[valid]
    sub_freqs = freqs[valid]
    peak_idx = int(np.argmax(sub))
    peak_val = float(sub[peak_idx])
    background = float(np.median(sub) + 1e-9)
    confidence = max(0.0, min(1.0, (peak_val - background) / (peak_val + background)))
    if confidence < 0.05:
        return None, confidence
    period = 1.0 / sub_freqs[peak_idx]
    return float(period), confidence


def estimate_grid_pitch(gray: np.ndarray) -> GridCalibration:
    """Estimate fine-grid pitch (≈1 mm) along x and y from luminance projections."""
    g = np.asarray(gray, dtype=np.float64)
    if g.ndim != 2 or g.size == 0:
        return GridCalibration(None, None, 0.0)
    col_proj = g.mean(axis=0)
    row_proj = g.mean(axis=1)
    px, cx = _dominant_period_px(col_proj)
    py, cy = _dominant_period_px(row_proj)
    confidence = float(min(cx, cy)) if (px is not None and py is not None) else 0.0
    return GridCalibration(pitch_x_px=px, pitch_y_px=py, confidence=confidence)


def bpm_from_calibration(
    rr_samples: float | None,
    image_width_px: int,
    grid: GridCalibration,
    paper_speed_mm_per_s: float = 25.0,
) -> tuple[float | None, str | None]:
    """Convert a mean R-R distance in pixels into BPM using the detected grid.

    Returns ``(bpm, basis)`` with basis ``GRID_CALIBRATED`` when a confident
    pitch was found, ``None`` otherwise.
    """
    if rr_samples is None or rr_samples <= 0 or grid.pitch_x_px is None or grid.confidence < 0.15:
        return None, None
    # 1 fine square ~ 1 mm; paper at 25 mm/s -> 1 mm = 0.04 s.
    seconds_per_mm = 1.0 / paper_speed_mm_per_s
    rr_seconds = (rr_samples / grid.pitch_x_px) * seconds_per_mm
    if rr_seconds <= 0:
        return None, None
    return 60.0 / rr_seconds, "GRID_CALIBRATED"


# ---------------------------------------------------------------------------
# Multi-lead detection (rough): split horizontally on dark-row gaps
# ---------------------------------------------------------------------------


def detect_lead_strips(gray: np.ndarray, min_height: int = 40) -> list[tuple[int, int]]:
    """Return ``(y0, y1)`` ranges for plausible horizontal lead strips.

    Heuristic: row energy of the inverted image; large peaks separated by
    valleys delimit strips. Always returns at least one range covering the
    full image so callers can rely on a non-empty list.
    """
    h, w = gray.shape
    if h < min_height * 2:
        return [(0, h)]
    inv = 255 - gray.astype(np.float64)
    energy = inv.mean(axis=1)
    # smooth
    kernel = max(3, h // 50)
    if kernel % 2 == 0:
        kernel += 1
    pad = kernel // 2
    padded = np.pad(energy, pad, mode="edge")
    smooth = np.convolve(padded, np.ones(kernel) / kernel, mode="valid")
    threshold = smooth.mean() + 0.25 * smooth.std()
    above = smooth > threshold

    strips: list[tuple[int, int]] = []
    in_run = False
    start = 0
    for i, flag in enumerate(above):
        if flag and not in_run:
            in_run = True
            start = i
        elif not flag and in_run:
            in_run = False
            if i - start >= min_height:
                strips.append((start, i))
    if in_run and h - start >= min_height:
        strips.append((start, h))
    if not strips:
        return [(0, h)]
    return strips


def dominant_strip(gray: np.ndarray) -> tuple[np.ndarray, int]:
    """Return ``(image_of_dominant_strip, lead_count_detected)``."""
    strips = detect_lead_strips(gray)
    if len(strips) <= 1:
        return gray, 1
    # dominant = tallest
    y0, y1 = max(strips, key=lambda s: s[1] - s[0])
    return gray[y0:y1, :], len(strips)


# ---------------------------------------------------------------------------
# Quality signals
# ---------------------------------------------------------------------------


def _laplacian_variance(gray: np.ndarray) -> float:
    try:
        import cv2

        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    except ImportError:
        # naive 3x3 Laplacian
        kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)
        h, w = gray.shape
        if h < 3 or w < 3:
            return 0.0
        out = np.zeros_like(gray, dtype=np.float64)
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                window = gray[y - 1 : y + 2, x - 1 : x + 2].astype(np.float64)
                out[y, x] = float((window * kernel).sum())
        return float(out.var())


def photo_quality_signals(gray: np.ndarray, tilt_deg: float | None = None) -> PhotoQuality:
    if gray.size == 0:
        return PhotoQuality(blur=0.0, glare=0.0, tilt_deg=tilt_deg, contrast=0.0)
    lap_var = _laplacian_variance(gray)
    # Normalise: lap_var > 200 is a typical "sharp" threshold; clip to [0, 1].
    blur = float(min(1.0, lap_var / 400.0))
    glare = float((gray > 245).mean())
    contrast = float(np.std(gray) / 255.0)
    return PhotoQuality(blur=blur, glare=glare, tilt_deg=tilt_deg, contrast=contrast)
