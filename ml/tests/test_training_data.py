from __future__ import annotations

import sys
from types import SimpleNamespace

import numpy as np
import pytest

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

from ml.training.data import PTBXLDiagnosticDataset, ParquetECGDataset
from ml.training.pretrain import _classification_report, _class_weights
from ml.training.train_multilabel import _multilabel_report


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


def test_training_report_and_weights_include_all_classes(tmp_path):
    manifest = tmp_path / "manifest.parquet"
    rows = [
        {
            "file_path": str(tmp_path / f"{idx}.npy"),
            "label": "normal" if idx < 4 else "arrhythmia",
            "label_id": 0 if idx < 4 else 1,
            "sampling_rate_hz": 100,
            "n_leads": 1,
            "duration_s": 10.0,
            "source_dataset": "unit",
            "split": "train",
        }
        for idx in range(5)
    ]
    for row in rows:
        np.save(row["file_path"], np.arange(16, dtype=np.float32))
    pq.write_table(pa.Table.from_pylist(rows), manifest)

    ds = ParquetECGDataset(manifest, split="train")
    weights = _class_weights(ds, "inverse_sqrt", device=__import__("torch").device("cpu"))
    report = _classification_report(np.array([0, 1, 1]), np.array([0, 0, 1]))

    assert weights is not None
    assert weights.shape[0] == 3
    assert weights[1] > weights[0]
    assert report["confusion_matrix"] == [[1, 0, 0], [1, 1, 0], [0, 0, 0]]
    assert report["per_class"]["arrhythmia"]["support"] == 2


def test_ptbxl_diagnostic_dataset_returns_12_leads(tmp_path, monkeypatch):
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
                    "label": "arrhythmia",
                    "label_id": 1,
                    "sampling_rate_hz": 100,
                    "n_leads": 12,
                    "duration_s": 10.0,
                    "source_dataset": "ptb_xl",
                    "split": "train",
                    "metadata": {
                        "diagnostic_classes": ["MI", "CD"],
                        "diagnostic_subclasses": ["AMI", "RBBB"],
                    },
                }
            ]
        ),
        manifest,
    )
    raw = np.tile(np.linspace(-1.0, 1.0, num=1000, dtype=np.float32)[:, None], (1, 12))
    fake_wfdb = SimpleNamespace(rdrecord=lambda _: SimpleNamespace(p_signal=raw))
    monkeypatch.setitem(sys.modules, "wfdb", fake_wfdb)

    sample, target = PTBXLDiagnosticDataset(manifest, split="train")[0]

    assert sample.shape == (12, 1024)
    assert target.tolist() == [0.0, 1.0, 0.0, 1.0, 0.0]


def test_multilabel_report_metrics():
    y = np.array([[1, 0, 0, 0, 0], [0, 1, 1, 0, 0]], dtype=np.float32)
    p = np.array([[0.9, 0.1, 0.1, 0.1, 0.1], [0.2, 0.8, 0.7, 0.1, 0.1]], dtype=np.float32)

    report = _multilabel_report(y, p, threshold=0.5)

    assert report["exact_match"] == 1.0
    assert report["per_class"]["NORM"]["recall"] == 1.0
