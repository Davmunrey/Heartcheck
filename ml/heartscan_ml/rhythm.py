"""Heart rate / BPM from 1D ECG using SleepECG (fast R-peak detection)."""

from __future__ import annotations

import numpy as np
from sleepecg import detect_heartbeats


def estimate_bpm_from_lead(
    lead: np.ndarray,
    fs: float,
) -> tuple[float | None, int]:
    """Returns (BPM or None if unreliable, number of detected beats)."""
    if lead.size < int(2 * fs):
        return None, 0
    try:
        beats = detect_heartbeats(lead.astype(np.float64), fs)
    except Exception:
        return None, 0
    n = len(beats)
    if n < 2:
        return None, n
    rr_s = np.diff(beats.astype(np.float64)) / fs
    rr_s = rr_s[rr_s > 0]
    if rr_s.size == 0:
        return None, n
    bpm = float(60.0 / np.median(rr_s))
    return bpm, n


def estimate_rr_regularity(lead: np.ndarray, fs: float) -> str:
    """Heurística simple: variabilidad de intervalos RR → regular / irregular / unknown."""
    try:
        beats = detect_heartbeats(lead.astype(np.float64), fs)
    except Exception:
        return "unknown"
    if len(beats) < 4:
        return "unknown"
    rr = np.diff(beats.astype(np.float64)) / fs
    rr = rr[rr > 0]
    if rr.size < 2:
        return "unknown"
    cv = float(np.std(rr) / (np.mean(rr) + 1e-6))
    return "irregular" if cv > 0.12 else "regular"


def estimate_bpm_multilead(
    signal_12: np.ndarray,
    fs: float,
    lead_index: int = 1,
) -> tuple[float | None, int]:
    """Use lead II (index 1) by default; fallback to mean of leads."""
    if signal_12.ndim != 2 or signal_12.shape[0] < 2:
        return None, 0
    lead_ii = signal_12[lead_index]
    bpm, n = estimate_bpm_from_lead(lead_ii, fs)
    if bpm is not None:
        return bpm, n
    merged = signal_12.mean(axis=0)
    return estimate_bpm_from_lead(merged, fs)
