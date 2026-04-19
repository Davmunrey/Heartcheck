"""Load CNN weights and run inference with optional TTA, calibration and
conformal prediction.

Security
--------
Checkpoints are loaded with ``torch.load(weights_only=True)`` (PyTorch ≥ 2.4)
to prevent arbitrary code execution via pickle. ``HEARTSCAN_ALLOW_UNSAFE_TORCH_LOAD``
is the explicit, audited escape hatch for older runtimes.

Provenance
----------
Each checkpoint should ship next to a ``<name>.yaml`` manifest. In production
(``HEARTSCAN_ENV=production``) :func:`load_model` refuses to start without a
matching manifest. See :mod:`app.ml.manifest`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from app.core.logging import get_logger
from app.ml.calibration import ConformalClassifier, TemperatureScaler
from app.ml.manifest import CheckpointManifest, load_manifest

logger = get_logger(__name__)

CLASS_NAMES = ("normal", "arrhythmia", "noise")

# Lazy torch/cnn1d: importing PyTorch at module load blocks HTTP for tens of seconds
# on cold start; the API and static pages should bind immediately.
_DEVICE: Any | None = None


def _get_device() -> Any:
    global _DEVICE
    if _DEVICE is None:
        import torch

        _DEVICE = torch.device("cpu")
    return _DEVICE


@dataclass
class _ModelState:
    model: Any = None
    version: str = "ecg-resnet1d-0.1.0-untrained"
    manifest: CheckpointManifest | None = None
    temperature: TemperatureScaler = field(default_factory=TemperatureScaler)
    conformal: ConformalClassifier = field(default_factory=ConformalClassifier)


_STATE = _ModelState()


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _safe_load(weights_path: Path) -> dict:
    import torch

    dev = _get_device()
    allow_unsafe = os.environ.get("HEARTSCAN_ALLOW_UNSAFE_TORCH_LOAD", "").lower() in {
        "1",
        "true",
        "yes",
    }
    try:
        return torch.load(weights_path, map_location=dev, weights_only=True)
    except TypeError:
        if not allow_unsafe:
            raise
        logger.warning("torch_load_unsafe_fallback", path=str(weights_path))
        return torch.load(weights_path, map_location=dev)
    except Exception:  # noqa: BLE001
        if allow_unsafe:
            logger.warning("torch_load_unsafe_fallback", path=str(weights_path))
            return torch.load(weights_path, map_location=dev)
        raise


def load_model(weights_path: str | None) -> tuple[Any, str]:
    """Build (and optionally fill) the default model.

    Resolves a sibling YAML manifest, refuses missing manifests in production,
    and loads optional ``temperature`` / ``conformal`` calibration data shipped
    alongside the weights when present.
    """
    from app.ml.cnn1d import build_default_model, default_model_version

    model = build_default_model()
    version = default_model_version()
    manifest: CheckpointManifest | None = None

    if weights_path:
        path = Path(weights_path)
        if path.is_file():
            manifest = _resolve_manifest(path)
            state = _safe_load(path)
            if isinstance(state, dict) and "state_dict" in state:
                model.load_state_dict(state["state_dict"], strict=False)
                version = str(state.get("version", manifest.model_version if manifest else version))
                temp = state.get("temperature")
                if temp is not None:
                    _STATE.temperature = TemperatureScaler(temperature=float(temp))
                conf_threshold = state.get("conformal_threshold")
                if conf_threshold is not None:
                    _STATE.conformal = ConformalClassifier(threshold=float(conf_threshold))
            else:
                model.load_state_dict(state, strict=False)
                version = manifest.model_version if manifest else f"loaded:{path.name}"
        else:
            logger.warning("model_path_missing", path=str(path))

    model.eval()
    _STATE.model = model
    _STATE.version = version
    _STATE.manifest = manifest
    return model, version


def _resolve_manifest(weights_path: Path) -> CheckpointManifest | None:
    yaml_path = weights_path.with_suffix(weights_path.suffix + ".yaml")
    legacy_yaml = weights_path.with_suffix(".yaml")
    candidate = yaml_path if yaml_path.is_file() else legacy_yaml
    env = os.environ.get("HEARTSCAN_ENV", "development").lower()
    if not candidate.is_file():
        if env == "production":
            raise RuntimeError(
                f"Refusing to load checkpoint {weights_path} in production without a manifest "
                f"(expected at {yaml_path} or {legacy_yaml})."
            )
        logger.warning("checkpoint_manifest_missing", path=str(weights_path))
        return None
    manifest = load_manifest(candidate)
    if env == "production":
        manifest.verify_against_file(weights_path)
    return manifest


# ---------------------------------------------------------------------------
# Public accessors
# ---------------------------------------------------------------------------


def get_model() -> Any | None:
    return _STATE.model


def get_model_version() -> str:
    return _STATE.version


def get_manifest() -> CheckpointManifest | None:
    return _STATE.manifest


def get_temperature() -> float:
    return _STATE.temperature.temperature


def get_conformal_threshold() -> float:
    return _STATE.conformal.threshold


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------


def _logits_for(signal: np.ndarray) -> np.ndarray:
    import torch

    model = _STATE.model
    if model is None:
        return np.zeros((1, len(CLASS_NAMES)), dtype=np.float64)
    dev = _get_device()
    x = torch.from_numpy(signal.astype(np.float32)).unsqueeze(0).unsqueeze(0)
    with torch.no_grad():
        return model(x.to(dev)).cpu().numpy()


def _tta_signals(signal: np.ndarray, n: int = 5) -> list[np.ndarray]:
    """Cheap deterministic TTA: small temporal shifts and an inversion."""
    if n <= 1:
        return [signal]
    L = len(signal)
    out = [signal]
    shifts = [-L // 32, L // 32, -L // 16, L // 16]
    for s in shifts[: n - 1]:
        out.append(np.roll(signal, s))
    return out


def infer_class(signal_1024: np.ndarray, *, tta: int = 1) -> tuple[str, float]:
    """Return ``(class_label, confidence)``.

    ``confidence`` is the *calibrated* probability of the predicted class when
    a temperature is configured.
    """
    if _STATE.model is None:
        return "noise", 0.0

    if tta > 1:
        logits_list = [_logits_for(s)[0] for s in _tta_signals(signal_1024, tta)]
        logits_mean = np.mean(np.stack(logits_list), axis=0, keepdims=True)
    else:
        logits_mean = _logits_for(signal_1024)

    probs = _STATE.temperature.apply(logits_mean)[0]
    idx = int(np.argmax(probs))
    return CLASS_NAMES[idx], float(probs[idx])


def predict_distribution(signal_1024: np.ndarray, *, tta: int = 1) -> dict[str, Any]:
    """Return calibrated probabilities and the conformal prediction set."""
    if _STATE.model is None:
        return {
            "probs": {n: 1.0 / len(CLASS_NAMES) for n in CLASS_NAMES},
            "prediction_set": list(CLASS_NAMES),
            "calibrated_confidence": 0.0,
        }
    if tta > 1:
        logits_list = [_logits_for(s)[0] for s in _tta_signals(signal_1024, tta)]
        logits_mean = np.mean(np.stack(logits_list), axis=0, keepdims=True)
    else:
        logits_mean = _logits_for(signal_1024)

    probs = _STATE.temperature.apply(logits_mean)[0]
    set_idx = _STATE.conformal.prediction_set(probs)
    if not set_idx:
        set_idx = [int(np.argmax(probs))]
    return {
        "probs": {CLASS_NAMES[i]: float(probs[i]) for i in range(len(CLASS_NAMES))},
        "prediction_set": [CLASS_NAMES[i] for i in set_idx],
        "calibrated_confidence": float(probs[int(np.argmax(probs))]),
    }
