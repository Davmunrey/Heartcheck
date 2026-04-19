"""Suppress grid/background noise; emphasize dark ECG trace.

Two implementations are exported:

- :func:`suppress_grid` (v1): Gaussian + adaptive threshold (legacy default).
- :func:`suppress_grid_v2`: FFT-domain notch around the dominant grid pitch
  followed by adaptive thresholding. Falls back to v1 when no grid pitch can
  be reliably estimated.

The active variant is selected via :data:`active_variant` so the harness can
A/B without code changes.
"""

from __future__ import annotations

from typing import Literal

import numpy as np

from app.services.photo_geometry import GridCalibration, estimate_grid_pitch

Variant = Literal["v1", "v2"]
_ACTIVE: Variant = "v2"


def set_variant(variant: Variant) -> None:
    """Override the active suppressor (eval/A-B testing)."""
    global _ACTIVE
    _ACTIVE = variant


def active_variant() -> Variant:
    return _ACTIVE


def suppress_grid(gray: np.ndarray, gaussian_ksize: int = 5) -> np.ndarray:
    """Top-level entry point used by the pipeline; dispatches to the active variant."""
    if _ACTIVE == "v2":
        return suppress_grid_v2(gray)
    return _suppress_grid_v1(gray, gaussian_ksize)


def _suppress_grid_v1(gray: np.ndarray, gaussian_ksize: int = 5) -> np.ndarray:
    """Legacy adaptive-threshold suppressor."""
    import cv2

    k = gaussian_ksize if gaussian_ksize % 2 == 1 else gaussian_ksize + 1
    blurred = cv2.GaussianBlur(gray, (k, k), 0)
    th = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11,
        2,
    )
    kernel = np.ones((2, 2), np.uint8)
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel, iterations=1)
    return th


def _notch_filter_2d(gray: np.ndarray, pitch_x: float, pitch_y: float, bandwidth: float = 0.25) -> np.ndarray:
    """Suppress periodic frequencies near (1/pitch_x, 1/pitch_y) via 2D FFT."""
    h, w = gray.shape
    f = np.fft.fft2(gray.astype(np.float64))
    fshift = np.fft.fftshift(f)
    cy, cx = h // 2, w // 2
    fx = np.fft.fftshift(np.fft.fftfreq(w))
    fy = np.fft.fftshift(np.fft.fftfreq(h))
    fxg, fyg = np.meshgrid(fx, fy)
    mask = np.ones_like(fshift, dtype=np.float64)
    targets_x = [1.0 / pitch_x, 1.0 / (pitch_x * 5)] if pitch_x > 0 else []
    targets_y = [1.0 / pitch_y, 1.0 / (pitch_y * 5)] if pitch_y > 0 else []
    for tx in targets_x:
        mask *= 1 - np.exp(-((fxg - tx) ** 2 + fyg**2) / (2 * (bandwidth * tx) ** 2 + 1e-9))
        mask *= 1 - np.exp(-((fxg + tx) ** 2 + fyg**2) / (2 * (bandwidth * tx) ** 2 + 1e-9))
    for ty in targets_y:
        mask *= 1 - np.exp(-((fyg - ty) ** 2 + fxg**2) / (2 * (bandwidth * ty) ** 2 + 1e-9))
        mask *= 1 - np.exp(-((fyg + ty) ** 2 + fxg**2) / (2 * (bandwidth * ty) ** 2 + 1e-9))
    # never zero out DC
    mask[cy, cx] = 1.0
    filtered = fshift * mask
    img = np.fft.ifft2(np.fft.ifftshift(filtered)).real
    img = np.clip(img, 0, 255).astype(np.uint8)
    return img


def suppress_grid_v2(gray: np.ndarray, calibration: GridCalibration | None = None) -> np.ndarray:
    """FFT notch around the dominant grid pitch then adaptive threshold.

    Falls back to v1 silently if no confident pitch is found.
    """
    import cv2

    cal = calibration or estimate_grid_pitch(gray)
    if cal.pitch_x_px is None or cal.pitch_y_px is None or cal.confidence < 0.1:
        return _suppress_grid_v1(gray)

    notched = _notch_filter_2d(gray, cal.pitch_x_px, cal.pitch_y_px)
    blurred = cv2.GaussianBlur(notched, (5, 5), 0)
    th = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        15,
        4,
    )
    kernel = np.ones((2, 2), np.uint8)
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel, iterations=1)
    return th
