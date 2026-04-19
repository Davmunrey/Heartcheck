from __future__ import annotations

import torch
import torch.nn as nn


class ConvBlock(nn.Module):
    def __init__(self, c_in: int, c_out: int, k: int = 7, s: int = 1) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(c_in, c_out, k, stride=s, padding=k // 2, bias=False),
            nn.BatchNorm1d(c_out),
            nn.ReLU(inplace=True),
            nn.Dropout(0.1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class CNN1D12Lead(nn.Module):
    """12-lead ECG → 3-class logits (normal / arrhythmia / noise)."""

    def __init__(self, seq_len: int = 1000, num_classes: int = 3, base: int = 32) -> None:
        super().__init__()
        self.stem = ConvBlock(12, base)
        self.down1 = nn.Sequential(ConvBlock(base, base * 2, k=5, s=2), ConvBlock(base * 2, base * 2))
        self.down2 = nn.Sequential(ConvBlock(base * 2, base * 4, k=5, s=2), ConvBlock(base * 4, base * 4))
        self.down3 = nn.Sequential(ConvBlock(base * 4, base * 8, k=5, s=2), ConvBlock(base * 8, base * 8))
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.head = nn.Linear(base * 8, num_classes)
        self._seq_len = seq_len

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, 12, T)
        x = self.stem(x)
        x = self.down1(x)
        x = self.down2(x)
        x = self.down3(x)
        x = self.pool(x).squeeze(-1)
        return self.head(x)


def count_parameters(m: nn.Module) -> int:
    return sum(p.numel() for p in m.parameters() if p.requires_grad)
