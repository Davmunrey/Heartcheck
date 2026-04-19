"""Torch Dataset adapter that reads a Parquet manifest produced by
``ml.datasets.cli manifest`` and serves 1024-sample 1D windows.

Lead handling
-------------

- 12-lead records: pick lead II by default (most rhythm-informative).
- single-lead records: use the only channel.
- multi-channel that is neither: average channels (defensive default).

Resampling
----------

Resamples to 100 Hz so the standard 10 s clip becomes 1000 samples; padded
to the model length (1024) with reflection. This matches the convention of
PTB-XL's ``filename_lr`` and the 100 Hz heartscan_ml pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import torch
from torch.utils.data import Dataset

CLASS_NAMES = ("normal", "arrhythmia", "noise")


@dataclass
class ManifestRow:
    file_path: str
    label_id: int
    sampling_rate_hz: int
    n_leads: int
    duration_s: float
    source_dataset: str


class ParquetECGDataset(Dataset):
    """Loads a unified Parquet manifest and serves ``(signal, label)``."""

    def __init__(
        self,
        manifest_path: str | Path,
        split: str | None = None,
        target_len: int = 1024,
        target_fs: int = 100,
        lead: Literal["ii", "first", "mean"] = "ii",
    ) -> None:
        try:
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise RuntimeError("pyarrow required: pip install pyarrow") from exc
        table = pq.read_table(manifest_path)
        df = table.to_pylist()
        if split:
            df = [r for r in df if r.get("split") == split]
        self.rows: list[ManifestRow] = [
            ManifestRow(
                file_path=r["file_path"],
                label_id=int(r["label_id"]),
                sampling_rate_hz=int(r.get("sampling_rate_hz") or 500),
                n_leads=int(r.get("n_leads") or 1),
                duration_s=float(r.get("duration_s") or 10.0),
                source_dataset=str(r.get("source_dataset") or "unknown"),
            )
            for r in df
        ]
        self.target_len = target_len
        self.target_fs = target_fs
        self.lead = lead

    def __len__(self) -> int:
        return len(self.rows)

    def _load_raw(self, row: ManifestRow) -> np.ndarray:
        path = Path(row.file_path)
        # WFDB / .mat / .dat / .h5 dispatch — defensive: try wfdb, fall back
        # to numpy.load, fall back to a zero stub so missing files don't kill
        # a 1M-row epoch.
        if path.suffix in {".dat", ".hea"}:
            try:
                import wfdb

                rec = wfdb.rdrecord(str(path.with_suffix("")))
                return np.asarray(rec.p_signal, dtype=np.float32)
            except Exception:
                return np.zeros((self.target_len, max(1, row.n_leads)), dtype=np.float32)
        if path.suffix == ".mat":
            try:
                from scipy.io import loadmat

                m = loadmat(path)
                key = next((k for k in m if not k.startswith("__")), None)
                arr = np.asarray(m[key], dtype=np.float32) if key else np.zeros((self.target_len, 1))
                if arr.ndim == 2 and arr.shape[0] < arr.shape[1]:
                    arr = arr.T  # (samples, channels)
                return arr
            except Exception:
                return np.zeros((self.target_len, max(1, row.n_leads)), dtype=np.float32)
        if path.suffix in {".npy", ".npz"}:
            try:
                arr = np.load(path)
                if hasattr(arr, "files"):
                    arr = arr[arr.files[0]]
                return np.asarray(arr, dtype=np.float32)
            except Exception:
                pass
        return np.zeros((self.target_len, max(1, row.n_leads)), dtype=np.float32)

    def _select_lead(self, raw: np.ndarray) -> np.ndarray:
        if raw.ndim == 1:
            return raw
        if raw.shape[1] == 1:
            return raw[:, 0]
        if self.lead == "ii" and raw.shape[1] >= 2:
            return raw[:, 1]
        if self.lead == "first":
            return raw[:, 0]
        return raw.mean(axis=1)

    def _resample(self, signal: np.ndarray, fs_in: int) -> np.ndarray:
        if fs_in == self.target_fs:
            return signal
        n_out = int(round(len(signal) * self.target_fs / fs_in))
        if n_out < 2:
            return np.zeros(self.target_len, dtype=np.float32)
        x_in = np.linspace(0, 1, num=len(signal))
        x_out = np.linspace(0, 1, num=n_out)
        return np.interp(x_out, x_in, signal).astype(np.float32)

    def _crop_or_pad(self, signal: np.ndarray) -> np.ndarray:
        L = self.target_len
        if len(signal) >= L:
            start = (len(signal) - L) // 2
            return signal[start : start + L]
        pad = L - len(signal)
        return np.pad(signal, (pad // 2, pad - pad // 2), mode="reflect" if len(signal) > 1 else "constant")

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        row = self.rows[idx]
        raw = self._load_raw(row)
        sig = self._select_lead(raw)
        sig = self._resample(sig, fs_in=row.sampling_rate_hz)
        sig = self._crop_or_pad(sig)
        # global z-score
        sig = sig - sig.mean()
        std = sig.std() + 1e-6
        sig = sig / std
        return (
            torch.from_numpy(sig.astype(np.float32)).unsqueeze(0),  # (1, L)
            torch.tensor(row.label_id, dtype=torch.long),
        )
