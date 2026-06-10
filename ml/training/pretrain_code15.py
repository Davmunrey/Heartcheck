"""Pretrain the deep ECG backbone on CODE-15% (Ribeiro et al., 345k 12-lead ECGs).

Why: a 6.8M-param net cold-started on our 34k diagnostic blend is data-starved
(see docs/MODEL_CARD.md "negative result"). CODE-15% gives a 345k-record corpus
to learn rich 12-lead features first; we then transfer the backbone (drop the
head) and fine-tune the 5-superclass head on the PTB-XL + CinC2020 blend via
``train_multilabel --arch deep --init-backbone <this checkpoint>``.

CODE-15 labels are 6 binary abnormalities (1dAVb, RBBB, LBBB, SB, ST, AF). The
exact labels don't matter for transfer — what matters is the backbone learning
ECG morphology from a large, diverse cohort.

Data layout (from scripts/download_code15.sh):
  <root>/exams.csv                      # exam_id, ..., 6 label cols, trace_file
  <root>/exams_part{0..17}.hdf5         # datasets: 'tracings' (N,4096,12), 'exam_id'

Usage:
  apps/ml-api/.venv/bin/python -m ml.training.pretrain_code15 \
    --data-root ~/heartscan_data/code_15pct --out runs/local/code15_pretrain \
    --epochs 8 --batch-size 64 --lr 1e-3 --workers 6
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

from heartscan_ml.cnn1d import build_model

CODE15_LABELS = ("1dAVb", "RBBB", "LBBB", "SB", "ST", "AF")
_TRUTHY = {"1", "true", "t", "yes"}


def _truthy(v: object) -> bool:
    return str(v).strip().lower() in _TRUTHY


class Code15Dataset(Dataset):
    """Lazily reads CODE-15 tracings from the HDF5 parts, labelled from the CSV."""

    def __init__(self, root: Path, exam_ids: list[str], rows: dict[str, dict], target_len: int = 4096) -> None:
        self.root = root
        self.exam_ids = exam_ids
        self.rows = rows
        self.target_len = target_len
        self._files: dict[str, object] = {}
        self._index: dict[str, dict[str, int]] = {}

    def __len__(self) -> int:
        return len(self.exam_ids)

    def _handle(self, trace_file: str):
        import h5py

        if trace_file not in self._files:
            h = h5py.File(self.root / trace_file, "r")
            ids = np.asarray(h["exam_id"])
            self._files[trace_file] = h
            self._index[trace_file] = {str(int(v)): i for i, v in enumerate(ids)}
        return self._files[trace_file], self._index[trace_file]

    def __getitem__(self, i: int):
        eid = self.exam_ids[i]
        row = self.rows[eid]
        h, idx = self._handle(row["trace_file"])
        sig = np.asarray(h["tracings"][idx[eid]], dtype=np.float32)  # (4096, 12)
        if sig.shape[0] < sig.shape[1]:
            sig = sig.T
        sig = sig.T  # -> (12, samples)
        # crop/pad to target_len, then per-lead z-score (scale-invariant, matches
        # the diagnostic dataset preprocessing so transfer is consistent).
        L = sig.shape[1]
        if L >= self.target_len:
            sig = sig[:, : self.target_len]
        else:
            sig = np.pad(sig, ((0, 0), (0, self.target_len - L)))
        sig = sig - sig.mean(axis=1, keepdims=True)
        sig = sig / (sig.std(axis=1, keepdims=True) + 1e-6)
        target = np.asarray([1.0 if _truthy(row.get(k)) else 0.0 for k in CODE15_LABELS], dtype=np.float32)
        return torch.from_numpy(sig.astype(np.float32)), torch.from_numpy(target)


def _load_rows(root: Path, limit: int | None) -> dict[str, dict]:
    csv_path = root / "exams.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(f"CODE-15 exams.csv not found at {csv_path}; run scripts/download_code15.sh")
    rows: dict[str, dict] = {}
    with csv_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tf = row.get("trace_file")
            if not tf or not (root / tf).is_file():
                continue  # part not downloaded yet
            rows[row["exam_id"]] = row
            if limit and len(rows) >= limit:
                break
    if not rows:
        raise RuntimeError(f"No CODE-15 records with present HDF5 parts under {root}.")
    return rows


def _patient_split(rows: dict[str, dict], val_frac: float, seed: int) -> tuple[list[str], list[str]]:
    """Patient-disjoint split so no patient leaks across train/val."""
    by_patient: dict[str, list[str]] = {}
    for eid, r in rows.items():
        by_patient.setdefault(str(r.get("patient_id") or eid), []).append(eid)
    patients = sorted(by_patient)
    rng = np.random.default_rng(seed)
    rng.shuffle(patients)
    n_val = int(len(patients) * val_frac)
    val_p = set(patients[:n_val])
    train, val = [], []
    for p, eids in by_patient.items():
        (val if p in val_p else train).extend(eids)
    return train, val


def _pos_weight(rows: dict[str, dict], ids: list[str], device) -> torch.Tensor:
    y = np.asarray([[1.0 if _truthy(rows[e].get(k)) else 0.0 for k in CODE15_LABELS] for e in ids])
    pos = y.sum(axis=0)
    neg = len(y) - pos
    w = np.clip(neg / np.maximum(pos, 1.0), 1.0, 50.0).astype(np.float32)
    return torch.tensor(w, device=device)


def run(args: argparse.Namespace) -> int:
    root = Path(args.data_root).expanduser()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = _load_rows(root, args.limit)
    train_ids, val_ids = _patient_split(rows, args.val_frac, args.seed)
    print(f"[code15] records={len(rows):,}  train={len(train_ids):,}  val={len(val_ids):,}")

    device = (
        torch.device("cuda") if torch.cuda.is_available()
        else torch.device("mps") if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()
        else torch.device("cpu")
    )
    train_ds = Code15Dataset(root, train_ids, rows, args.target_len)
    val_ds = Code15Dataset(root, val_ids, rows, args.target_len)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=args.workers)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, num_workers=args.workers)

    model = build_model("deep", num_classes=len(CODE15_LABELS), length=args.target_len, in_channels=12).to(device)
    optim = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(optim, T_max=args.epochs)
    loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=_pos_weight(rows, train_ids, device))

    best_auroc = -1.0
    for epoch in range(1, args.epochs + 1):
        model.train()
        t0 = time.perf_counter()
        losses = []
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optim.zero_grad()
            loss = loss_fn(model(x), y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optim.step()
            losses.append(float(loss.item()))
        sched.step()
        auroc = _val_auroc(model, val_loader, device)
        dt = time.perf_counter() - t0
        print(f"[epoch {epoch:>2}] loss={np.mean(losses):.4f} val_macro_auroc={auroc:.4f} ({dt:.0f}s)")
        if auroc > best_auroc:
            best_auroc = auroc
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "arch": "deep",
                    "task": "code15_pretrain",
                    "labels": list(CODE15_LABELS),
                    "target_len": args.target_len,
                    "target_fs": 400,
                    "in_channels": 12,
                    "val_macro_auroc": best_auroc,
                },
                out / "backbone.pt",
            )
    (out / "summary.json").write_text(
        json.dumps({"records": len(rows), "best_val_macro_auroc": best_auroc, "epochs": args.epochs}, indent=2),
        encoding="utf-8",
    )
    print(f"[done] best val macro-AUROC={best_auroc:.4f}; backbone at {out / 'backbone.pt'}")
    print(f"       fine-tune: train_multilabel --arch deep --init-backbone {out / 'backbone.pt'}")
    return 0


def _val_auroc(model, loader, device) -> float:
    model.eval()
    logits, labels = [], []
    with torch.no_grad():
        for x, y in loader:
            logits.append(model(x.to(device)).cpu().numpy())
            labels.append(y.numpy())
    if not logits:
        return 0.0
    p = 1.0 / (1.0 + np.exp(-np.concatenate(logits)))
    y = np.concatenate(labels)
    aucs = []
    for c in range(y.shape[1]):
        yc = y[:, c]
        if yc.min() == yc.max():
            continue  # AUROC undefined for a single-class column
        aucs.append(_auroc(yc, p[:, c]))
    return float(np.mean(aucs)) if aucs else 0.0


def _auroc(y_true: np.ndarray, scores: np.ndarray) -> float:
    """Rank-based AUROC (Mann-Whitney U), tie-aware, no sklearn dependency."""
    n_pos = y_true.sum()
    n_neg = len(y_true) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.5
    order = np.argsort(scores, kind="mergesort")
    sorted_scores = scores[order]
    ranks = np.empty(len(scores), dtype=np.float64)
    i = 0
    while i < len(scores):
        j = i
        while j < len(scores) and sorted_scores[j] == sorted_scores[i]:
            j += 1
        ranks[order[i:j]] = (i + j + 1) / 2.0  # average rank for ties (1-indexed)
        i = j
    return float((ranks[y_true == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Pretrain the deep ECG backbone on CODE-15%")
    p.add_argument("--data-root", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--epochs", type=int, default=8)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--target-len", type=int, default=4096)
    p.add_argument("--val-frac", type=float, default=0.05)
    p.add_argument("--limit", type=int, default=None, help="cap records (smoke test)")
    p.add_argument("--seed", type=int, default=1234)
    return run(p.parse_args(argv))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
