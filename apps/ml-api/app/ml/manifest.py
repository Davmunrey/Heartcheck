"""Checkpoint manifest schema and validation.

A manifest is a small YAML file that lives next to the checkpoint and
documents *what* it is and *how it was made*. In production the backend
refuses to load a checkpoint whose manifest is missing or whose SHA-256 does
not match the file on disk.

Schema (minimal but enforceable)::

    model_version: ecg-resnet1d-1.0.0          # required, str
    architecture: ECGResNet1D                  # required, str
    sha256: <hex>                              # required, sha256 of the .pt file
    dataset:
      name: ptbxl                              # required
      version: 1.0.3                           # required
      split: train_folds_1-8_val_9             # optional
      synthetic_augmentations: synth_v1        # optional
    metrics:                                   # required (output of `make eval`)
      f1_macro: 0.78
      ece: 0.04
      p95_ms: 120
    training:
      epochs: 30
      batch_size: 64
      seed: 1234
    created_at: 2026-04-18T00:00:00Z
    author: heartscan-eng
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class CheckpointManifest:
    model_version: str
    architecture: str
    sha256: str
    dataset_name: str
    dataset_version: str
    metrics: dict[str, float]
    training: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    author: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def verify_against_file(self, weights_path: Path) -> None:
        """Raise if the SHA-256 of ``weights_path`` does not match the manifest."""
        digest = hashlib.sha256(weights_path.read_bytes()).hexdigest()
        if digest.lower() != self.sha256.lower():
            raise RuntimeError(
                f"Checkpoint SHA mismatch for {weights_path.name}: "
                f"manifest={self.sha256[:12]}.. file={digest[:12]}.."
            )

    def public_meta(self) -> dict[str, Any]:
        """Subset safe to expose via /api/v1/meta (no training details)."""
        return {
            "model_version": self.model_version,
            "architecture": self.architecture,
            "dataset": {"name": self.dataset_name, "version": self.dataset_version},
            "metrics": self.metrics,
        }


def load_manifest(path: Path) -> CheckpointManifest:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    required = ("model_version", "architecture", "sha256", "dataset", "metrics")
    missing = [k for k in required if k not in raw]
    if missing:
        raise ValueError(f"Manifest {path} missing required keys: {missing}")
    dataset = raw["dataset"] or {}
    if "name" not in dataset or "version" not in dataset:
        raise ValueError(f"Manifest {path}: dataset must have name and version")
    return CheckpointManifest(
        model_version=str(raw["model_version"]),
        architecture=str(raw["architecture"]),
        sha256=str(raw["sha256"]),
        dataset_name=str(dataset["name"]),
        dataset_version=str(dataset["version"]),
        metrics={k: float(v) for k, v in (raw["metrics"] or {}).items()},
        training=dict(raw.get("training") or {}),
        created_at=str(raw.get("created_at", "")),
        author=str(raw.get("author", "")),
        extra={k: v for k, v in raw.items() if k not in {*required, "training", "created_at", "author"}},
    )
