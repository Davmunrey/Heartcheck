"""Pretrain ``ECGResNet1D`` on a Parquet manifest of 12-lead ECGs.

Inputs
------

A manifest produced by ``ml.datasets.cli manifest`` and split by
``ml.datasets.splits`` (so it carries a ``split`` column).

Outputs
-------

- ``out_dir/checkpoint.pt`` — torch ``state_dict`` saved with
  ``weights_only`` -compatible payload (no pickled classes besides tensors).
- ``out_dir/training_log.jsonl`` — one JSON line per epoch with loss/F1.
- ``out_dir/training_summary.json`` — final metrics and config snapshot.

The manifest emitter (``ml.training.write_manifest``) is invoked separately
so that calibration metrics (``T8``) can be folded in before the YAML lands
next to the checkpoint.
"""

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
from torch.utils.data import DataLoader, WeightedRandomSampler

# Reuse the production model so the checkpoint loads back without surprises.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.ml.cnn1d import ECGResNet1D, default_model_version  # noqa: E402

from ml.training.data import CLASS_NAMES, ParquetECGDataset  # noqa: E402


@dataclass
class TrainConfig:
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
    sample_balanced: bool = True


def _balanced_sampler(ds: ParquetECGDataset) -> WeightedRandomSampler:
    counts = Counter(int(r.label_id) for r in ds.rows)
    weights = [1.0 / counts[int(r.label_id)] for r in ds.rows]
    return WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)


def _macro_f1(true: np.ndarray, pred: np.ndarray, n_classes: int) -> float:
    f1s = []
    for c in range(n_classes):
        tp = int(((pred == c) & (true == c)).sum())
        fp = int(((pred == c) & (true != c)).sum())
        fn = int(((pred != c) & (true == c)).sum())
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if (prec + rec) else 0.0)
    return float(np.mean(f1s))


def run(cfg: TrainConfig) -> dict:
    torch.manual_seed(cfg.seed)
    np.random.seed(cfg.seed)

    out_dir = Path(cfg.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train_ds = ParquetECGDataset(cfg.manifest, split="train", target_len=cfg.target_len, target_fs=cfg.target_fs)
    val_ds = ParquetECGDataset(cfg.manifest, split="val", target_len=cfg.target_len, target_fs=cfg.target_fs)
    if not train_ds.rows:
        raise RuntimeError("Train split is empty; check the manifest.")

    sampler = _balanced_sampler(train_ds) if cfg.sample_balanced else None
    train_loader = DataLoader(
        train_ds,
        batch_size=cfg.batch_size,
        sampler=sampler,
        shuffle=sampler is None,
        num_workers=cfg.num_workers,
    )
    val_loader = DataLoader(val_ds, batch_size=cfg.batch_size, num_workers=cfg.num_workers)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = ECGResNet1D(num_classes=len(CLASS_NAMES), length=cfg.target_len).to(device)
    optim = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    loss_fn = torch.nn.CrossEntropyLoss()

    log_path = out_dir / "training_log.jsonl"
    log_f = log_path.open("w", encoding="utf-8")
    best_f1 = -1.0
    val_logits_buf: np.ndarray | None = None
    val_labels_buf: np.ndarray | None = None

    for epoch in range(1, cfg.epochs + 1):
        model.train()
        t0 = time.perf_counter()
        losses = []
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optim.zero_grad()
            logits = model(x)
            loss = loss_fn(logits, y)
            loss.backward()
            optim.step()
            losses.append(float(loss.item()))

        model.eval()
        all_logits = []
        all_y = []
        with torch.no_grad():
            for x, y in val_loader:
                logits = model(x.to(device)).cpu().numpy()
                all_logits.append(logits)
                all_y.append(y.numpy())
        val_logits = np.concatenate(all_logits) if all_logits else np.zeros((0, len(CLASS_NAMES)))
        val_y = np.concatenate(all_y) if all_y else np.zeros(0, dtype=np.int64)
        if len(val_y):
            preds = val_logits.argmax(axis=1)
            f1 = _macro_f1(val_y, preds, len(CLASS_NAMES))
            acc = float((preds == val_y).mean())
        else:
            f1, acc = 0.0, 0.0

        elapsed = time.perf_counter() - t0
        rec = {
            "epoch": epoch,
            "train_loss": float(np.mean(losses)) if losses else 0.0,
            "val_f1_macro": f1,
            "val_accuracy": acc,
            "seconds": round(elapsed, 2),
        }
        log_f.write(json.dumps(rec) + "\n")
        log_f.flush()
        print(f"[epoch {epoch:>3}] loss={rec['train_loss']:.4f} val_f1={f1:.4f} val_acc={acc:.4f} ({elapsed:.0f}s)")

        if f1 > best_f1:
            best_f1 = f1
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "version": default_model_version().replace("-untrained", "-trained"),
                },
                out_dir / "checkpoint.pt",
            )
            val_logits_buf = val_logits
            val_labels_buf = val_y

    log_f.close()
    summary = {
        "config": asdict(cfg),
        "best_val_f1_macro": best_f1,
        "n_train": len(train_ds),
        "n_val": len(val_ds),
        "device": str(device),
    }
    if val_logits_buf is not None:
        np.savez(out_dir / "val_logits.npz", logits=val_logits_buf, labels=val_labels_buf)
        summary["val_logits_path"] = "val_logits.npz"
    (out_dir / "training_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"[done] best val F1 macro = {best_f1:.4f}; checkpoint at {out_dir / 'checkpoint.pt'}")
    return summary


def _parse() -> TrainConfig:
    p = argparse.ArgumentParser(description="Pretrain ECGResNet1D")
    p.add_argument("--manifest", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--workers", type=int, default=2)
    args = p.parse_args()
    return TrainConfig(
        manifest=args.manifest,
        out_dir=args.out,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        num_workers=args.workers,
    )


def main() -> None:
    run(_parse())


if __name__ == "__main__":  # pragma: no cover
    main()
