from __future__ import annotations

import sys
from types import SimpleNamespace

import numpy as np
import pytest

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

from ml.training.data import ParquetECGDataset


def test_suffixless_wfdb_record_loads(tmp_path, monkeypatch):
    record = tmp_path / "records100" / "00000" / "00001_lr"
    record.parent.mkdir(parents=True)
    record.with_suffix(".hea").write_text("stub\n", encoding="utf-8")
    record.with_suffix(".dat").write_bytes(b"stub")

    manifest = tmp_path / "manifest.parquet"
    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "file_path": str(record),
                    "label_id": 1,
                    "sampling_rate_hz": 100,
                    "n_leads": 12,
                    "duration_s": 10.0,
                    "source_dataset": "ptb_xl",
                    "split": "train",
                }
            ]
        ),
        manifest,
    )

    raw = np.zeros((1000, 12), dtype=np.float32)
    raw[:, 1] = np.linspace(-1.0, 1.0, num=1000, dtype=np.float32)
    fake_wfdb = SimpleNamespace(rdrecord=lambda _: SimpleNamespace(p_signal=raw))
    monkeypatch.setitem(sys.modules, "wfdb", fake_wfdb)

    sample, label = ParquetECGDataset(manifest, split="train")[0]

    assert label == 1
    assert sample.shape == (1, 1024)
    assert float(sample.std()) > 0.5
