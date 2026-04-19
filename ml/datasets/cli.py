"""Command-line interface for the HeartScan dataset registry.

Usage examples
--------------

::

    # List every known dataset with its license + size estimate.
    python -m ml.datasets.cli list

    # Inspect a dataset (prints citation, license, expected size, notes).
    python -m ml.datasets.cli info ptb_xl

    # Download into a target directory (PhysioNet wget recipe; restricted
    # datasets explain how to proceed instead of downloading).
    python -m ml.datasets.cli download ptb_xl --target data/raw/ptb_xl

    # Build a unified Parquet manifest from one or many downloaded datasets.
    python -m ml.datasets.cli manifest \
        --root data/raw \
        --datasets ptb_xl chapman_shaoxing cinc2017 \
        --out data/manifests/tier1.parquet
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from ml.datasets._common import warn_restricted
from ml.datasets.registry import REGISTRY, get


def _cmd_list(args: argparse.Namespace) -> int:
    print(f"{'name':<22} {'version':<8} {'license':<28} {'size_gb':>8}  notes")
    for name, ds in sorted(REGISTRY.items()):
        print(f"{name:<22} {ds.version:<8} {ds.license:<28} {ds.expected_size_gb:>8.1f}  {ds.notes}")
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    ds = get(args.name)
    payload = {
        "name": ds.name,
        "version": ds.version,
        "homepage": ds.homepage,
        "license": ds.license,
        "license_class": ds.license_class,
        "commercial_safe": ds.commercial_safe(),
        "expected_size_gb": ds.expected_size_gb,
        "citation": ds.citation,
        "notes": ds.notes,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _cmd_download(args: argparse.Namespace) -> int:
    ds = get(args.name)
    target = Path(args.target).resolve()
    target.mkdir(parents=True, exist_ok=True)
    if ds.license_class == "restricted":
        warn_restricted(ds.name, ds.notes or "see homepage")
    if not args.confirm and ds.license_class == "non_commercial":
        print(
            f"[abort] {ds.name} is licensed {ds.license} (non-commercial). "
            f"Re-run with --confirm if your use is research-only.",
            file=sys.stderr,
        )
        return 2
    ds.download(target)
    return 0


def _cmd_manifest(args: argparse.Namespace) -> int:
    """Stream every requested dataset and write a single parquet manifest."""
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        print("pyarrow required: pip install pyarrow", file=sys.stderr)
        return 2
    rows: list[dict] = []
    root = Path(args.root)
    for name in args.datasets:
        ds = get(name)
        ds_root = root / name
        if not ds_root.is_dir():
            print(f"[skip] {name}: {ds_root} does not exist", file=sys.stderr)
            continue
        try:
            for sample in ds.parse(ds_root):
                rows.append(_sample_to_row(sample, ds.version))
        except FileNotFoundError as exc:
            print(f"[warn] {name}: {exc}", file=sys.stderr)
    if not rows:
        print("[empty] no samples gathered", file=sys.stderr)
        return 1
    table = pa.Table.from_pylist(rows)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out)
    print(f"[manifest] wrote {len(rows):,} rows to {out}")
    return 0


def _sample_to_row(sample, version: str) -> dict:
    d = asdict(sample)
    d["file_path"] = str(d["file_path"])
    d["dataset_version"] = version
    return d


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="HeartScan dataset registry CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list datasets").set_defaults(func=_cmd_list)

    info = sub.add_parser("info", help="show dataset details")
    info.add_argument("name")
    info.set_defaults(func=_cmd_info)

    dl = sub.add_parser("download", help="download a dataset")
    dl.add_argument("name")
    dl.add_argument("--target", required=True)
    dl.add_argument("--confirm", action="store_true", help="proceed even for non-commercial datasets")
    dl.set_defaults(func=_cmd_download)

    mf = sub.add_parser("manifest", help="build a unified Parquet manifest")
    mf.add_argument("--root", required=True, help="root directory containing one subfolder per dataset")
    mf.add_argument("--datasets", nargs="+", required=True)
    mf.add_argument("--out", required=True)
    mf.set_defaults(func=_cmd_manifest)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
