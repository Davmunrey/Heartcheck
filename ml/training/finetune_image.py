"""Fine-tune the pretrained ``ECGResNet1D`` on ECG **images** by routing each
image through HeartScan's own extraction pipeline.

This closes the foto↔señal gap: instead of training on clean PTB-XL signals
and hoping the production extractor doesn't introduce distribution shift,
we feed the model the same noisy 1D signal it will see at inference time.

Manifest expected
-----------------

A Parquet manifest with at least:

- ``file_path`` pointing to a PNG/JPEG image file.
- ``label_id`` in ``{0, 1, 2}``.
- ``split`` in ``{train, val, test}``.

Both ``ecg_image_database`` and ``ptb_xl_image_17k`` produce manifests of
this shape via ``ml.datasets.cli manifest``.
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
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

# Production-side imports (analysis pipeline + model).
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.ml.cnn1d import ECGResNet1D, default_model_version  # noqa: E402
from app.services import (  # noqa: E402
    grid_suppression,
    photo_geometry,
    preprocess as svc_preprocess,
    trace_extract,
)


CLASS_NAMES = ("normal", "arrhythmia", "noise")


@dataclass
class FinetuneConfig:
    manifest: str
    out_dir: str
    pretrained: str | None = None
    epochs: int = 3
    batch_size: int = 32
    lr: float = 5e-4
    weight_decay: float = 1e-4
    target_len: int = 1024
    seed: int = 1234
    num_workers: int = 2
    sample_balanced: bool = True


class HeartScanImageDataset(Dataset):
    """Reads images from disk and runs them through the production extractor."""

    def __init__(self, manifest_path: str | Path, split: str | None = None, target_len: int = 1024) -> None:
        try:
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise RuntimeError("pyarrow required: pip install pyarrow") from exc
        rows = pq.read_table(manifest_path).to_pylist()
        if split:
            rows = [r for r in rows if r.get("split") == split]
        self.rows = rows
        self.target_len = target_len

    def __len__(self) -> int:
        return len(self.rows)

    def _image_to_signal(self, path: Path) -> np.ndarray:
        try:
            data = path.read_bytes()
            gray = svc_preprocess.decode_image_to_gray(data)
            rect = photo_geometry.correct_perspective(gray)
            strip, _ = photo_geometry.dominant_strip(rect.image)
            grid = photo_geometry.estimate_grid_pitch(strip)
            binary = (
                grid_suppression.suppress_grid_v2(strip, calibration=grid)
                if grid_suppression.active_variant() == "v2"
                else grid_suppression.suppress_grid(strip)
            )
            _, y_signal = trace_extract.extract_trace_1d(binary)
            sig = trace_extract.resample_signal(y_signal, target_len=self.target_len)
            return sig
        except Exception:
            return np.zeros(self.target_len, dtype=np.float32)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        row = self.rows[idx]
        sig = self._image_to_signal(Path(row["file_path"]))
        return (
            torch.from_numpy(sig).unsqueeze(0),
            torch.tensor(int(row["label_id"]), dtype=torch.long),
        )


def _balanced_sampler(ds: HeartScanImageDataset) -> WeightedRandomSampler:
    counts = Counter(int(r["label_id"]) for r in ds.rows)
    weights = [1.0 / counts[int(r["label_id"])] for r in ds.rows]
    return WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)


def _macro_f1(true: np.ndarray, pred: np.ndarray, n: int) -> float:
    f1s = []
    for c in range(n):
        tp = int(((pred == c) & (true == c)).sum())
        fp = int(((pred == c) & (true != c)).sum())
        fn = int(((pred != c) & (true == c)).sum())
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if (prec + rec) else 0.0)
    return float(np.mean(f1s))


def run(cfg: FinetuneConfig) -> dict:
    torch.manual_seed(cfg.seed)
    out_dir = Path(cfg.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train_ds = HeartScanImageDataset(cfg.manifest, split="train", target_len=cfg.target_len)
    val_ds = HeartScanImageDataset(cfg.manifest, split="val", target_len=cfg.target_len)
    if not train_ds.rows:
        raise RuntimeError("Train split is empty")

    sampler = _balanced_sampler(train_ds) if cfg.sample_balanced else None
    train_loader = DataLoader(train_ds, batch_size=cfg.batch_size, sampler=sampler,
                              shuffle=sampler is None, num_workers=cfg.num_workers)
    val_loader = DataLoader(val_ds, batch_size=cfg.batch_size, num_workers=cfg.num_workers)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = ECGResNet1D(num_classes=len(CLASS_NAMES), length=cfg.target_len).to(device)
    if cfg.pretrained:
        state = torch.load(cfg.pretrained, map_location=device, weights_only=True)
        payload = state["state_dict"] if isinstance(state, dict) and "state_dict" in state else state
        model.load_state_dict(payload, strict=False)
    optim = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    loss_fn = torch.nn.CrossEntropyLoss()

    log_path = out_dir / "finetune_log.jsonl"
    log_f = log_path.open("w", encoding="utf-8")
    best_f1 = -1.0
    val_logits_buf: np.ndarray | None = None
    val_labels_buf: np.ndarray | None = None

    for epoch in range(1, cfg.epochs + 1):
        model.train()
        losses = []
        t0 = time.perf_counter()
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optim.zero_grad()
            logits = model(x)
            loss = loss_fn(logits, y)
            loss.backward()
            optim.step()
            losses.append(float(loss.item()))

        model.eval()
        all_logits, all_y = [], []
        with torch.no_grad():
            for x, y in val_loader:
                logits = model(x.to(device)).cpu().numpy()
                all_logits.append(logits)
                all_y.append(y.numpy())
        val_logits = np.concatenate(all_logits) if all_logits else np.zeros((0, len(CLASS_NAMES)))
        val_y = np.concatenate(all_y) if all_y else np.zeros(0, dtype=np.int64)
        f1 = _macro_f1(val_y, val_logits.argmax(axis=1), len(CLASS_NAMES)) if len(val_y) else 0.0
        elapsed = time.perf_counter() - t0
        rec = {"epoch": epoch, "train_loss": float(np.mean(losses)) if losses else 0.0,
               "val_f1_macro": f1, "seconds": round(elapsed, 2)}
        log_f.write(json.dumps(rec) + "\n")
        log_f.flush()
        print(f"[ft epoch {epoch:>3}] loss={rec['train_loss']:.4f} val_f1={f1:.4f} ({elapsed:.0f}s)")

        if f1 > best_f1:
            best_f1 = f1
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "version": default_model_version().replace("-untrained", "-image-tuned"),
                },
                out_dir / "checkpoint.pt",
            )
            val_logits_buf, val_labels_buf = val_logits, val_y

    log_f.close()
    summary = {"config": asdict(cfg), "best_val_f1_macro": best_f1, "device": str(device)}
    if val_logits_buf is not None:
        np.savez(out_dir / "val_logits.npz", logits=val_logits_buf, labels=val_labels_buf)
        summary["val_logits_path"] = "val_logits.npz"
    (out_dir / "finetune_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"[done] image fine-tune best F1 = {best_f1:.4f}")
    return summary


def _parse() -> FinetuneConfig:
    p = argparse.ArgumentParser(description="Fine-tune ECGResNet1D on ECG photos")
    p.add_argument("--manifest", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--pretrained", default=None, help="path to checkpoint.pt from pretrain step")
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr", type=float, default=5e-4)
    p.add_argument("--workers", type=int, default=2)
    args = p.parse_args()
    return FinetuneConfig(
        manifest=args.manifest,
        out_dir=args.out,
        pretrained=args.pretrained,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        num_workers=args.workers,
    )


if __name__ == "__main__":  # pragma: no cover
    run(_parse())
