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
    loss: str = "bce"
    focal_gamma: float = 2.0
    threshold_metric: str = "f1"
    monitor: str = "tuned_macro_f1"
    augment: bool = True
    init_checkpoint: str | None = None


def _pos_weight(ds: PTBXLDiagnosticDataset, device: torch.device) -> torch.Tensor:
    targets = np.stack(ds.targets)
    pos = targets.sum(axis=0)
    neg = len(targets) - pos
    weight = neg / np.maximum(pos, 1.0)
    weight = np.clip(weight, 1.0, 20.0).astype(np.float32)
    return torch.tensor(weight, dtype=torch.float32, device=device)


def _threshold_array(threshold: float | list[float] | np.ndarray) -> np.ndarray:
    if isinstance(threshold, (list, tuple, np.ndarray)):
        arr = np.asarray(threshold, dtype=np.float32)
        if arr.shape != (len(PTBXL_DIAGNOSTIC_CLASSES),):
            raise ValueError(f"thresholds must have {len(PTBXL_DIAGNOSTIC_CLASSES)} values")
        return arr
    return np.full(len(PTBXL_DIAGNOSTIC_CLASSES), float(threshold), dtype=np.float32)


def _multilabel_report(y_true: np.ndarray, probs: np.ndarray, threshold: float | list[float] | np.ndarray) -> dict:
    thresholds = _threshold_array(threshold)
    pred = probs >= thresholds[np.newaxis, :]
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
        "threshold": thresholds.tolist(),
        "macro_f1": float(np.mean(f1s)) if f1s else 0.0,
        "macro_precision": float(np.mean(precisions)) if precisions else 0.0,
        "macro_recall": float(np.mean(recalls)) if recalls else 0.0,
        "exact_match": exact_match,
        "hamming_accuracy": hamming_accuracy,
        "classes": list(PTBXL_DIAGNOSTIC_CLASSES),
        "per_class": per_class,
    }


def tune_thresholds(
    y_true: np.ndarray,
    probs: np.ndarray,
    *,
    metric: str = "f1",
    min_threshold: float = 0.05,
    max_threshold: float = 0.95,
    steps: int = 19,
) -> list[float]:
    """Tune one threshold per label on validation data."""
    grid = np.linspace(min_threshold, max_threshold, steps)
    thresholds = []
    for idx in range(y_true.shape[1]):
        yt = y_true[:, idx].astype(bool)
        best = (0.5, -1.0)
        for thr in grid:
            yp = probs[:, idx] >= thr
            tp = int((yt & yp).sum())
            fp = int((~yt & yp).sum())
            fn = int((yt & ~yp).sum())
            precision = tp / (tp + fp) if (tp + fp) else 0.0
            recall = tp / (tp + fn) if (tp + fn) else 0.0
            if metric == "recall":
                score = recall - 0.01 * fp
            else:
                score = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
            if score > best[1]:
                best = (float(thr), float(score))
        thresholds.append(best[0])
    return thresholds


class FocalBCEWithLogitsLoss(torch.nn.Module):
    def __init__(self, pos_weight: torch.Tensor | None = None, gamma: float = 2.0) -> None:
        super().__init__()
        self.pos_weight = pos_weight
        self.gamma = gamma

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        bce = torch.nn.functional.binary_cross_entropy_with_logits(
            logits,
            targets,
            pos_weight=self.pos_weight,
            reduction="none",
        )
        probs = torch.sigmoid(logits)
        pt = torch.where(targets > 0, probs, 1 - probs)
        return (bce * (1 - pt).pow(self.gamma)).mean()


