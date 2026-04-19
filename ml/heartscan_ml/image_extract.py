"""Vectorizar trazo ECG desde foto (una derivación horizontal aproximada).

La señal se replica en 12 canales para el CNN entrenado en 12 derivaciones (modo cribado).
"""

from __future__ import annotations

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None


def _ensure_cv2():
    if cv2 is None:
        raise ImportError("opencv-python-headless is required for image extraction")


def _interpolate_nans(y: np.ndarray) -> np.ndarray:
    n = y.size
    mask = np.isfinite(y)
    if not mask.any():
        return np.zeros(n, dtype=np.float32)
    if mask.all():
        return y.astype(np.float32)
    x = np.arange(n)
    good = x[mask]
    vals = y[mask].astype(np.float64)
    filled = np.interp(x, good, vals).astype(np.float32)
    return filled


def extract_lead_1d_from_gray(gray: np.ndarray, target_len: int = 1000) -> tuple[np.ndarray, float]:
    """Extrae una serie 1D (posición vertical del trazo por columna) y score 0–1 de cobertura."""
    _ensure_cv2()
    h, w = gray.shape[:2]
    if w < 16 or h < 16:
        raise ValueError("Image too small")

    small = cv2.resize(gray, (target_len, max(64, min(h, 256))), interpolation=cv2.INTER_AREA)
    hs, ws = small.shape[:2]
    blur = cv2.GaussianBlur(small, (5, 5), 0)
    _, bw = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ys: list[float] = []
    for x in range(ws):
        col = bw[:, x]
        rows = np.where(col > 0)[0]
        if rows.size == 0:
            ys.append(float("nan"))
        else:
            ys.append(float(np.mean(rows)))

    y = np.array(ys, dtype=np.float32)
    y = _interpolate_nans(y)
    y = (y - y.mean()) / (y.std() + 1e-6)
    activity = float(np.std(y))
    edge = float(np.mean(np.abs(np.diff(y)))) if y.size > 1 else 0.0
    # Proxy 0–1: trazo con variación vs. línea plana o fallo de detección
    coverage = min(1.0, max(0.0, 0.35 * activity + 0.45 * min(edge, 2.0)))
    return y.astype(np.float32), coverage


def load_image_bgr(path: str) -> np.ndarray:
    _ensure_cv2()
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    return img


def image_file_to_gray(path: str) -> np.ndarray:
    bgr = load_image_bgr(path)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)


def bytes_to_gray(data: bytes) -> np.ndarray:
    _ensure_cv2()
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Could not decode image bytes")
    return img


def single_lead_to_12(single: np.ndarray) -> np.ndarray:
    """(T,) -> (12, T) misma señal en todos los canales."""
    t = single.shape[0]
    return np.tile(single[np.newaxis, :], (12, 1)).astype(np.float32)


def extraction_quality_score(coverage: float) -> int:
    """1–3 para API; 3 = buena cobertura de trazo."""
    if coverage >= 0.45:
        return 3
    if coverage >= 0.2:
        return 2
    return 1
