"""Shared helpers for dataset loaders: HTTP downloads, SHA verification,
WFDB parsing, label-mapping utilities."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

CHUNK = 1 << 20  # 1 MiB


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def verify_sha(path: Path, expected_sha256: str) -> None:
    digest = sha256_file(path)
    if digest.lower() != expected_sha256.lower():
        raise RuntimeError(
            f"SHA mismatch for {path.name}: expected={expected_sha256[:12]}.. got={digest[:12]}.."
        )


def http_download(url: str, target: Path) -> None:
    """Resilient wget; prints to stderr so the CLI can capture progress."""
    ensure_dir(target.parent)
    print(f"[download] {url} -> {target}", file=sys.stderr)
    if shutil.which("wget"):
        subprocess.check_call(
            ["wget", "-c", "--tries=5", "--retry-connrefused", "-O", str(target), url]
        )
    elif shutil.which("curl"):
        subprocess.check_call(["curl", "-L", "-C", "-", "-o", str(target), url])
    else:  # last resort, slow but works
        import urllib.request

        urllib.request.urlretrieve(url, target)


def physionet_wget(slug: str, target_dir: Path) -> None:
    """Mirror a PhysioNet record set via the published wget recipe.

    PhysioNet uses ``-r -N -c -np`` against ``https://physionet.org/files/<slug>/``.
    The caller is responsible for accepting the dataset license and providing
    credentials when needed (CITI for MIMIC, etc.).
    """
    if not shutil.which("wget"):
        raise RuntimeError("wget required for PhysioNet mirroring; install it first")
    ensure_dir(target_dir)
    base = f"https://physionet.org/files/{slug}/"
    print(f"[physionet] mirroring {base} -> {target_dir}", file=sys.stderr)
    subprocess.check_call(
        [
            "wget",
            "-r",
            "-N",
            "-c",
            "-np",
            "--no-host-directories",
            "--cut-dirs=2",
            "--directory-prefix",
            str(target_dir),
            base,
        ]
    )


def write_manifest(records: Iterable[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")


def warn_restricted(name: str, reason: str) -> None:
    print(
        f"[skip] dataset {name!r} requires manual access: {reason}\n"
        f"      run the documented procedure (see ml/datasets/{name}.py docstring)",
        file=sys.stderr,
    )


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if raw in {"1", "true", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "no", "n", "off"}:
        return False
    return default
