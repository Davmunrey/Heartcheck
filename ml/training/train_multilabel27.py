"""Train the COMPLETE ECG model: 27-class rhythm+diagnostic multi-label head.

The 5-superclass model (NORM/MI/STTC/CD/HYP) discards rhythm — half of clinical
ECG reading. This trains the full CinC2020 27-class taxonomy (AF, flutter,
brady/tachy, ectopy, conduction, axis, intervals, ST/T, hypertrophy, MI) on the
PTB-XL + CinC2020 blend, ideally from the CODE-15 pretrained backbone.

Reuses the existing 27-capable dataset (PTBXLDiagnosticDataset with
classes=CINC2020_27_CLASSES, label_key="cinc2020_27") and the deep backbone, and
monitors macro-AUROC (threshold-independent — the honest metric).

Usage:
  apps/ml-api/.venv/bin/python -m ml.training.train_multilabel27 \
    --manifest runs/local/blend27/manifest_split.parquet --out runs/local/full27 \
    --init-backbone runs/local/code15_pretrain/backbone.pt \
    --epochs 15 --batch-size 64 --lr 3e-4 --workers 6
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from heartscan_ml.cnn1d import build_model
from ml.datasets.labels import CINC2020_27_CLASSES
from ml.training.data import PTBXLDiagnosticDataset
from ml.training.pretrain_code15 import _auroc
from ml.training.train_multilabel import FocalBCEWithLogitsLoss, _select_device, transfer_backbone

CLASSES = tuple(CINC2020_27_CLASSES)


def _pos_weight(ds, device):
    t = np.stack(ds.targets)
    pos = t.sum(0)
    w = np.clip((len(t) - pos) / np.maximum(pos, 1.0), 1.0, 50.0).astype(np.float32)
    return torch.tensor(w, device=device)


def _val_auroc(model, loader, device):
    model.eval()
    L, Y = [], []
    with torch.no_grad():
        for x, y in loader:
            L.append(model(x.to(device)).cpu().numpy())
            Y.append(y.numpy())
    P = 1 / (1 + np.exp(-np.concatenate(L)))
    Yc = np.concatenate(Y)
    per = {}
    aucs = []
    for i, c in enumerate(CLASSES):
        if Yc[:, i].min() == Yc[:, i].max():
            continue
        a = _auroc(Yc[:, i], P[:, i])
        per[c] = round(a, 3)
        aucs.append(a)
    return (float(np.mean(aucs)) if aucs else 0.0), per


def run(a: argparse.Namespace) -> int:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dev = _select_device()
    mk = lambda split, aug: PTBXLDiagnosticDataset(  # noqa: E731
        a.manifest, split=split, target_len=a.target_len, target_fs=a.target_fs,
        augment=aug, classes=CLASSES, label_key="cinc2020_27",
    )
    tr, va = mk("train", True), mk("val", False)
    print(f"[27c] train={len(tr.rows):,} val={len(va.rows):,} classes={len(CLASSES)}")
    tl = DataLoader(tr, batch_size=a.batch_size, shuffle=True, num_workers=a.workers)
    vl = DataLoader(va, batch_size=a.batch_size, num_workers=a.workers)

    model = build_model("deep", num_classes=len(CLASSES), length=a.target_len, in_channels=12).to(dev)
    if a.init_backbone and Path(a.init_backbone).is_file():
        st = torch.load(a.init_backbone, map_location=dev, weights_only=True)
        n, miss, unexp = transfer_backbone(model, st.get("state_dict", st))
        print(f"[27c] backbone: {n} tensors transferred (missing={miss}, unexpected={unexp})")

    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=a.epochs)
    loss_fn = FocalBCEWithLogitsLoss(pos_weight=_pos_weight(tr, dev))
    best = -1.0
    for ep in range(1, a.epochs + 1):
        model.train()
        t0 = time.perf_counter()
        losses = []
        for x, y in tl:
            x, y = x.to(dev), y.to(dev)
            opt.zero_grad()
            loss = loss_fn(model(x), y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            losses.append(float(loss.item()))
        sched.step()
        auroc, per = _val_auroc(model, vl, dev)
        print(f"[epoch {ep:>2}] loss={np.mean(losses):.4f} val_macro_auroc={auroc:.4f} ({time.perf_counter()-t0:.0f}s)")
        if auroc > best:
            best = auroc
            torch.save(
                {"state_dict": model.state_dict(), "arch": "deep", "classes": list(CLASSES),
                 "task": "ecg_27class", "target_len": a.target_len, "target_fs": a.target_fs,
                 "in_channels": 12, "val_macro_auroc": best, "per_class_auroc": per},
                out / "checkpoint.pt",
            )
    (out / "summary.json").write_text(json.dumps({"best_val_macro_auroc": best, "per_class": per}, indent=2))
    print(f"[done] best val macro-AUROC={best:.4f}; checkpoint at {out / 'checkpoint.pt'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Train the 27-class complete ECG model")
    p.add_argument("--manifest", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--init-backbone", default=None)
    p.add_argument("--epochs", type=int, default=15)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--target-len", type=int, default=1024)
    p.add_argument("--target-fs", type=int, default=100)
    return run(p.parse_args(argv))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
