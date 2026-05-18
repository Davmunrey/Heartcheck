"""Extract 1D signal (row index per column) from binarized ECG trace."""

from __future__ import annotations

import numpy as np


def extract_trace_1d(binary_trace: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    For each column x, take the mean row of foreground pixels (inverse binary: ink=255).

    Returns:
        x_coords: 0..W-1
        y_signal: row indices (float), shape (W,)
    """
    h, w = binary_trace.shape
    y_signal = np.zeros(w, dtype=np.float64)
    coverage = np.zeros(w, dtype=np.float64)

    for x in range(w):
        col = binary_trace[:, x]
        idx = np.where(col > 128)[0]
        if len(idx) == 0:
            y_signal[x] = np.nan
        else:
            y_signal[x] = float(np.mean(idx))
            coverage[x] = 1.0

    x_coords = np.arange(w, dtype=np.float64)
    return x_coords, y_signal


def resample_signal(y_signal: np.ndarray, target_len: int = 1024) -> np.ndarray:
    """Linearly interpolate to fixed length; fill NaN with forward fill then zero."""
    import numpy as np

    valid = np.isfinite(y_signal)
    if not np.any(valid):
        return np.zeros(target_len, dtype=np.float32)

    y = y_signal.copy()
    idx = np.arange(len(y), dtype=np.float64)
    # simple nan fill
    if np.any(~valid):
        mask = valid
        y[~mask] = np.interp(idx[~mask], idx[mask], y[mask])

    y = y - np.nanmean(y)
    std = np.nanstd(y)
    if std > 1e-6:
        y = y / std
    else:
        y = y * 0.0

    xp = np.linspace(0, len(y) - 1, target_len)
    out = np.interp(xp, np.arange(len(y)), y).astype(np.float32)
    return out
