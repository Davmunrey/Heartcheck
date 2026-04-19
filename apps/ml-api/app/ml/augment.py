"""Data augmentations matched to the failure modes of photo extraction.

Used by the ``ml/`` training pipeline; kept inside ``apps/ml-api/app/ml`` so the
shipped runtime can apply the same transforms during test-time augmentation
or robustness checks.

All transforms operate on a 1D float signal of fixed length and return a new
array of the same length so they can be chained.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class AugmentConfig:
    jitter_std: float = 0.05
    drift_amplitude: float = 0.1
    drift_period_min: int = 200
    drift_period_max: int = 800
    time_warp_max: float = 0.05  # fraction
    noise_std: float = 0.05
    invert_prob: float = 0.05  # mimics inverted polarity from photo extraction


def apply_jitter(signal: np.ndarray, std: float, rng: np.random.Generator) -> np.ndarray:
    return signal + rng.normal(0.0, std, size=signal.shape)


def apply_drift(signal: np.ndarray, amp: float, period_min: int, period_max: int, rng: np.random.Generator) -> np.ndarray:
    period = float(rng.integers(period_min, period_max + 1))
    phase = float(rng.uniform(0, 2 * np.pi))
    x = np.arange(len(signal), dtype=np.float64)
    return signal + amp * np.sin(2 * np.pi * x / period + phase)


def apply_time_warp(signal: np.ndarray, max_frac: float, rng: np.random.Generator) -> np.ndarray:
    """Locally stretch/squeeze the signal by interpolation."""
    L = len(signal)
    factor = 1.0 + float(rng.uniform(-max_frac, max_frac))
    new_L = max(2, int(round(L * factor)))
    src = np.linspace(0, L - 1, new_L)
    stretched = np.interp(src, np.arange(L), signal)
    # crop or pad back to L
    if new_L >= L:
        start = (new_L - L) // 2
        return stretched[start : start + L]
    out = np.zeros(L, dtype=signal.dtype)
    start = (L - new_L) // 2
    out[start : start + new_L] = stretched
    return out


def apply_noise(signal: np.ndarray, std: float, rng: np.random.Generator) -> np.ndarray:
    return signal + rng.normal(0.0, std, size=signal.shape)


def maybe_invert(signal: np.ndarray, prob: float, rng: np.random.Generator) -> np.ndarray:
    return -signal if rng.random() < prob else signal


def augment_signal(signal: np.ndarray, cfg: AugmentConfig, seed: int | None = None) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = signal.astype(np.float64)
    out = apply_jitter(out, cfg.jitter_std, rng)
    out = apply_drift(out, cfg.drift_amplitude, cfg.drift_period_min, cfg.drift_period_max, rng)
    out = apply_time_warp(out, cfg.time_warp_max, rng)
    out = apply_noise(out, cfg.noise_std, rng)
    out = maybe_invert(out, cfg.invert_prob, rng)
    return out.astype(np.float32)
