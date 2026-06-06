#!/usr/bin/env python3
"""Train a compact 2D CNN beat-image classifier (AAMI-style N/S/V/F/Q/M).

Input: a directory with train/<class>/*.png and test/<class>/*.png (the
MIT-BIH beat-image layout, e.g. ~/Downloads/ECG_Image_data). Pure torch + PIL
(no torchvision) so it adds no new API/CI dependency. Handles heavy class
imbalance via subsampling the majority class + class-weighted loss.

This is the image/beat wedge — distinct from the 12-lead diagnostic signal
model. It does NOT auto-promote; review metrics before wiring to the API.

Usage:
  apps/ml-api/.venv/bin/python scripts/train_beat_image.py \
    --data ~/Downloads/ECG_Image_data --out runs/local/beat_image --epochs 6
"""
from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader, Dataset

IMG = 128


def _device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class BeatImages(Dataset):
    def __init__(self, items: list[tuple[Path, int]]):
        self.items = items

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, i: int):
        path, label = self.items[i]
        im = Image.open(path).convert("L").resize((IMG, IMG))
        x = np.asarray(im, dtype=np.float32) / 255.0
        x = (x - 0.5) / 0.5
        return torch.from_numpy(x).unsqueeze(0), label


def _scan(root: Path, classes: list[str]) -> list[tuple[Path, int]]:
    items: list[tuple[Path, int]] = []
    for idx, c in enumerate(classes):
        for p in (root / c).glob("*.png"):
            items.append((p, idx))
    return items


def _subsample_majority(items, classes, cap: int, seed: int = 1234):
    rng = np.random.default_rng(seed)
    by_cls: dict[int, list] = {}
    for it in items:
        by_cls.setdefault(it[1], []).append(it)
    out = []
    for idx, lst in by_cls.items():
        if len(lst) > cap:
            sel = rng.choice(len(lst), size=cap, replace=False)
            out.extend(lst[i] for i in sel)
        else:
            out.extend(lst)
    rng.shuffle(out)
    return out


class SmallCNN(nn.Module):
    def __init__(self, n_classes: int):
        super().__init__()
        def block(i, o):
            return nn.Sequential(
                nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(),
                nn.Conv2d(o, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(),
                nn.MaxPool2d(2),
            )
        self.features = nn.Sequential(block(1, 16), block(16, 32), block(32, 64), block(64, 128))
        self.head = nn.Sequential(
            nn.AdaptiveAvgPool2d(1), nn.Flatten(),
            nn.Dropout(0.3), nn.Linear(128, n_classes),
        )

    def forward(self, x):
        return self.head(self.features(x))


def _evaluate(model, loader, device, n_classes):
    model.eval()
    cm = np.zeros((n_classes, n_classes), dtype=np.int64)
    with torch.no_grad():
        for x, y in loader:
            pred = model(x.to(device)).argmax(1).cpu().numpy()
            for t, p in zip(y.numpy(), pred):
                cm[t, p] += 1
    f1s = []
    per = {}
    for i in range(n_classes):
        tp = cm[i, i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        per[i] = {"precision": prec, "recall": rec, "f1": f1, "support": int(cm[i].sum())}
        f1s.append(f1)
    acc = float(np.trace(cm) / cm.sum()) if cm.sum() else 0.0
    return {"accuracy": acc, "macro_f1": float(np.mean(f1s)), "per_class": per}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--batch-size", type=int, default=128)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--majority-cap", type=int, default=8000)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=1234)
    args = ap.parse_args()

    root = Path(args.data).expanduser()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    classes = sorted(d.name for d in (root / "train").iterdir() if d.is_dir())
    device = _device()
    torch.manual_seed(args.seed)

    train_all = _scan(root / "train", classes)
    train_items = _subsample_majority(train_all, classes, args.majority_cap, args.seed)
    rng = np.random.default_rng(args.seed)
    rng.shuffle(train_items)
    n_val = max(1, int(0.1 * len(train_items)))
    val_items, tr_items = train_items[:n_val], train_items[n_val:]
    test_items = _scan(root / "test", classes)

    print(f"classes={classes} device={device}", flush=True)
    print(f"train={len(tr_items)} (capped from {len(train_all)}) val={len(val_items)} test={len(test_items)}", flush=True)
    print(f"train class dist: {dict(Counter(c for _, c in tr_items))}", flush=True)

    tr = DataLoader(BeatImages(tr_items), batch_size=args.batch_size, shuffle=True, num_workers=args.workers)
    va = DataLoader(BeatImages(val_items), batch_size=args.batch_size, num_workers=args.workers)
    te = DataLoader(BeatImages(test_items), batch_size=args.batch_size, num_workers=args.workers)

    counts = Counter(c for _, c in tr_items)
    weights = torch.tensor(
        [len(tr_items) / (len(classes) * max(1, counts.get(i, 0))) for i in range(len(classes))],
        dtype=torch.float32, device=device,
    )
    model = SmallCNN(len(classes)).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    loss_fn = nn.CrossEntropyLoss(weight=weights)

    best = -1.0
    for epoch in range(1, args.epochs + 1):
        model.train()
        t0 = time.perf_counter()
        losses = []
        for x, y in tr:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            loss = loss_fn(model(x), y)
            loss.backward()
            opt.step()
            losses.append(float(loss.item()))
        sched.step()
        rep = _evaluate(model, va, device, len(classes))
        dt = time.perf_counter() - t0
        print(f"[epoch {epoch}] loss={np.mean(losses):.4f} val_macro_f1={rep['macro_f1']:.4f} acc={rep['accuracy']:.4f} ({dt:.0f}s)", flush=True)
        if rep["macro_f1"] > best:
            best = rep["macro_f1"]
            torch.save({"state_dict": model.state_dict(), "classes": classes, "img": IMG,
                        "task": "beat_image_aami"}, out / "checkpoint.pt")

    test_rep = _evaluate(model, te, device, len(classes))
    test_rep["classes"] = classes
    (out / "eval_test.json").write_text(json.dumps(test_rep, indent=2))
    print(f"[done] best val macro-F1={best:.4f} | TEST macro-F1={test_rep['macro_f1']:.4f} acc={test_rep['accuracy']:.4f}", flush=True)
    for i, c in enumerate(classes):
        m = test_rep["per_class"][i]
        print(f"  {c}: f1={m['f1']:.3f} prec={m['precision']:.3f} rec={m['recall']:.3f} n={m['support']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
