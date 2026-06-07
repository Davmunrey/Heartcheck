"""Calibrate temperature scaling and a split-conformal threshold from a
validation logits dump and bake them into the trained checkpoint.

After this step the checkpoint is ready for production: ``inference.load_model``
will pick up ``temperature`` and ``conformal_threshold`` from the same file.

Inputs
------

- ``--logits``: path to ``val_logits.npz`` with arrays ``logits`` ``(N, C)``
  and ``labels`` ``(N,)``. Produced by ``ml.training.pretrain`` /
  ``ml.training.finetune_image``.
- ``--checkpoint``: path to ``checkpoint.pt`` that will be updated in place.
- ``--alpha``: target mis-coverage (default 0.1 → 90% coverage).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

from heartscan_ml.calibration import (
    ConformalClassifier,
    MultiLabelTemperatureScaler,
    TemperatureScaler,
)
from heartscan_ml.calibration import _bce as _multilabel_bce
from heartscan_ml.eval_metrics import expected_calibration_error


def _calibrate_multilabel(logits: np.ndarray, labels: np.ndarray) -> dict:
    """Scalar sigmoid-temperature calibration for a multi-label ``(N, C)`` head.

    Softmax temperature + split-conformal assume a single label; the diagnostic
    superclass head is multi-label, so we fit one temperature minimising mean
    BCE and report BCE before/after. Per-class decision thresholds live in the
    checkpoint and are unchanged here.
    """
    ts = MultiLabelTemperatureScaler()
    t_star = ts.calibrate(logits, labels)
    sig = lambda z: 1.0 / (1.0 + np.exp(-z))  # noqa: E731
    return {
        "temperature": t_star,
        "multilabel": True,
        "bce_raw": _multilabel_bce(sig(logits), labels),
        "bce_calibrated": _multilabel_bce(ts.apply(logits), labels),
        "n_val": int(len(labels)),
    }


def calibrate(logits: np.ndarray, labels: np.ndarray, alpha: float) -> dict:
    if len(labels) == 0:
        raise RuntimeError("Empty validation set; cannot calibrate.")
    if np.asarray(labels).ndim == 2:
        return _calibrate_multilabel(logits, labels)
    ts = TemperatureScaler()
    t_star = ts.calibrate(logits, labels)
    probs_calibrated = ts.apply(logits)
    cp = ConformalClassifier()
    threshold = cp.calibrate(probs_calibrated, labels, alpha=alpha)

    ece_raw = expected_calibration_error(labels, _softmax(logits))
    ece_cal = expected_calibration_error(labels, probs_calibrated)
    coverage = float(
        np.mean(
            [
                1 - probs_calibrated[i, int(labels[i])] <= threshold
                for i in range(len(labels))
            ]
        )
    )
    return {
        "temperature": t_star,
        "conformal_threshold": threshold,
        "alpha": alpha,
        "ece_raw": ece_raw,
        "ece_calibrated": ece_cal,
        "empirical_coverage": coverage,
        "n_val": int(len(labels)),
    }


def _softmax(logits: np.ndarray) -> np.ndarray:
    z = logits - logits.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


def _bake(checkpoint_path: Path, calibration: dict) -> None:
    state = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if not isinstance(state, dict):
        state = {"state_dict": state}
    state["temperature"] = float(calibration["temperature"])
    if "conformal_threshold" in calibration:
        state["conformal_threshold"] = float(calibration["conformal_threshold"])
    state["calibration"] = {k: v for k, v in calibration.items() if k != "n_val"}
    torch.save(state, checkpoint_path)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Bake temperature + conformal into a checkpoint")
    p.add_argument("--logits", required=True, help="val_logits.npz (or cal_logits.npz)")
    p.add_argument("--checkpoint", required=True, help="checkpoint.pt to update in place")
    p.add_argument("--alpha", type=float, default=0.1)
    p.add_argument("--report", default=None, help="optional JSON report")
    args = p.parse_args(argv)

    logits_path = Path(args.logits)

    # 3-way split: prefer cal_logits.npz for temperature fitting to avoid
    # leakage from checkpoint selection.  Fall back to the provided path with
    # a warning when the sidecar file is absent (e.g. old training runs).
    cal_path = logits_path.parent / "cal_logits.npz"
    held_path = logits_path.parent / "held_logits.npz"

    if cal_path.is_file():
        cal_npz = np.load(cal_path)
        cal_logits, cal_labels = cal_npz["logits"], cal_npz["labels"]
    else:
        import warnings
        warnings.warn(
            f"cal_logits.npz not found next to {logits_path}; using full val set for "
            "calibration fitting.  Re-run pretrain.py to get a proper 3-way split.",
            stacklevel=1,
        )
        cal_npz = np.load(logits_path)
        cal_logits, cal_labels = cal_npz["logits"], cal_npz["labels"]

    cal = calibrate(cal_logits, cal_labels, alpha=args.alpha)
    _bake(Path(args.checkpoint), cal)

    # Report final ECE on the held set when available (single-label only;
    # softmax ECE does not apply to the multi-label head).
    if held_path.is_file() and not cal.get("multilabel"):
        held_npz = np.load(held_path)
        held_logits, held_labels = held_npz["logits"], held_npz["labels"]
        ts = TemperatureScaler(temperature=cal["temperature"])
        held_probs = ts.apply(held_logits)
        cal["held_ece"] = expected_calibration_error(held_labels, held_probs)
        cal["n_held"] = int(len(held_labels))

    print(json.dumps(cal, indent=2))
    if args.report:
        Path(args.report).write_text(json.dumps(cal, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
