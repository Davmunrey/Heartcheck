"""Evaluate a 12-lead PTB-XL diagnostic multi-label checkpoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from heartscan_ml.cnn1d import ECGResNet1D
from ml.training.data import PTBXL_DIAGNOSTIC_CLASSES, PTBXLDiagnosticDataset
from ml.training.train_multilabel import _multilabel_report


def evaluate(
    *,
    manifest: str,
    checkpoint: str,
    split: str = "test",
    batch_size: int = 64,
    workers: int = 2,
    threshold: float = 0.5,
    thresholds: list[float] | None = None,
    use_checkpoint_thresholds: bool = True,
) -> dict:
    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "mps"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()
        else "cpu"
    )
    state = torch.load(checkpoint, map_location=device, weights_only=True)
    classes = list(state.get("classes", PTBXL_DIAGNOSTIC_CLASSES)) if isinstance(state, dict) else list(PTBXL_DIAGNOSTIC_CLASSES)
    if tuple(classes) != PTBXL_DIAGNOSTIC_CLASSES:
        raise RuntimeError(f"Unsupported class order: {classes}")
    target_len = int(state.get("target_len", 1024)) if isinstance(state, dict) else 1024
    target_fs = int(state.get("target_fs", 100)) if isinstance(state, dict) else 100

    ds = PTBXLDiagnosticDataset(manifest, split=split, target_len=target_len, target_fs=target_fs)
    if not ds.rows:
        raise RuntimeError(f"Split {split!r} is empty.")

    model = ECGResNet1D(num_classes=len(PTBXL_DIAGNOSTIC_CLASSES), length=target_len, in_channels=12).to(device)
    payload = state.get("state_dict") if isinstance(state, dict) else state
    model.load_state_dict(payload, strict=True)
    model.eval()

    logits_buf = []
    labels_buf = []
    loader = DataLoader(ds, batch_size=batch_size, num_workers=workers)
    with torch.no_grad():
        for x, y in loader:
            logits_buf.append(model(x.to(device)).cpu().numpy())
            labels_buf.append(y.numpy())
    logits = np.concatenate(logits_buf)
    labels = np.concatenate(labels_buf)
    probs = 1.0 / (1.0 + np.exp(-logits))
    effective_threshold = threshold
    if thresholds is not None:
        effective_threshold = thresholds
    elif use_checkpoint_thresholds and isinstance(state, dict) and state.get("thresholds"):
        effective_threshold = list(state["thresholds"])
    report = _multilabel_report(labels, probs, effective_threshold)
    report.update(
        {
            "manifest": manifest,
            "checkpoint": checkpoint,
            "split": split,
            "n": int(len(labels)),
            "device": str(device),
        }
    )
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Evaluate 12-lead PTB-XL diagnostic multi-label checkpoint")
    p.add_argument("--manifest", required=True)
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--split", default="test")
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--thresholds-json", default=None, help="JSON file with a thresholds list")
    p.add_argument("--ignore-checkpoint-thresholds", action="store_true")
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    thresholds = None
    if args.thresholds_json:
        payload = json.loads(Path(args.thresholds_json).read_text(encoding="utf-8"))
        thresholds = payload.get("thresholds") or payload.get("tuned_thresholds") or payload
    report = evaluate(
        manifest=args.manifest,
        checkpoint=args.checkpoint,
        split=args.split,
        batch_size=args.batch_size,
        workers=args.workers,
        threshold=args.threshold,
        thresholds=thresholds,
        use_checkpoint_thresholds=not args.ignore_checkpoint_thresholds,
    )
    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
