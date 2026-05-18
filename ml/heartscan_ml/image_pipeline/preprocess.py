"""Image loading and grayscale conversion."""

from __future__ import annotations

import numpy as np


def decode_image_to_gray(image_bytes: bytes) -> np.ndarray:
    """Decode bytes to single-channel uint8 grayscale via OpenCV."""
    import cv2

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("Could not decode image")
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return gray
