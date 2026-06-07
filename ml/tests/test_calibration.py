"""Calibration: single-label (softmax) stays intact; multi-label (sigmoid) works."""

import numpy as np

from heartscan_ml.calibration import (
    MultiLabelTemperatureScaler,
    TemperatureScaler,
    _bce,
)


def test_single_label_temperature_unchanged() -> None:
    rng = np.random.default_rng(0)
    logits = rng.normal(size=(200, 3)).astype(np.float32)
    labels = rng.integers(0, 3, size=200)
    ts = TemperatureScaler()
    t = ts.calibrate(logits, labels)
    assert t > 0
    probs = ts.apply(logits)
    assert probs.shape == (200, 3)
    np.testing.assert_allclose(probs.sum(axis=1), 1.0, atol=1e-5)


def test_multilabel_temperature_fits_and_applies() -> None:
    rng = np.random.default_rng(1)
    labels = rng.integers(0, 2, size=(300, 5)).astype(np.float32)
    # Over-confident logits (×3) so a temperature > 1 should reduce BCE.
    base = np.where(labels > 0, 2.0, -2.0).astype(np.float32)
    logits = (base + 0.3 * rng.normal(size=labels.shape)).astype(np.float32) * 3.0

    ts = MultiLabelTemperatureScaler()
    t = ts.calibrate(logits, labels)
    assert t > 0
    probs = ts.apply(logits)
    assert probs.shape == (300, 5)
    assert ((probs >= 0) & (probs <= 1)).all()
    # Calibration should not worsen BCE versus T=1.
    sig = 1.0 / (1.0 + np.exp(-logits))
    assert _bce(probs, labels) <= _bce(sig, labels) + 1e-6


def test_multilabel_calibrate_path_no_crash() -> None:
    from ml.training.calibrate import calibrate

    rng = np.random.default_rng(2)
    labels = rng.integers(0, 2, size=(150, 5)).astype(np.float32)
    logits = np.where(labels > 0, 1.5, -1.5).astype(np.float32)
    out = calibrate(logits, labels, alpha=0.1)
    assert out["multilabel"] is True
    assert out["temperature"] > 0
    assert "conformal_threshold" not in out
    assert out["bce_calibrated"] <= out["bce_raw"] + 1e-6
