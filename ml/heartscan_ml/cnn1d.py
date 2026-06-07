"""1D classifiers for ECG waveform classification (3 classes).

Canonical source for ECGResNet1D shared between the heartscan_ml training
package and apps/ml-api. Both must stay in sync — the checkpoint format
is tied to this architecture definition.

Two architectures are exported:

- :class:`ECGCNN1D` — small baseline convnet kept for backward compatibility.
- :class:`ECGResNet1D` — slightly deeper residual model; ~150k params so CPU
  inference stays under SLO.

Both expose the same forward signature ``(B, C, L) -> (B, num_classes)``.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class ECGCNN1D(nn.Module):
    """Small convolutional classifier — legacy baseline."""

    def __init__(self, num_classes: int = 3, length: int = 1024, in_channels: int = 1) -> None:
        super().__init__()
        self.length = length
        self.in_channels = in_channels
        self.features = nn.Sequential(
            nn.Conv1d(in_channels, 32, kernel_size=7, padding=3),
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

    def __init__(self, num_classes: int = 3, length: int = 1024, in_channels: int = 1) -> None:
        super().__init__()
        self.length = length
        self.in_channels = in_channels
        self.stem = nn.Sequential(
            nn.Conv1d(in_channels, 32, kernel_size=7, padding=3),
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


class _ResidualUnit1D(nn.Module):
    """Ribeiro-style residual unit with strided downsampling and a pooled skip.

    Adapted from Ribeiro et al. (Nature Comms 2020;
    antonior92/automatic-ecg-diagnosis). Each unit halves/quarters the temporal
    length and grows channels, so the network learns multi-scale morphology
    natively — robust to sampling-rate / QRS-width changes.
    """

    def __init__(self, in_ch: int, out_ch: int, kernel: int = 17, downsample: int = 4, dropout: float = 0.2) -> None:
        super().__init__()
        pad = kernel // 2
        self.main = nn.Sequential(
            nn.Conv1d(in_ch, out_ch, kernel, padding=pad),
            nn.BatchNorm1d(out_ch),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Conv1d(out_ch, out_ch, kernel, stride=downsample, padding=pad),
            nn.BatchNorm1d(out_ch),
        )
        self.skip = nn.Sequential(
            nn.MaxPool1d(downsample),
            nn.Conv1d(in_ch, out_ch, kernel_size=1),
        )
        self.act = nn.ReLU(inplace=True)
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        m = self.main(x)
        s = self.skip(x)
        # Align lengths if even kernel/stride produced an off-by-one.
        if m.shape[-1] != s.shape[-1]:
            n = min(m.shape[-1], s.shape[-1])
            m, s = m[..., :n], s[..., :n]
        return self.drop(self.act(m + s))


class ECGResNetDeep1D(nn.Module):
    """Deeper Ribeiro-style residual net for high-resolution (500 Hz/4096) ECG.

    ~4 residual units, channels 64→128→196→256→320, each downsampling ×4.
    Length-agnostic (AdaptiveAvgPool head), so the same weights serve any input
    length. Heavier than ``ECGResNet1D`` (~few M params) — train on GPU/MPS.
    """

    def __init__(
        self,
        num_classes: int = 5,
        length: int = 4096,
        in_channels: int = 12,
        channels: tuple[int, ...] = (128, 196, 256, 320),
        kernel: int = 17,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.length = length
        self.in_channels = in_channels
        self.stem = nn.Sequential(
            nn.Conv1d(in_channels, 64, kernel_size=kernel, padding=kernel // 2),
            nn.BatchNorm1d(64),
            nn.ReLU(inplace=True),
        )
        units = []
        prev = 64
        for ch in channels:
            units.append(_ResidualUnit1D(prev, ch, kernel=kernel, downsample=4, dropout=dropout))
            prev = ch
        self.blocks = nn.Sequential(*units)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Linear(prev, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.stem(x)
        x = self.blocks(x)
        x = self.pool(x).flatten(1)
        x = self.dropout(x)
        return self.head(x)


def build_default_model(num_classes: int = 3, length: int = 1024, in_channels: int = 1) -> nn.Module:
    """Construct the default classifier; switch architectures here in the future."""
    return ECGResNet1D(num_classes=num_classes, length=length, in_channels=in_channels)


def build_model(arch: str = "resnet", **kwargs) -> nn.Module:
    """Factory: ``resnet`` (default, serving) or ``deep`` (Ribeiro-style)."""
    if arch in ("deep", "ribeiro", "resnet_deep"):
        return ECGResNetDeep1D(**kwargs)
    return ECGResNet1D(**kwargs)


def default_model_version() -> str:
    return "ecg-resnet1d-0.1.0-untrained"
