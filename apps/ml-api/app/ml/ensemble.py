"""Optional ensemble of small models (plan v2 §D6).

Behaviour
---------

- If a directory of ``*.pt`` checkpoints is configured via
  :func:`load_ensemble`, inference averages softmax probabilities across all
  members.
- When the ensemble is empty, callers fall back to the single model loaded
  by :mod:`app.services.inference`.

This is opt-in: the production deploy decides whether to pay the latency cost
based on the eval-harness numbers.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from app.ml.cnn1d import build_default_model

_MEMBERS: list[torch.nn.Module] = []


def load_ensemble(directory: str | Path | None) -> int:
    """Load every ``*.pt`` from ``directory`` into memory. Returns count."""
    global _MEMBERS
    _MEMBERS = []
    if not directory:
        return 0
    d = Path(directory)
    if not d.is_dir():
        return 0
    for path in sorted(d.glob("*.pt")):
        try:
            state = torch.load(path, map_location="cpu", weights_only=True)
        except Exception:  # noqa: BLE001
            continue
        m = build_default_model()
        try:
            payload = state["state_dict"] if isinstance(state, dict) and "state_dict" in state else state
            m.load_state_dict(payload, strict=False)
        except Exception:  # noqa: BLE001
            continue
        m.eval()
        _MEMBERS.append(m)
    return len(_MEMBERS)


def get_size() -> int:
    return len(_MEMBERS)


def predict_probs(signal: np.ndarray) -> np.ndarray | None:
    """Average softmax probabilities across ensemble members. ``None`` if empty."""
    if not _MEMBERS:
        return None
    x = torch.from_numpy(signal.astype(np.float32)).unsqueeze(0).unsqueeze(0)
    probs_acc: np.ndarray | None = None
    with torch.no_grad():
        for m in _MEMBERS:
            logits = m(x).cpu().numpy()
            shifted = logits - logits.max(axis=-1, keepdims=True)
            exp = np.exp(shifted)
            p = exp / exp.sum(axis=-1, keepdims=True)
            probs_acc = p if probs_acc is None else probs_acc + p
    if probs_acc is None:
        return None
    return (probs_acc / len(_MEMBERS))[0]
