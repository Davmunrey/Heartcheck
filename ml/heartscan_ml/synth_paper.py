"""Synthetic ECG-on-paper rendering for domain randomization (not clinical validation)."""

from __future__ import annotations

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None


def render_trace_to_image(
    lead_1d: np.ndarray,
    height: int = 128,
    width: int = 512,
    grid_mm: int = 5,
    sigma_blur: float = 0.8,
) -> np.ndarray:
    """Draw a single normalized lead as a greyscale image (numpy + optional Gaussian blur)."""
    if cv2 is None:
        raise ImportError("opencv-python-headless required for synth_paper.render_trace_to_image")
    lead = lead_1d.astype(np.float32)
    lead = (lead - lead.min()) / (lead.max() - lead.min() + 1e-6)
    y = (lead * (height - 8) + 4).astype(np.int32)
    img = np.ones((height, width), dtype=np.float32) * 0.95
    xs = np.linspace(0, width - 1, num=len(y), dtype=np.int32)
    for i in range(len(xs) - 1):
        cv2.line(img, (int(xs[i]), int(y[i])), (int(xs[i + 1]), int(y[i + 1])), 0.15, 1)
    step = max(1, width // (width // grid_mm))
    for x in range(0, width, step):
        img[:, x] = np.minimum(img[:, x], 0.85)
    for yy in range(0, height, step):
        img[yy, :] = np.minimum(img[yy, :], 0.85)
    img = np.clip(img, 0, 1)
    if sigma_blur > 0:
        k = max(1, int(sigma_blur * 3)) | 1
        img = cv2.GaussianBlur(img, (k, k), sigma_blur)
    return (img * 255).astype(np.uint8)
