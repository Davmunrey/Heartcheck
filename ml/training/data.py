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

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import torch
from torch.utils.data import Dataset

_logger = logging.getLogger(__name__)

CLASS_NAMES = ("normal", "arrhythmia", "noise")
PTBXL_DIAGNOSTIC_CLASSES = ("NORM", "MI", "STTC", "CD", "HYP")


@dataclass
class ManifestRow:
    file_path: str
    label_id: int
    label: str
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
                label=str(r.get("label") or CLASS_NAMES[int(r["label_id"])]),
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
        is_wfdb_record = path.suffix in {".dat", ".hea"} or (
            not path.suffix and (path.with_suffix(".hea").is_file() or path.with_suffix(".dat").is_file())
        )
        if is_wfdb_record:
            try:
                import wfdb

                rec = wfdb.rdrecord(str(path.with_suffix("")))
                return np.asarray(rec.p_signal, dtype=np.float32)
            except Exception:  # noqa: BLE001
                _logger.warning("ecg_load_failed", extra={"path": str(row.file_path), "suffix": path.suffix})
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
            except Exception:  # noqa: BLE001
                _logger.warning("ecg_load_failed", extra={"path": str(row.file_path), "suffix": path.suffix})
                return np.zeros((self.target_len, max(1, row.n_leads)), dtype=np.float32)
        if path.suffix in {".npy", ".npz"}:
            try:
                arr = np.load(path)
                if hasattr(arr, "files"):
                    arr = arr[arr.files[0]]
                return np.asarray(arr, dtype=np.float32)
            except Exception:  # noqa: BLE001
                _logger.warning("ecg_load_failed", extra={"path": str(row.file_path), "suffix": path.suffix})
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

    def _to_channel_first(self, raw: np.ndarray) -> np.ndarray:
        if raw.ndim == 1:
            raw = raw[:, np.newaxis]
        if raw.shape[1] >= 12:
            raw = raw[:, :12]
        elif raw.shape[1] < 12:
            raw = np.pad(raw, ((0, 0), (0, 12 - raw.shape[1])), mode="constant")
        return raw.T

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


class PTBXLDiagnosticDataset(ParquetECGDataset):
    """Multi-label PTB-XL diagnostic superclass dataset.

    Targets follow PTB-XL diagnostic superclasses: NORM, MI, STTC, CD, HYP.
    Output tensors are 12-lead channel-first arrays: ``(12, target_len)``.
    """

    classes = PTBXL_DIAGNOSTIC_CLASSES

    def __init__(
        self,
        manifest_path: str | Path,
        split: str | None = None,
        target_len: int = 1024,
        target_fs: int = 100,
        augment: bool = False,
        seed: int = 1234,
    ) -> None:
        try:
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise RuntimeError("pyarrow required: pip install pyarrow") from exc
        table = pq.read_table(manifest_path)
        rows = table.to_pylist()
        if split:
            rows = [r for r in rows if r.get("split") == split]
        self.rows = []
        self.targets: list[np.ndarray] = []
        for r in rows:
            metadata = r.get("metadata") or {}
            diagnostic_classes = metadata.get("diagnostic_classes") or []
            target = np.asarray([1.0 if c in diagnostic_classes else 0.0 for c in self.classes], dtype=np.float32)
            if not target.any():
                continue
            self.rows.append(
                ManifestRow(
                    file_path=r["file_path"],
                    label_id=int(r["label_id"]),
                    label=str(r.get("label") or CLASS_NAMES[int(r["label_id"])]),
                    sampling_rate_hz=int(r.get("sampling_rate_hz") or 500),
                    n_leads=int(r.get("n_leads") or 12),
                    duration_s=float(r.get("duration_s") or 10.0),
                    source_dataset=str(r.get("source_dataset") or "unknown"),
                )
            )
            self.targets.append(target)
        self.target_len = target_len
        self.target_fs = target_fs
        self.lead = "ii"
        self.augment = augment
        self.rng = np.random.default_rng(seed)

    def _augment_signal(self, signal: np.ndarray) -> np.ndarray:
        """Apply conservative ECG augmentations to improve demo robustness."""
        signal = signal.copy()
        if self.rng.random() < 0.5:
            signal *= self.rng.uniform(0.85, 1.15, size=(signal.shape[0], 1)).astype(np.float32)
        if self.rng.random() < 0.35:
            signal += self.rng.normal(0.0, 0.03, size=signal.shape).astype(np.float32)
        if self.rng.random() < 0.25:
            shift = int(self.rng.integers(-24, 25))
            signal = np.roll(signal, shift, axis=1)
        if self.rng.random() < 0.15:
            n_drop = int(self.rng.integers(1, 3))
            leads = self.rng.choice(signal.shape[0], size=n_drop, replace=False)
            signal[leads] = 0.0
        return signal

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        row = self.rows[idx]
        raw = self._load_raw(row)
        signal = self._to_channel_first(raw)
        resampled = []
        for lead in signal:
            x = self._resample(lead, fs_in=row.sampling_rate_hz)
            x = self._crop_or_pad(x)
            x = x - x.mean()
            x = x / (x.std() + 1e-6)
            resampled.append(x.astype(np.float32))
        stacked = np.stack(resampled)
        if self.augment:
            stacked = self._augment_signal(stacked)
        return torch.from_numpy(stacked.astype(np.float32)), torch.from_numpy(self.targets[idx])
