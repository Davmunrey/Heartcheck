#!/usr/bin/env python3
"""
Train ECGCNN1D on MIT-BIH style NPZ exports (project-specific).

This script is a scaffold: plug in wfdb loading from PhysioNet MIT-BIH Arrhythmia Database
and map labels to {normal, arrhythmia, noise}.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

# Run from backend root: python scripts/train_cnn1d.py
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.cnn1d import ECGCNN1D  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("weights/ecg_cnn1d.pt"))
    p.add_argument("--epochs", type=int, default=3)
    args = p.parse_args()

    # Synthetic dummy data for pipeline smoke only — replace with real MIT-BIH windows.
    n, l, c = 64, 1024, 3
    x = torch.randn(n, 1, l)
    y = torch.randint(0, c, (n,))
    ds = TensorDataset(x, y)
    dl = DataLoader(ds, batch_size=16, shuffle=True)

    model = ECGCNN1D(num_classes=c, length=l)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.CrossEntropyLoss()

    for _ in range(args.epochs):
        for xb, yb in dl:
            opt.zero_grad()
            logits = model(xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            opt.step()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"state_dict": model.state_dict(), "version": "cnn1d-train-scaffold-0.1"},
        args.out,
    )
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
