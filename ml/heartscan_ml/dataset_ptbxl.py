from __future__ import annotations

import os

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset
import wfdb

from heartscan_ml.config import TrainConfig
from heartscan_ml.labels import parse_scp_codes, ptbxl_to_screening_class
from heartscan_ml.preprocess import crop_center, resample_linear, zscore_per_lead


class PTBXLScreeningDataset(Dataset):
    """Loads PTB-XL WFDB records; labels 0/1 from SCP; optional synthetic noise as class 2."""

    def __init__(
        self,
        cfg: TrainConfig,
        folds: tuple[int, ...],
        augment_noise: bool,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.cfg = cfg
        self.augment_noise = augment_noise
        self.rng = rng or np.random.default_rng(cfg.seed)
        csv_path = os.path.join(cfg.ptbxl_dir, "ptbxl_database.csv")
        if not os.path.isfile(csv_path):
            raise FileNotFoundError(
                f"Missing {csv_path}. Download PTB-XL from PhysioNet and set PTBXL_DIR."
            )
        df = pd.read_csv(csv_path)
        df = df[df["strat_fold"].isin(folds)].reset_index(drop=True)
        self.rows = df
        self._leads = 12

    def __len__(self) -> int:
        return len(self.rows)

    def _load_signal(self, row: pd.Series) -> np.ndarray:
        rel = str(row["filename_lr"] if self.cfg.sample_rate == 100 else row["filename_hr"]).strip()
        if rel.endswith(".hea"):
            rel = rel[:-4]
        path = os.path.join(self.cfg.ptbxl_dir, rel)
        record = wfdb.rdrecord(path)
        sig = record.p_signal.T.astype(np.float32)
        fs = int(record.fs)
        if fs != self.cfg.sample_rate:
            sig = resample_linear(sig, fs, self.cfg.sample_rate)
        if sig.shape[0] < self._leads:
            raise ValueError(f"Expected 12 leads, got {sig.shape[0]}")
        sig = sig[: self._leads]
        sig = crop_center(sig, self.cfg.crop_len)
        sig = zscore_per_lead(sig)
        return sig

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        row = self.rows.iloc[idx]
        scp = parse_scp_codes(row["scp_codes"])
        y = ptbxl_to_screening_class(scp)
        x = self._load_signal(row)

        if self.augment_noise and self.rng.random() < self.cfg.noise_prob:
            from heartscan_ml.preprocess import add_noise_augmentation

            x = add_noise_augmentation(x, self.rng)
            y = 2

        return torch.from_numpy(x), torch.tensor(y, dtype=torch.long)
