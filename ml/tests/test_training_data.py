from __future__ import annotations

import sys
from types import SimpleNamespace

import numpy as np
import pytest

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

from ml.training.data import PTBXLDiagnosticDataset, ParquetECGDataset  # noqa: E402
from ml.training.pretrain import _classification_report, _class_weights  # noqa: E402
from ml.training.train_multilabel import FocalBCEWithLogitsLoss, _multilabel_report, tune_thresholds  # noqa: E402


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


def test_multilabel_threshold_tuning_and_focal_loss():
    y = np.array([[1, 0, 0, 0, 0], [1, 1, 0, 0, 0], [0, 1, 0, 0, 0]], dtype=np.float32)
    p = np.array([[0.7, 0.2, 0.1, 0.1, 0.1], [0.6, 0.4, 0.1, 0.1, 0.1], [0.2, 0.8, 0.1, 0.1, 0.1]], dtype=np.float32)
    thresholds = tune_thresholds(y, p, steps=5)
    report = _multilabel_report(y, p, thresholds)

    torch = __import__("torch")
    loss = FocalBCEWithLogitsLoss(gamma=2.0)(torch.zeros((2, 5)), torch.zeros((2, 5)))

    assert len(thresholds) == 5
    assert report["macro_f1"] >= 0.4
    assert float(loss) >= 0.0


def _write_manifest(path, rows):
    pq.write_table(pa.Table.from_pylist(rows), path)


def test_partial_label_mask_ignores_unobserved_classes(tmp_path):
    """A source that never expresses a class must get that class masked out."""
    manifest = tmp_path / "m.parquet"
    rows = [
        # PTB-XL: expresses MI and HYP -> both observed
        {"file_path": "a", "label_id": 1, "sampling_rate_hz": 100, "n_leads": 12,
         "duration_s": 10.0, "source_dataset": "ptb_xl", "split": "train",
         "metadata": {"diagnostic_classes": ["MI"]}},
        {"file_path": "b", "label_id": 1, "sampling_rate_hz": 100, "n_leads": 12,
         "duration_s": 10.0, "source_dataset": "ptb_xl", "split": "train",
         "metadata": {"diagnostic_classes": ["HYP"]}},
        # cpsc-like: only ever expresses MI -> HYP/STTC/CD/NORM unobserved
        {"file_path": "c", "label_id": 1, "sampling_rate_hz": 500, "n_leads": 12,
         "duration_s": 10.0, "source_dataset": "cpsc", "split": "train",
         "metadata": {"diagnostic_classes": ["MI"]}},
    ]
    _write_manifest(manifest, rows)
    ds = PTBXLDiagnosticDataset(manifest, split="train", return_mask=True)
    classes = list(ds.classes)
    mi, hyp = classes.index("MI"), classes.index("HYP")
    masks = {s: m for s, m in zip(ds._sources, ds.masks)}
    # cpsc never expresses HYP -> masked (0); MI is observed -> kept (1)
    assert masks["cpsc"][hyp] == 0.0
    assert masks["cpsc"][mi] == 1.0
    # ptb_xl expresses both -> all observed entries kept
    assert masks["ptb_xl"][hyp] == 1.0


def test_focal_loss_mask_skips_masked_entries():
    import torch
    loss = FocalBCEWithLogitsLoss()
    # Non-uniform logits so per-element losses differ across columns.
    logits = torch.tensor([[5.0, 0.0, 0.0, 0.0, 0.0], [5.0, 0.0, 0.0, 0.0, 0.0]])
    targets = torch.zeros(2, 5)
    targets[:, 0] = 1.0  # class 0 positive and well-predicted (low loss)
    full = loss(logits, targets)
    mask = torch.ones(2, 5)
    mask[:, 0] = 0.0  # mask out the well-predicted positive column
    masked = loss(logits, targets, mask)
    # Removing the low-loss column raises the masked mean -> must differ.
    assert not torch.isclose(full, masked)
    assert masked > full


def test_build_model_arch_selection():
    import torch
    from heartscan_ml.cnn1d import ECGResNet1D, ECGResNetDeep1D, build_model
    light = build_model("resnet", num_classes=5, length=1024, in_channels=12)
    deep = build_model("deep", num_classes=5, length=4096, in_channels=12)
    assert isinstance(light, ECGResNet1D)
    assert isinstance(deep, ECGResNetDeep1D)
    # Deep net is length-agnostic and emits (B, num_classes).
    assert tuple(deep(torch.randn(2, 12, 4096)).shape) == (2, 5)
    assert tuple(deep(torch.randn(1, 12, 5000)).shape) == (1, 5)
    # Deep net has substantially more capacity than the light serving net.
    assert sum(p.numel() for p in deep.parameters()) > 10 * sum(p.numel() for p in light.parameters())


