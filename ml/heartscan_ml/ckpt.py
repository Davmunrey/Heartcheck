from __future__ import annotations

import torch


def load_torch(path: str, map_location: str | torch.device) -> dict:
    try:
        return torch.load(path, map_location=map_location, weights_only=False)
    except TypeError:
        return torch.load(path, map_location=map_location)
