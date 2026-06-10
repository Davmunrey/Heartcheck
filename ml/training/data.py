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
import re
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
        self._hdf5_files = {}
        self._hdf5_indices = {}

    def _load_wfdb_format16(self, path: Path) -> np.ndarray | None:
        """Fast local reader for common WFDB 16-bit interleaved records."""
        base = path.with_suffix("") if path.suffix in {".hea", ".dat"} else path
        header_path = base.with_suffix(".hea")
        if not header_path.is_file():
            return None
        lines = [line.strip() for line in header_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return None
        parts = lines[0].split()
        if len(parts) < 4:
            return None
        try:
            n_leads = int(parts[1])
            n_samples = int(parts[3])
        except ValueError:
            return None
        sig_lines = [line.split() for line in lines[1:] if not line.startswith("#")]
        if len(sig_lines) < n_leads:
            return None
        dat_name = sig_lines[0][0]
        if any(len(fields) < 3 or fields[0] != dat_name or fields[1] != "16" for fields in sig_lines[:n_leads]):
            return None
        dat_path = header_path.with_name(dat_name)
        if not dat_path.is_file():
            return None
        raw = np.fromfile(dat_path, dtype="<i2", count=n_samples * n_leads)
        if raw.size != n_samples * n_leads:
            return None
        digital = raw.reshape(n_samples, n_leads).astype(np.float32)
        gains = []
        baselines = []
        for fields in sig_lines[:n_leads]:
            gain_field = fields[2]
            match = re.match(r"([-+0-9.]+)(?:\(([-+0-9.]+)\))?", gain_field)
            gain = float(match.group(1)) if match else 1.0
            baseline = float(match.group(2)) if match and match.group(2) is not None else 0.0
            gains.append(gain if gain else 1.0)
            baselines.append(baseline)
        return (digital - np.asarray(baselines, dtype=np.float32)) / np.asarray(gains, dtype=np.float32)

    def __len__(self) -> int:
        return len(self.rows)

    def _load_raw(self, row: ManifestRow) -> np.ndarray:
        path = Path(row.file_path)
        raw_path = str(row.file_path)
        if "::" in raw_path:
            hdf5_path, record_id = raw_path.split("::", 1)
            try:
                import h5py

                if hdf5_path not in self._hdf5_files:
                    handle = h5py.File(hdf5_path, "r")
                    ids = handle["exam_id"][:]
                    self._hdf5_files[hdf5_path] = handle
                    self._hdf5_indices[hdf5_path] = {str(int(v)): i for i, v in enumerate(ids)}
                idx = self._hdf5_indices[hdf5_path][str(record_id)]
                return np.asarray(self._hdf5_files[hdf5_path]["tracings"][idx], dtype=np.float32)
            except Exception:  # noqa: BLE001
                _logger.warning("ecg_load_failed", extra={"path": raw_path, "suffix": ".hdf5"})
                return np.zeros((self.target_len, max(1, row.n_leads)), dtype=np.float32)
        # WFDB / .mat / .dat / .h5 dispatch — defensive: try wfdb, fall back
        # to numpy.load, fall back to a zero stub so missing files don't kill
        # a 1M-row epoch.
        is_wfdb_record = path.suffix in {".dat", ".hea"} or (
            not path.suffix and (path.with_suffix(".hea").is_file() or path.with_suffix(".dat").is_file())
        )
        if is_wfdb_record:
            try:
                direct = self._load_wfdb_format16(path)
                if direct is not None:
                    return direct.astype(np.float32, copy=False)
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
        return_mask: bool = False,
        classes: tuple[str, ...] | None = None,
        label_key: str = "diagnostic_classes",
    ) -> None:
        # Override the 5-superclass default to train a richer head (e.g. the
        # 27-class rhythm+diagnostic taxonomy via classes=CINC2020_27_CLASSES,
        # label_key="cinc2020_27"). Default keeps backward-compatible behaviour.
        if classes is not None:
            self.classes = tuple(classes)
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
        self._sources: list[str] = []
        for r in rows:
            metadata = r.get("metadata") or {}
            positive = metadata.get(label_key) or []
            target = np.asarray([1.0 if c in positive else 0.0 for c in self.classes], dtype=np.float32)
            if not target.any():
                continue
            source = str(r.get("source_dataset") or "unknown")
            self.rows.append(
                ManifestRow(
                    file_path=r["file_path"],
                    label_id=int(r["label_id"]),
                    label=str(r.get("label") or CLASS_NAMES[int(r["label_id"])]),
                    sampling_rate_hz=int(r.get("sampling_rate_hz") or 500),
                    n_leads=int(r.get("n_leads") or 12),
                    duration_s=float(r.get("duration_s") or 10.0),
                    source_dataset=source,
                )
            )
            self.targets.append(target)
            self._sources.append(source)
        self.target_len = target_len
        self.target_fs = target_fs
        self.lead = "ii"
        self.augment = augment
        self.return_mask = return_mask
        self.rng = np.random.default_rng(seed)
        self._hdf5_files = {}
        self._hdf5_indices = {}
        self.masks = self._build_partial_label_masks()

    def _build_partial_label_masks(self) -> list[np.ndarray]:
        """Per-record loss mask for partial-label datasets.

        A source whose coding scheme never expresses a superclass (e.g.
        CPSC-2018 carries no MI/HYP codes) produces *unreliable negatives* for
        that class — every record reads 0 only because the annotator never
        looked. Treating those as true negatives poisons MI/STTC precision.

        We mark a class ``observed`` for a source iff it is positive in at least
        one of that source's records; the loss then ignores un-observed classes.
        Fully-annotated sources (PTB-XL: all 5 present) get an all-ones mask, so
        this is a no-op for them.
        """
        observed: dict[str, np.ndarray] = {}
        for src, tgt in zip(self._sources, self.targets):
            observed[src] = observed.get(src, np.zeros(len(self.classes), np.float32)) + tgt
        source_mask = {s: (v > 0).astype(np.float32) for s, v in observed.items()}
        return [source_mask[s] for s in self._sources]

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
        signal = torch.from_numpy(stacked.astype(np.float32))
        target = torch.from_numpy(self.targets[idx])
        if self.return_mask:
            return signal, target, torch.from_numpy(self.masks[idx])
        return signal, target
