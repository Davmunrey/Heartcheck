#!/usr/bin/env python3
"""Remap a HeartScan signal manifest's file_path column to a local (non-iCloud)
data root, preserving every other column and the train/val/test split.

Motivation: the repo lives under ~/Desktop which iCloud evicts ("dataless"
files), making every WFDB read block ~24s on on-demand download. We re-download
the raw signals to a local path and point an existing manifest at it so the
exact champion splits are preserved for a fair before/after comparison.

Usage:
  python scripts/remap_manifest_local.py \
    --in  runs/auto/ptbxl_georgia_full/signal_manifest_split.parquet \
    --out runs/auto/ptbxl_georgia_full/signal_manifest_split.local.parquet \
    --data-root /Users/mac/heartscan_data
"""
from __future__ import annotations

import argparse
import os

import pyarrow as pa
import pyarrow.parquet as pq

# (old_prefix, new_subdir_under_data_root)
REMAPS = [
    (
        "data/raw/ptb_xl/ptb-xl-a-large-publicly-available-electrocardiography-dataset-1.0.3/",
        "ptb_xl/",
    ),
    ("data/raw/georgia12/1.0.2/training/georgia/", "georgia12/"),
    ("data/raw/chapman_shaoxing/", "chapman_shaoxing/"),
]


def remap_path(p: str, data_root: str) -> str:
    for old, new in REMAPS:
        if p.startswith(old):
            return os.path.join(data_root, new + p[len(old):])
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--check-exists", action="store_true", help="report missing files after remap")
    args = ap.parse_args()

    table = pq.read_table(args.inp)
    paths = table.column("file_path").to_pylist()
    new_paths = [remap_path(p, args.data_root) for p in paths]

    idx = table.schema.get_field_index("file_path")
    table = table.set_column(idx, "file_path", pa.array(new_paths, type=pa.string()))
    pq.write_table(table, args.out)
    print(f"[remap] wrote {args.out} ({table.num_rows} rows)")

    if args.check_exists:
        miss = 0
        for p in new_paths:
            ok = os.path.exists(p) or os.path.exists(p + ".dat") or os.path.exists(p + ".mat")
            if not ok:
                miss += 1
        print(f"[remap] missing after remap: {miss}/{len(new_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