def _select_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


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

    train_ds = PTBXLDiagnosticDataset(
        cfg.manifest,
        split="train",
        target_len=cfg.target_len,
        target_fs=cfg.target_fs,
        augment=cfg.augment,
        seed=cfg.seed,
    )
    val_ds = PTBXLDiagnosticDataset(cfg.manifest, split="val", target_len=cfg.target_len, target_fs=cfg.target_fs)
    if not train_ds.rows or not val_ds.rows:
        raise RuntimeError("Train/val split empty; need PTB-XL diagnostic metadata.")

    train_loader = DataLoader(train_ds, batch_size=cfg.batch_size, shuffle=True, num_workers=cfg.num_workers)
    val_loader = DataLoader(val_ds, batch_size=cfg.batch_size, num_workers=cfg.num_workers)
    device = _select_device()
    model = ECGResNet1D(
        num_classes=len(PTBXL_DIAGNOSTIC_CLASSES),
        length=cfg.target_len,
        in_channels=12,
    ).to(device)
    if cfg.init_checkpoint:
        state = torch.load(cfg.init_checkpoint, map_location=device, weights_only=True)
        classes = list(state.get("classes", PTBXL_DIAGNOSTIC_CLASSES)) if isinstance(state, dict) else list(PTBXL_DIAGNOSTIC_CLASSES)
        if tuple(classes) != PTBXL_DIAGNOSTIC_CLASSES:
            raise RuntimeError(f"Unsupported init checkpoint class order: {classes}")
        payload = state.get("state_dict") if isinstance(state, dict) else state
        model.load_state_dict(payload, strict=True)
    optim = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optim, T_max=cfg.epochs)
    pos_weight = _pos_weight(train_ds, device)
    if cfg.loss == "focal":
        loss_fn = FocalBCEWithLogitsLoss(pos_weight=pos_weight, gamma=cfg.focal_gamma)
    else:
        loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    log_f = (out_dir / "training_log.jsonl").open("w", encoding="utf-8")
    best_score = -1.0
    best_report: dict | None = None
    best_tuned_report: dict | None = None
    best_thresholds: list[float] | None = None
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
        probs = 1.0 / (1.0 + np.exp(-logits))
        tuned_thresholds = tune_thresholds(labels, probs, metric=cfg.threshold_metric)
        tuned_report = _multilabel_report(labels, probs, tuned_thresholds)
        score = tuned_report["macro_f1"] if cfg.monitor == "tuned_macro_f1" else report["macro_f1"]
        rec = {
            "epoch": epoch,
            "train_loss": float(np.mean(losses)) if losses else 0.0,
            "val_macro_f1": report["macro_f1"],
            "val_tuned_macro_f1": tuned_report["macro_f1"],
            "val_exact_match": report["exact_match"],
            "val_tuned_exact_match": tuned_report["exact_match"],
            "val_hamming_accuracy": report["hamming_accuracy"],
            "val_tuned_hamming_accuracy": tuned_report["hamming_accuracy"],
            "monitor_score": score,
            "seconds": round(time.perf_counter() - t0, 2),
            "lr": float(scheduler.get_last_lr()[0]),
        }
        log_f.write(json.dumps(rec) + "\n")
        log_f.flush()
        print(
            f"[epoch {epoch:>3}] loss={rec['train_loss']:.4f} "
            f"val_f1={rec['val_macro_f1']:.4f} tuned_f1={rec['val_tuned_macro_f1']:.4f} "
            f"exact={rec['val_tuned_exact_match']:.4f} "
            f"hamming={rec['val_hamming_accuracy']:.4f} ({rec['seconds']:.0f}s)"
        )
        if score > best_score:
            best_score = score
            best_report = report
            best_logits = logits
            best_labels = labels
            best_thresholds = tuned_thresholds
            best_tuned_report = tuned_report
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "version": "ecg-resnet1d-ptbxl-multilabel-0.1.0",
                    "classes": list(PTBXL_DIAGNOSTIC_CLASSES),
                    "task": "ptbxl_diagnostic_multilabel",
                    "threshold": cfg.threshold,
                    "thresholds": best_thresholds,
                    "target_len": cfg.target_len,
                    "target_fs": cfg.target_fs,
                    "in_channels": 12,
                    "loss": cfg.loss,
                    "threshold_metric": cfg.threshold_metric,
                    "monitor": cfg.monitor,
                    "augment": cfg.augment,
                    "init_checkpoint": cfg.init_checkpoint,
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
        "best_val_score": best_score,
        "monitor": cfg.monitor,
        "validation": best_report,
        "tuned_thresholds": best_thresholds,
        "validation_tuned": best_tuned_report,
    }
    if best_logits is not None and best_labels is not None:
        np.savez(out_dir / "val_logits.npz", logits=best_logits, labels=best_labels)
    (out_dir / "training_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[done] best val {cfg.monitor} = {best_score:.4f}; checkpoint at {out_dir / 'checkpoint.pt'}")
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
    p.add_argument("--loss", choices=["bce", "focal"], default="bce")
    p.add_argument("--focal-gamma", type=float, default=2.0)
    p.add_argument("--threshold-metric", choices=["f1", "recall"], default="f1")
    p.add_argument("--monitor", choices=["macro_f1", "tuned_macro_f1"], default="tuned_macro_f1")
    p.add_argument("--no-augment", action="store_true")
    p.add_argument("--init-checkpoint", default=None)
    p.add_argument("--target-fs", type=int, default=100, help="resample rate; use 500 with records500 for finer morphology")
    p.add_argument("--target-len", type=int, default=1024, help="samples per lead fed to the model")
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
            loss=args.loss,
            focal_gamma=args.focal_gamma,
            threshold_metric=args.threshold_metric,
            monitor=args.monitor,
            augment=not args.no_augment,
            init_checkpoint=args.init_checkpoint,
            target_len=args.target_len,
            target_fs=args.target_fs,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
