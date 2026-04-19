from __future__ import annotations

import argparse
import json
import os
from collections import Counter

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from heartscan_ml import MODEL_FAMILY, PIPELINE_VERSION
from heartscan_ml.config import TrainConfig
from heartscan_ml.dataset_ptbxl import PTBXLScreeningDataset
from heartscan_ml.labels import parse_scp_codes, ptbxl_to_screening_class
from heartscan_ml.model_cnn1d import CNN1D12Lead, count_parameters


def compute_class_weights(cfg: TrainConfig) -> torch.Tensor:
    csv_path = os.path.join(cfg.ptbxl_dir, "ptbxl_database.csv")
    df = pd.read_csv(csv_path)
    df = df[df["strat_fold"].isin(cfg.train_folds)]
    ys = [ptbxl_to_screening_class(parse_scp_codes(x)) for x in df["scp_codes"]]
    cnt = Counter(ys)
    cnt[2] += int(len(ys) * cfg.noise_prob)
    w = torch.tensor([1.0 / max(cnt.get(i, 1), 1) for i in range(3)], dtype=torch.float32)
    return w * (3.0 / w.sum())


def main() -> None:
    p = argparse.ArgumentParser(description="Train CNN1D on PTB-XL screening labels.")
    p.add_argument("--ptbxl-dir", default=os.environ.get("PTBXL_DIR", ""))
    p.add_argument("--epochs", type=int, default=20)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--checkpoint-dir", default="checkpoints")
    args = p.parse_args()

    if not args.ptbxl_dir:
        raise SystemExit("Set --ptbxl-dir or PTBXL_DIR to your PTB-XL root (contains ptbxl_database.csv).")

    cfg = TrainConfig(
        ptbxl_dir=args.ptbxl_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        device=args.device,
        checkpoint_dir=args.checkpoint_dir,
    )

    torch.manual_seed(cfg.seed)
    rng = np.random.default_rng(cfg.seed)

    train_ds = PTBXLScreeningDataset(cfg, cfg.train_folds, augment_noise=True, rng=rng)
    val_ds = PTBXLScreeningDataset(cfg, (cfg.val_fold,), augment_noise=False, rng=rng)

    train_loader = DataLoader(
        train_ds,
        batch_size=cfg.batch_size,
        shuffle=True,
        num_workers=cfg.num_workers,
    )
    val_loader = DataLoader(val_ds, batch_size=cfg.batch_size, shuffle=False, num_workers=cfg.num_workers)

    device = torch.device(cfg.device)
    model = CNN1D12Lead(seq_len=cfg.crop_len, num_classes=3).to(device)
    weights = compute_class_weights(cfg).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    criterion = nn.CrossEntropyLoss(weight=weights)

    os.makedirs(cfg.checkpoint_dir, exist_ok=True)
    best_val = float("inf")
    meta = {
        "pipeline_version": PIPELINE_VERSION,
        "model_family": MODEL_FAMILY,
        "train_config": cfg.__dict__,
    }

    for epoch in range(cfg.epochs):
        model.train()
        loss_tr = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            opt.step()
            loss_tr += loss.item() * xb.size(0)
        loss_tr /= len(train_ds)

        model.eval()
        loss_va = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                logits = model(xb)
                loss_va += nn.functional.cross_entropy(logits, yb, weight=weights).item() * xb.size(0)
                pred = logits.argmax(dim=1)
                correct += (pred == yb).sum().item()
                total += yb.size(0)
        loss_va /= len(val_ds)
        acc = correct / max(total, 1)
        print(f"epoch {epoch+1}/{cfg.epochs}  train_loss={loss_tr:.4f}  val_loss={loss_va:.4f}  val_acc={acc:.4f}")

        if loss_va < best_val:
            best_val = loss_va
            ckpt_path = os.path.join(cfg.checkpoint_dir, "cnn1d_best.pt")
            torch.save(
                {
                    "model_state": model.state_dict(),
                    "meta": meta,
                    "val_loss": loss_va,
                    "val_acc": acc,
                    "params": count_parameters(model),
                },
                ckpt_path,
            )
            with open(os.path.join(cfg.checkpoint_dir, "run_meta.json"), "w", encoding="utf-8") as f:
                json.dump({**meta, "val_loss": loss_va, "val_acc": acc, "epochs_trained": epoch + 1}, f, indent=2)
            print(f"  saved {ckpt_path}")


if __name__ == "__main__":
    main()
