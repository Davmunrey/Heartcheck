"""Tiny U-Net for ECG-trace segmentation (plan v2 §C1).

The actual training pipeline lives in ``ml/`` and uses the synthetic dataset
produced by :mod:`app.eval.synth`. This module only ships the architecture
plus a safe runtime wrapper so the FastAPI backend can use it when a
checkpoint is present, and **silently fall back** to the OpenCV extractor
when the model can't load.

Design constraints
------------------

- ~50k–200k params (CPU-friendly).
- Input: ``(B, 1, H, W)`` grayscale, normalised to ``[0, 1]``.
- Output: ``(B, 1, H, W)`` per-pixel logits ("trace" vs "background").
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def _conv_block(in_ch: int, out_ch: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1),
        nn.BatchNorm2d(out_ch),
        nn.ReLU(inplace=True),
        nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1),
        nn.BatchNorm2d(out_ch),
        nn.ReLU(inplace=True),
    )


class TinyUNet(nn.Module):
    """3-level U-Net with shallow channels for trace segmentation."""

    def __init__(self, base: int = 16) -> None:
        super().__init__()
        self.enc1 = _conv_block(1, base)
        self.enc2 = _conv_block(base, base * 2)
        self.enc3 = _conv_block(base * 2, base * 4)
        self.pool = nn.MaxPool2d(2)
        self.up2 = nn.ConvTranspose2d(base * 4, base * 2, kernel_size=2, stride=2)
        self.dec2 = _conv_block(base * 4, base * 2)
        self.up1 = nn.ConvTranspose2d(base * 2, base, kernel_size=2, stride=2)
        self.dec1 = _conv_block(base * 2, base)
        self.head = nn.Conv2d(base, 1, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        d2 = self.dec2(torch.cat([self.up2(e3), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
        return self.head(d1)


_LOADED: TinyUNet | None = None


def load_unet(weights_path: str | Path | None) -> TinyUNet | None:
    """Best-effort load. Returns ``None`` if path is missing or load fails."""
    global _LOADED
    if not weights_path:
        _LOADED = None
        return None
    p = Path(weights_path)
    if not p.is_file():
        _LOADED = None
        return None
    try:
        state = torch.load(p, map_location="cpu", weights_only=True)
    except Exception:  # noqa: BLE001
        _LOADED = None
        return None
    model = TinyUNet()
    try:
        model.load_state_dict(state if isinstance(state, dict) and "weight" not in state.keys() else state, strict=False)
    except Exception:  # noqa: BLE001
        _LOADED = None
        return None
    model.eval()
    _LOADED = model
    return model


def get_unet() -> TinyUNet | None:
    return _LOADED


def segment(gray: np.ndarray, threshold: float = 0.5) -> np.ndarray | None:
    """Run inference; return uint8 mask (255 = trace) or ``None`` if unavailable."""
    if _LOADED is None:
        return None
    h, w = gray.shape
    # pad to multiple of 4 for the two pool/up cycles
    h2 = ((h + 3) // 4) * 4
    w2 = ((w + 3) // 4) * 4
    pad = np.pad(gray.astype(np.float32) / 255.0, ((0, h2 - h), (0, w2 - w)))
    x = torch.from_numpy(pad).unsqueeze(0).unsqueeze(0)
    with torch.no_grad():
        logits = _LOADED(x)
        probs = torch.sigmoid(logits).numpy()[0, 0]
    mask = (probs[:h, :w] >= threshold).astype(np.uint8) * 255
    return mask