def test_sample_weights_oversample_rare_class(tmp_path):
    from ml.training.train_multilabel import _sample_weights
    manifest = tmp_path / "m.parquet"
    # 4 common (NORM) + 1 rare (HYP) records
    rows = [
        {"file_path": str(i), "label_id": 0, "sampling_rate_hz": 100, "n_leads": 12,
         "duration_s": 10.0, "source_dataset": "ptb_xl", "split": "train",
         "metadata": {"diagnostic_classes": ["NORM"]}}
        for i in range(4)
    ] + [
        {"file_path": "h", "label_id": 1, "sampling_rate_hz": 100, "n_leads": 12,
         "duration_s": 10.0, "source_dataset": "ptb_xl", "split": "train",
         "metadata": {"diagnostic_classes": ["HYP"]}}
    ]
    _write_manifest(manifest, rows)
    ds = PTBXLDiagnosticDataset(manifest, split="train")
    w = _sample_weights(ds)
    # the lone HYP record must carry a much larger sampling weight
    assert w[-1] > w[0]


def test_warmup_cosine_scheduler_shape():
    import torch
    from ml.training.train_multilabel import _build_scheduler
    p = torch.nn.Parameter(torch.zeros(1))
    optim = torch.optim.SGD([p], lr=1.0)
    sched = _build_scheduler(optim, epochs=10, warmup_epochs=3)
    lrs = []
    for _ in range(10):
        lrs.append(optim.param_groups[0]["lr"])
        optim.step()
        sched.step()
    # warmup ramps up then cosine decays toward ~0
    assert lrs[0] < lrs[2] <= lrs[3]      # increasing during warmup
    assert lrs[-1] < lrs[3]               # decaying after
    assert lrs[-1] < 0.1


def test_transfer_backbone_loads_conv_drops_head():
    import torch
    from heartscan_ml.cnn1d import build_model
    from ml.training.train_multilabel import transfer_backbone
    # A 6-class pretrained deep net (CODE-15) -> transfer into a fresh 5-class net.
    pre = build_model("deep", num_classes=6, length=4096, in_channels=12)
    tgt = build_model("deep", num_classes=5, length=4096, in_channels=12)
    payload = pre.state_dict()
    n, missing, unexpected = transfer_backbone(tgt, payload)
    # Backbone tensors (stem/blocks) transfer; head.* excluded -> not unexpected.
    assert n > 0
    assert unexpected == 0           # no stray (head excluded from payload)
    # The target's stem weight now equals the pretrained one (transferred).
    assert torch.equal(tgt.stem[0].weight, pre.stem[0].weight)
    # Head stayed its own shape (5 classes), not overwritten by the 6-class head.
    assert tgt.head.weight.shape[0] == 5


def test_code15_auroc_helper():
    import numpy as np
    from ml.training.pretrain_code15 import _auroc
    y = np.array([0, 0, 1, 1])
    assert _auroc(y, np.array([0.1, 0.2, 0.8, 0.9])) == 1.0   # perfect ranking
    assert _auroc(y, np.array([0.9, 0.8, 0.2, 0.1])) == 0.0   # inverted
    assert abs(_auroc(y, np.array([0.5, 0.5, 0.5, 0.5])) - 0.5) < 1e-9  # ties


def test_dataset_27class_label_key(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    from ml.datasets.labels import CINC2020_27_CLASSES
    rec = tmp_path / "records100" / "00000" / "00001_lr"
    rec.parent.mkdir(parents=True)
    rec.with_suffix(".hea").write_text("stub\n")
    rec.with_suffix(".dat").write_bytes(b"x")
    manifest = tmp_path / "m.parquet"
    pq.write_table(pa.Table.from_pylist([{
        "file_path": str(rec), "label_id": 1, "sampling_rate_hz": 100, "n_leads": 12,
        "duration_s": 10.0, "source_dataset": "ptb_xl", "split": "train",
        "metadata": {"cinc2020_27": ["AF", "RBBB"]},
    }]), manifest)
    raw = np.tile(np.linspace(-1, 1, 1000, dtype=np.float32)[:, None], (1, 12))
    monkeypatch.setitem(sys.modules, "wfdb", SimpleNamespace(rdrecord=lambda _: SimpleNamespace(p_signal=raw)))
    ds = PTBXLDiagnosticDataset(manifest, split="train", classes=CINC2020_27_CLASSES, label_key="cinc2020_27")
    assert ds.classes == tuple(CINC2020_27_CLASSES)
    _, target = ds[0]
    assert target.shape[0] == len(CINC2020_27_CLASSES)
    # AF and RBBB positive, rest zero
    pos = {CINC2020_27_CLASSES[i] for i, v in enumerate(target.tolist()) if v == 1.0}
    assert pos == {"AF", "RBBB"}
