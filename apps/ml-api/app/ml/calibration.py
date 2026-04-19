"""Post-hoc calibration helpers.

- :class:`TemperatureScaler` — single-parameter softmax temperature; trained on
  a validation set to minimise NLL. Reduces ECE without affecting accuracy.
- :class:`ConformalClassifier` — split-conformal prediction. Given calibration
  scores it returns prediction sets with coverage ``≥ 1 - alpha``.

Both are deliberately tiny (no torch optimiser dependency for production
inference) so they can be loaded and applied in the request path with zero
extra latency.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class TemperatureScaler:
    """Apply ``softmax(logits / T)`` with a single learned temperature."""

    temperature: float = 1.0

    def apply(self, logits: np.ndarray) -> np.ndarray:
        if self.temperature <= 0:
            raise ValueError("temperature must be > 0")
        scaled = logits / self.temperature
        scaled -= scaled.max(axis=-1, keepdims=True)
        exp = np.exp(scaled)
        return exp / np.clip(exp.sum(axis=-1, keepdims=True), 1e-12, None)

    def calibrate(self, logits: np.ndarray, labels: np.ndarray) -> float:
        """Grid + ternary search for T minimising NLL on (logits, labels)."""
        if len(labels) == 0:
            self.temperature = 1.0
            return 1.0
        best = (1.0, _nll(self.apply(logits), labels))
        for t in np.geomspace(0.5, 4.0, num=24):
            self.temperature = float(t)
            nll = _nll(self.apply(logits), labels)
            if nll < best[1]:
                best = (float(t), nll)
        # ternary refinement
        lo, hi = best[0] / 1.4, best[0] * 1.4
        for _ in range(20):
            m1 = lo + (hi - lo) / 3
            m2 = hi - (hi - lo) / 3
            self.temperature = m1
            nll1 = _nll(self.apply(logits), labels)
            self.temperature = m2
            nll2 = _nll(self.apply(logits), labels)
            if nll1 < nll2:
                hi = m2
            else:
                lo = m1
        self.temperature = float((lo + hi) / 2)
        return self.temperature


def _nll(probs: np.ndarray, labels: np.ndarray) -> float:
    p = probs[np.arange(len(labels)), labels.astype(np.int64)]
    return float(-np.mean(np.log(np.clip(p, 1e-12, 1.0))))


@dataclass
class ConformalClassifier:
    """Split-conformal classification with the standard score ``s = 1 - p_y``.

    Calibrate once on a held-out set; at inference time
    :meth:`prediction_set` returns the indices whose nonconformity score is
    below the calibrated threshold.
    """

    threshold: float = 1.0  # vacuous default = always returns the full set
    alpha: float = 0.1

    def calibrate(self, probs: np.ndarray, labels: np.ndarray, alpha: float = 0.1) -> float:
        self.alpha = alpha
        if len(labels) == 0:
            self.threshold = 1.0
            return 1.0
        scores = 1.0 - probs[np.arange(len(labels)), labels.astype(np.int64)]
        n = len(scores)
        q_level = float(np.ceil((n + 1) * (1 - alpha)) / n)
        q_level = min(1.0, q_level)
        self.threshold = float(np.quantile(scores, q_level, method="higher"))
        return self.threshold

    def prediction_set(self, probs: np.ndarray) -> list[int]:
        """Return indices included in the prediction set for a single example."""
        scores = 1.0 - np.asarray(probs)
        return [int(i) for i in np.where(scores <= self.threshold)[0]]
