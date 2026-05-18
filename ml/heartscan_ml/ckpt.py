from __future__ import annotations

import json
import logging
import torch
from pathlib import Path

_logger = logging.getLogger(__name__)


def load_torch(path: str, map_location: str | torch.device) -> dict:
    """Load a checkpoint with weights_only=True for security.

    Non-tensor metadata (temperature, conformal_threshold) are stored in a
    sidecar JSON at the same path with a ``.json`` extension.  If no sidecar
    exists the function falls back gracefully so older checkpoints still load.
    """
    try:
        state = torch.load(path, map_location=map_location, weights_only=True)
    except TypeError:
        # PyTorch < 2.0 does not accept weights_only keyword.
        state = torch.load(path, map_location=map_location)

    # Merge sidecar metadata so callers find temperature/conformal_threshold
    # under the expected keys without trusting pickled Python objects.
    sidecar = Path(str(path)).with_suffix(".json")
    if sidecar.is_file():
        try:
            meta = json.loads(sidecar.read_text(encoding="utf-8"))
            if isinstance(meta, dict):
                for k, v in meta.items():
                    if k not in state:
                        state[k] = v
        except Exception:  # noqa: BLE001
            _logger.warning("ckpt_sidecar_malformed", extra={"path": str(sidecar)})

    return state
