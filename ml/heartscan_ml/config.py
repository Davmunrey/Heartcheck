from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TrainConfig:
    ptbxl_dir: str
    sample_rate: int = 100
    crop_len: int = 1000
    batch_size: int = 32
    epochs: int = 20
    lr: float = 1e-3
    weight_decay: float = 1e-4
    train_folds: tuple[int, ...] = tuple(range(1, 9))
    val_fold: int = 9
    test_fold: int = 10
    noise_prob: float = 0.15
    num_workers: int = 0
    device: str = "cpu"
    checkpoint_dir: str = "checkpoints"
    seed: int = 42


def default_train_config() -> TrainConfig:
    root = os.environ.get("PTBXL_DIR", "")
    return TrainConfig(ptbxl_dir=root)


@dataclass(frozen=True)
class GuardConfig:
    min_confidence: float = 0.55
    max_bpm_human_plausible: float = 280.0
    min_bpm_human_plausible: float = 25.0
    min_extraction_quality: int = 2
    min_rr_samples: int = 50


def default_guard_config() -> GuardConfig:
    return GuardConfig()
