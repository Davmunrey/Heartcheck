"""1D classifiers for ECG waveform classification (3 classes).

Two architectures are exported:

- :class:`ECGCNN1D` — small baseline convnet kept for backward compatibility.
- :class:`ECGResNet1D` — slightly deeper residual model used as the new
  baseline once weights are available; still tiny (~150k params) so CPU
  inference stays under SLO.

Both expose the same forward signature ``(B, 1, L) -> (B, num_classes)``.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class ECGCNN1D(nn.Module):
    """Small convolutional classifier — legacy baseline."""

    def __init__(self, num_classes: int = 3, length: int = 1024) -> None:
        super().__init__()
        self.length = length
        self.features = nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=7, padding=3),
            nn.BatchNorm1d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),
            nn.Conv1d(32, 64, kernel_size=5, padding=2),
            nn.BatchNorm1d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),
            nn.Conv1d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool1d(1),
        )
        self.head = nn.Linear(128, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = x.flatten(1)
        return self.head(x)


class _ResBlock1D(nn.Module):
    def __init__(self, channels: int, kernel: int = 5) -> None:
        super().__init__()
        pad = kernel // 2
        self.body = nn.Sequential(
            nn.Conv1d(channels, channels, kernel, padding=pad),
            nn.BatchNorm1d(channels),
            nn.ReLU(inplace=True),
            nn.Conv1d(channels, channels, kernel, padding=pad),
            nn.BatchNorm1d(channels),
        )
        self.act = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.act(x + self.body(x))


class ECGResNet1D(nn.Module):
    """Residual 1D classifier; new baseline once trained weights ship.

    Design notes:
    - kept under ~150k params so CPU inference stays under 50 ms for L=1024;
    - dropout before the head reduces overconfidence (helps calibration);
    - returns logits — calibration (temperature scaling) is applied outside.
    """

    def __init__(self, num_classes: int = 3, length: int = 1024) -> None:
        super().__init__()
        self.length = length
        self.stem = nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=7, padding=3),
            nn.BatchNorm1d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),
        )
        self.stage1 = nn.Sequential(_ResBlock1D(32), _ResBlock1D(32))
        self.down1 = nn.Sequential(
            nn.Conv1d(32, 64, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(inplace=True),
        )
        self.stage2 = nn.Sequential(_ResBlock1D(64), _ResBlock1D(64))
        self.down2 = nn.Sequential(
            nn.Conv1d(64, 96, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm1d(96),
            nn.ReLU(inplace=True),
        )
        self.stage3 = nn.Sequential(_ResBlock1D(96), _ResBlock1D(96))
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.dropout = nn.Dropout(0.2)
        self.head = nn.Linear(96, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.stem(x)
        x = self.stage1(x)
        x = self.down1(x)
        x = self.stage2(x)
        x = self.down2(x)
        x = self.stage3(x)
        x = self.pool(x).flatten(1)
        x = self.dropout(x)
        return self.head(x)


def build_default_model(num_classes: int = 3, length: int = 1024) -> nn.Module:
    """Construct the default classifier; switch architectures here in the future."""
    return ECGResNet1D(num_classes=num_classes, length=length)


def default_model_version() -> str:
    return "ecg-resnet1d-0.1.0-untrained"
