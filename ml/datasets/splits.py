"""Patient-stratified train/val/test splits.

Reads a unified manifest (Parquet, produced by ``ml.datasets.cli manifest``)
and writes back the same rows with an extra ``split`` column in
``{train, val, test}``.

Stratification rules
--------------------

- Splits are at the **patient** level (not record), to avoid the most common
  evaluation leak in ECG ML.
- When ``patient_id`` is missing or empty the record is treated as its own
  patient — keeps things deterministic without dropping data.
- The ratio defaults to ``80 / 10 / 10``; reproducible via ``--seed``.
- Per-class proportions are *approximately* preserved (we resample the
  patient-level sort by ``label`` mode within each patient).
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np


def _patient_label_mode(rows: list[dict]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        counts[r["label"]] += 1
    return max(counts, key=counts.get)


def stratify(
    rows: list[dict],
    *,
    train: float = 0.8,
    val: float = 0.1,
    seed: int = 1234,
) -> dict[str, str]:
    """Return ``{patient_id: split}``."""
    if abs(train + val + (1 - train - val) - 1.0) > 1e-6:
        raise ValueError("train + val must be < 1")
    rng = np.random.default_rng(seed)
    by_patient: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        pid = r.get("patient_id") or r.get("record_id")
        by_patient[pid].append(r)
    by_class: dict[str, list[str]] = defaultdict(list)
    for pid, rs in by_patient.items():
        by_class[_patient_label_mode(rs)].append(pid)

    assignment: dict[str, str] = {}
    test = 1.0 - train - val
    for cls, pids in by_class.items():
        rng.shuffle(pids)
        n = len(pids)
        n_train = int(round(n * train))
        n_val = int(round(n * val))
        for pid in pids[:n_train]:
            assignment[pid] = "train"
        for pid in pids[n_train : n_train + n_val]:
            assignment[pid] = "val"
        for pid in pids[n_train + n_val :]:
            assignment[pid] = "test"
        _ = test  # documented but unused beyond computing tail slice
    return assignment


def _cmd(args: argparse.Namespace) -> int:
    try:
        import pyarrow.parquet as pq
        import pyarrow as pa
    except ImportError:
        print("pyarrow required: pip install pyarrow", file=sys.stderr)
        return 2

    in_path = Path(args.manifest)
    table = pq.read_table(in_path)
    rows = table.to_pylist()
    assignment = stratify(rows, train=args.train, val=args.val, seed=args.seed)
    for r in rows:
        pid = r.get("patient_id") or r.get("record_id")
        r["split"] = assignment.get(pid, "train")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), out_path)
    summary: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        summary[r["split"]][r["label"]] += 1
    print(f"[splits] wrote {len(rows):,} rows to {out_path}")
    for split, by_label in summary.items():
        total = sum(by_label.values())
        breakdown = ", ".join(f"{k}={v}" for k, v in sorted(by_label.items()))
        print(f"  {split:<6} {total:>7,}  ({breakdown})")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Patient-stratified train/val/test splits")
    p.add_argument("--manifest", required=True, help="input parquet from ml.datasets.cli manifest")
    p.add_argument("--out", required=True, help="output parquet with split column")
    p.add_argument("--train", type=float, default=0.8)
    p.add_argument("--val", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=1234)
    p.set_defaults(func=_cmd)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
