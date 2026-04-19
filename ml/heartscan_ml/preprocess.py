from __future__ import annotations

import numpy as np


def resample_linear(signal: np.ndarray, fs_in: int, fs_out: int) -> np.ndarray:
    """signal: (leads, time)."""
    if fs_in == fs_out:
        return signal.astype(np.float32)
    n_in = signal.shape[1]
    n_out = max(2, int(round(n_in * fs_out / fs_in)))
    x_old = np.linspace(0.0, 1.0, n_in)
    x_new = np.linspace(0.0, 1.0, n_out)
    out = np.empty((signal.shape[0], n_out), dtype=np.float32)
    for i in range(signal.shape[0]):
        out[i] = np.interp(x_new, x_old, signal[i].astype(np.float64)).astype(np.float32)
    return out


def zscore_per_lead(x: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """x: (leads, time)."""
    m = x.mean(axis=1, keepdims=True)
    s = x.std(axis=1, keepdims=True)
    return ((x - m) / (s + eps)).astype(np.float32)


def crop_center(x: np.ndarray, length: int) -> np.ndarray:
    t = x.shape[1]
    if t >= length:
        start = (t - length) // 2
        return x[:, start : start + length]
    pad = length - t
    left = pad // 2
    return np.pad(x, ((0, 0), (left, left + (pad % 2))), mode="edge")


def add_noise_augmentation(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Heavy noise + baseline wander → proxy training label 'noise'."""
    y = x.astype(np.float64)
    n = rng.normal(0, 0.35, size=y.shape)
    wander = rng.normal(0, 0.2, size=(y.shape[0], 1)) * np.sin(
        np.linspace(0, 4 * np.pi, y.shape[1], dtype=np.float64)
    )
    y = y + n + wander
    return y.astype(np.float32)
