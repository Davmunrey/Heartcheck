"""Shared utilities for ml/training scripts."""

from __future__ import annotations

import numpy as np


def macro_f1(true: np.ndarray, pred: np.ndarray, n_classes: int) -> float:
    """Compute macro-averaged F1 score without external dependencies."""
    f1s = []
    for c in range(n_classes):
        tp = int(((pred == c) & (true == c)).sum())
        fp = int(((pred == c) & (true != c)).sum())
        fn = int(((pred != c) & (true == c)).sum())
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if (prec + rec) else 0.0)
    return float(np.mean(f1s))
