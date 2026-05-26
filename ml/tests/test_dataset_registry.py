from __future__ import annotations

from ml.datasets._common import md5_file, verify_md5
from ml.datasets.chapman_shaoxing import dataset as chapman_dataset
from ml.datasets.code_15pct import dataset as code15_dataset
from ml.datasets.georgia12 import dataset as georgia12_dataset
from ml.datasets.labels import diagnostic_superclasses_from_snomed
from ml.datasets.mit_bih import dataset as mit_bih_dataset
from ml.datasets.registry import REGISTRY


def test_md5_verification(tmp_path):
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"heartcheck")

    digest = md5_file(payload)
    verify_md5(payload, digest)

    assert digest == "a5ed1b74b6831c5bfd5a9c5c277e4e06"


def test_mit_bih_parser_accepts_physionet_nested_root(tmp_path):
    root = tmp_path / "mit_bih"
    nested = root / "1.0.0"
    nested.mkdir(parents=True)
    (nested / "RECORDS").write_text("100\n200\n", encoding="utf-8")

    rows = list(mit_bih_dataset().parse(root))

    assert [r.record_id for r in rows] == ["100", "200"]
    assert [r.label for r in rows] == ["normal", "arrhythmia"]
    assert rows[0].file_path == nested / "100.dat"


def test_meeti_registered():
    ds = REGISTRY["meeti"]

    assert ds.license_class == "permissive"
    assert ds.homepage == "https://zenodo.org/records/15893351"


def test_snomed_diagnostic_superclass_mapping():
    assert diagnostic_superclasses_from_snomed(["426783006"]) == ["NORM"]
    assert diagnostic_superclasses_from_snomed(["164909002", "164873001"]) == ["CD", "HYP"]
    assert diagnostic_superclasses_from_snomed(["426783006", "164934002"]) == ["STTC"]


def test_georgia_parser_accepts_physionet_nested_root(tmp_path):
    root = tmp_path / "georgia12"
    nested = root / "1.0.2" / "training" / "georgia" / "g1"
    nested.mkdir(parents=True)
    header = nested / "E00001.hea"
    header.write_text("E00001 12 500 5000\n# Dx: 426783006,164909002\n", encoding="utf-8")
    header.with_suffix(".mat").write_bytes(b"stub")

    rows = list(georgia12_dataset().parse(root))

    assert len(rows) == 1
    assert rows[0].record_id == "E00001"
    assert rows[0].file_path == header.with_suffix(".mat")
    assert rows[0].metadata["diagnostic_classes"] == ["CD"]


def test_chapman_parser_accepts_physionet_nested_headers(tmp_path):
    root = tmp_path / "chapman_shaoxing"
    nested = root / "1.0.0" / "WFDBRecords" / "01" / "001"
    nested.mkdir(parents=True)
    header = nested / "JS00001.hea"
    header.write_text(
        "JS00001 12 500 5000\n"
        "#Age: 70\n"
        "#Sex: Female\n"
        "#Dx: 426783006,164909002\n",
        encoding="utf-8",
    )
    header.with_suffix(".mat").write_bytes(b"stub")

    rows = list(chapman_dataset().parse(root))

    assert len(rows) == 1
    assert rows[0].record_id == "JS00001"
    assert rows[0].file_path == header.with_suffix(".mat")
    assert rows[0].metadata["diagnostic_classes"] == ["CD"]


def test_code15_parser_filters_existing_hdf5_and_emits_diagnostic_classes(tmp_path):
    root = tmp_path / "code_15pct"
    root.mkdir()
    (root / "exams_part0.hdf5").write_bytes(b"stub")
    (root / "exams.csv").write_text(
        "exam_id,age,is_male,1dAVb,RBBB,LBBB,SB,ST,AF,patient_id,death,normal_ecg,trace_file\n"
        "1,50,True,False,True,False,False,False,False,p1,False,False,exams_part0.hdf5\n"
        "2,60,False,False,False,False,False,False,False,p2,False,True,missing.hdf5\n",
        encoding="utf-8",
    )

    rows = list(code15_dataset().parse(root))

    assert len(rows) == 1
    assert str(rows[0].file_path).endswith("exams_part0.hdf5::1")
    assert rows[0].source_label == "RBBB"
    assert rows[0].metadata["diagnostic_classes"] == ["CD"]
