"""Pure-python evaluation metrics for the HeartScan harness.

No sklearn dependency: keeps the eval pipeline shippable inside any minimal
backend image and trivially reviewable. Inputs are aligned numpy arrays.

Conventions
-----------
- ``y_true``: integer class indices (0..C-1).
- ``y_pred``: integer class indices (0..C-1).
- ``probs``: ``(N, C)`` softmax probabilities.
- ``confidence``: ``(N,)`` model self-reported confidence in ``[0, 1]``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ClassificationReport:
    accuracy: float
    f1_macro: float
    f1_per_class: dict[str, float]
    confusion: list[list[int]]
    support: list[int]


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int) -> np.ndarray:
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for t, p in zip(y_true, y_pred, strict=True):
        if 0 <= t < num_classes and 0 <= p < num_classes:
            cm[int(t), int(p)] += 1
    return cm


def classification_report(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: list[str],
) -> ClassificationReport:
    n_classes = len(class_names)
    cm = confusion_matrix(y_true, y_pred, n_classes)
    support = cm.sum(axis=1).tolist()
    correct = int(np.trace(cm))
    total = int(cm.sum())
    accuracy = correct / total if total else 0.0

    f1_per: dict[str, float] = {}
    for i, name in enumerate(class_names):
        tp = int(cm[i, i])
        fp = int(cm[:, i].sum() - tp)
        fn = int(cm[i, :].sum() - tp)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        f1_per[name] = float(f1)

    f1_macro = float(np.mean(list(f1_per.values()))) if f1_per else 0.0
    return ClassificationReport(
        accuracy=float(accuracy),
        f1_macro=f1_macro,
        f1_per_class=f1_per,
        confusion=cm.tolist(),
        support=support,
    )


def expected_calibration_error(
    y_true: np.ndarray,
    probs: np.ndarray,
    n_bins: int = 15,
) -> float:
    """Top-label ECE.

    Bins predictions by the max class probability and computes the weighted
    absolute difference between confidence and accuracy in each bin.
    """
    if probs.ndim != 2:
        raise ValueError("probs must be 2D (N, C)")
    pred = np.argmax(probs, axis=1)
    conf = np.max(probs, axis=1)
    correct = (pred == y_true).astype(np.float64)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    n = len(y_true)
    if n == 0:
        return 0.0
    ece = 0.0
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (conf > lo) & (conf <= hi) if i > 0 else (conf >= lo) & (conf <= hi)
        if not np.any(mask):
            continue
        w = float(mask.mean())
        gap = abs(float(conf[mask].mean()) - float(correct[mask].mean()))
        ece += w * gap
    return float(ece)


def brier_score_multiclass(y_true: np.ndarray, probs: np.ndarray, num_classes: int) -> float:
    """Mean squared error between one-hot ground truth and probabilities."""
    if len(y_true) == 0:
        return 0.0
    onehot = np.zeros_like(probs)
    onehot[np.arange(len(y_true)), y_true.astype(np.int64)] = 1.0
    return float(np.mean(np.sum((probs - onehot) ** 2, axis=1)))


def auroc_binary(scores: np.ndarray, positives: np.ndarray) -> float:
    """ROC-AUC for "is the model right?" given a confidence-like score.

    Implementation uses the rank-sum identity (Mann-Whitney U).
    Returns 0.5 when one of the classes is empty.
    """
    pos = scores[positives.astype(bool)]
    neg = scores[~positives.astype(bool)]
    if len(pos) == 0 or len(neg) == 0:
        return 0.5
    order = np.argsort(np.concatenate([pos, neg]))
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(1, len(order) + 1)
    pos_ranks = ranks[: len(pos)]
    auc = (pos_ranks.sum() - len(pos) * (len(pos) + 1) / 2.0) / (len(pos) * len(neg))
    return float(auc)


def confidence_correctness_auroc(y_true: np.ndarray, probs: np.ndarray) -> float:
    """AUROC of "max prob" as a detector for correctness."""
    pred = np.argmax(probs, axis=1)
    conf = np.max(probs, axis=1)
    correct = (pred == y_true).astype(np.int64)
    return auroc_binary(conf, correct)


def percentile(values: list[float] | np.ndarray, q: float) -> float:
    if len(values) == 0:
        return 0.0
    return float(np.percentile(np.asarray(values, dtype=np.float64), q))


def abstention_rate(predicted_class: list[str | None]) -> float:
    if not predicted_class:
        return 0.0
    return float(sum(1 for p in predicted_class if p is None) / len(predicted_class))
