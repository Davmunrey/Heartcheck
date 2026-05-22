"""Train a 12-lead multi-label PTB-XL diagnostic superclass model."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from heartscan_ml.cnn1d import ECGResNet1D
from ml.training.data import PTBXL_DIAGNOSTIC_CLASSES, PTBXLDiagnosticDataset


@dataclass
class MultiLabelTrainConfig:
    manifest: str
    out_dir: str
    epochs: int = 5
    batch_size: int = 64
    lr: float = 1e-3
    weight_decay: float = 1e-4
    target_len: int = 1024
    target_fs: int = 100
    seed: int = 1234
    num_workers: int = 2
    threshold: float = 0.5


def _pos_weight(ds: PTBXLDiagnosticDataset, device: torch.device) -> torch.Tensor:
    targets = np.stack(ds.targets)
    pos = targets.sum(axis=0)
    neg = len(targets) - pos
    weight = neg / np.maximum(pos, 1.0)
    weight = np.clip(weight, 1.0, 20.0).astype(np.float32)
    return torch.tensor(weight, dtype=torch.float32, device=device)


def _multilabel_report(y_true: np.ndarray, probs: np.ndarray, threshold: float) -> dict:
    pred = probs >= threshold
    per_class = {}
    f1s = []
    recalls = []
    precisions = []
    for idx, name in enumerate(PTBXL_DIAGNOSTIC_CLASSES):
        yt = y_true[:, idx].astype(bool)
        yp = pred[:, idx]
        tp = int((yt & yp).sum())
        fp = int((~yt & yp).sum())
        fn = int((yt & ~yp).sum())
        support = int(yt.sum())
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        per_class[name] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
        f1s.append(f1)
        recalls.append(recall)
        precisions.append(precision)
    exact_match = float((pred == y_true.astype(bool)).all(axis=1).mean()) if len(y_true) else 0.0
    hamming_accuracy = float((pred == y_true.astype(bool)).mean()) if len(y_true) else 0.0
    return {
        "threshold": threshold,
        "macro_f1": float(np.mean(f1s)) if f1s else 0.0,
        "macro_precision": float(np.mean(precisions)) if precisions else 0.0,
        "macro_recall": float(np.mean(recalls)) if recalls else 0.0,
        "exact_match": exact_match,
        "hamming_accuracy": hamming_accuracy,
        "classes": list(PTBXL_DIAGNOSTIC_CLASSES),
        "per_class": per_class,
    }


def _run_eval(model: torch.nn.Module, loader: DataLoader, device: torch.device, threshold: float) -> tuple[dict, np.ndarray, np.ndarray]:
    logits_buf = []
    labels_buf = []
    model.eval()
    with torch.no_grad():
        for x, y in loader:
            logits_buf.append(model(x.to(device)).cpu().numpy())
            labels_buf.append(y.numpy())
    logits = np.concatenate(logits_buf) if logits_buf else np.zeros((0, len(PTBXL_DIAGNOSTIC_CLASSES)))
    labels = np.concatenate(labels_buf) if labels_buf else np.zeros((0, len(PTBXL_DIAGNOSTIC_CLASSES)))
    probs = 1.0 / (1.0 + np.exp(-logits))
    return _multilabel_report(labels, probs, threshold), logits, labels


def run(cfg: MultiLabelTrainConfig) -> dict:
    torch.manual_seed(cfg.seed)
    np.random.seed(cfg.seed)
    out_dir = Path(cfg.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train_ds = PTBXLDiagnosticDataset(cfg.manifest, split="train", target_len=cfg.target_len, target_fs=cfg.target_fs)
    val_ds = PTBXLDiagnosticDataset(cfg.manifest, split="val", target_len=cfg.target_len, target_fs=cfg.target_fs)
    if not train_ds.rows or not val_ds.rows:
        raise RuntimeError("Train/val split empty; need PTB-XL diagnostic metadata.")

    train_loader = DataLoader(train_ds, batch_size=cfg.batch_size, shuffle=True, num_workers=cfg.num_workers)
    val_loader = DataLoader(val_ds, batch_size=cfg.batch_size, num_workers=cfg.num_workers)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = ECGResNet1D(
        num_classes=len(PTBXL_DIAGNOSTIC_CLASSES),
        length=cfg.target_len,
        in_channels=12,
    ).to(device)
    optim = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optim, T_max=cfg.epochs)
    loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=_pos_weight(train_ds, device))

    log_f = (out_dir / "training_log.jsonl").open("w", encoding="utf-8")
    best_f1 = -1.0
    best_report: dict | None = None
    best_logits: np.ndarray | None = None
    best_labels: np.ndarray | None = None

    for epoch in range(1, cfg.epochs + 1):
        model.train()
        t0 = time.perf_counter()
        losses = []
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optim.zero_grad()
            loss = loss_fn(model(x), y)
            loss.backward()
            optim.step()
            losses.append(float(loss.item()))
        report, logits, labels = _run_eval(model, val_loader, device, cfg.threshold)
        scheduler.step()
        rec = {
            "epoch": epoch,
            "train_loss": float(np.mean(losses)) if losses else 0.0,
            "val_macro_f1": report["macro_f1"],
            "val_exact_match": report["exact_match"],
            "val_hamming_accuracy": report["hamming_accuracy"],
            "seconds": round(time.perf_counter() - t0, 2),
            "lr": float(scheduler.get_last_lr()[0]),
        }
        log_f.write(json.dumps(rec) + "\n")
        log_f.flush()
        print(
            f"[epoch {epoch:>3}] loss={rec['train_loss']:.4f} "
            f"val_f1={rec['val_macro_f1']:.4f} exact={rec['val_exact_match']:.4f} "
            f"hamming={rec['val_hamming_accuracy']:.4f} ({rec['seconds']:.0f}s)"
        )
        if report["macro_f1"] > best_f1:
            best_f1 = report["macro_f1"]
            best_report = report
            best_logits = logits
            best_labels = labels
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "version": "ecg-resnet1d-ptbxl-multilabel-0.1.0",
                    "classes": list(PTBXL_DIAGNOSTIC_CLASSES),
                    "task": "ptbxl_diagnostic_multilabel",
                    "threshold": cfg.threshold,
                    "in_channels": 12,
                },
                out_dir / "checkpoint.pt",
            )
    log_f.close()
    combo_counts = Counter(",".join(PTBXL_DIAGNOSTIC_CLASSES[i] for i in np.where(t > 0)[0]) for t in train_ds.targets)
    summary = {
        "config": asdict(cfg),
        "classes": list(PTBXL_DIAGNOSTIC_CLASSES),
        "class_combo_counts_train": dict(combo_counts),
        "n_train": len(train_ds),
        "n_val": len(val_ds),
        "device": str(device),
        "best_val_macro_f1": best_f1,
        "validation": best_report,
    }
    if best_logits is not None and best_labels is not None:
        np.savez(out_dir / "val_logits.npz", logits=best_logits, labels=best_labels)
    (out_dir / "training_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[done] best val macro-F1 = {best_f1:.4f}; checkpoint at {out_dir / 'checkpoint.pt'}")
    return summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Train 12-lead PTB-XL diagnostic multi-label model")
    p.add_argument("--manifest", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--threshold", type=float, default=0.5)
    args = p.parse_args(argv)
    run(
        MultiLabelTrainConfig(
            manifest=args.manifest,
            out_dir=args.out,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
            num_workers=args.workers,
            threshold=args.threshold,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
