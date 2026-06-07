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
        for t in np.geomspace(0.1, 10.0, num=40):
            self.temperature = float(t)
            nll = _nll(self.apply(logits), labels)
            if nll < best[1]:
                best = (float(t), nll)
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


def _bce(probs: np.ndarray, labels: np.ndarray) -> float:
    """Mean binary cross-entropy for a multi-label ``(N, C)`` target.

    Work in float64: a float32 ``1 - 1e-12`` rounds to exactly ``1.0`` and makes
    ``log(1 - p)`` blow up, so clip after widening.
    """
    p = np.clip(probs.astype(np.float64), 1e-12, 1.0 - 1e-12)
    y = labels.astype(np.float64)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


@dataclass
class MultiLabelTemperatureScaler:
    """Single scalar temperature for an independent per-class sigmoid head.

    Use for multi-label models (e.g. the 12-lead diagnostic superclasses) where
    softmax temperature scaling does not apply. Fits ``T`` minimising mean BCE
    on a validation set; ``apply`` returns ``sigmoid(logits / T)`` element-wise.
    """

    temperature: float = 1.0

    def apply(self, logits: np.ndarray) -> np.ndarray:
        if self.temperature <= 0:
            raise ValueError("temperature must be > 0")
        # Numerically stable sigmoid (avoids exp overflow on large |logits|).
        z = np.asarray(logits, dtype=np.float64) / self.temperature
        out = np.empty_like(z)
        pos = z >= 0
        out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
        ez = np.exp(z[~pos])
        out[~pos] = ez / (1.0 + ez)
        return out

    def calibrate(self, logits: np.ndarray, labels: np.ndarray) -> float:
        """Grid + ternary search for T minimising mean BCE on (logits, labels)."""
        if len(labels) == 0:
            self.temperature = 1.0
            return 1.0
        best = (1.0, _bce(self.apply(logits), labels))
        for t in np.geomspace(0.1, 10.0, num=40):
            self.temperature = float(t)
            loss = _bce(self.apply(logits), labels)
            if loss < best[1]:
                best = (float(t), loss)
        lo, hi = best[0] / 1.4, best[0] * 1.4
        for _ in range(20):
            m1 = lo + (hi - lo) / 3
            m2 = hi - (hi - lo) / 3
            self.temperature = m1
            loss1 = _bce(self.apply(logits), labels)
            self.temperature = m2
            loss2 = _bce(self.apply(logits), labels)
            if loss1 < loss2:
                hi = m2
            else:
                lo = m1
        self.temperature = float((lo + hi) / 2)
        return self.temperature


@dataclass
class ConformalClassifier:
    """Split-conformal classification with the standard score ``s = 1 - p_y``.

    Calibrate once on a held-out set; at inference time
    :meth:`prediction_set` returns the indices whose nonconformity score is
    below the calibrated threshold.
    """

    threshold: float = 1.0
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
