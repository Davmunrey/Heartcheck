from __future__ import annotations

from ml.datasets._common import md5_file, verify_md5
from ml.datasets.chapman_shaoxing import dataset as chapman_dataset
from ml.datasets.cinc2020 import dataset as cinc2020_dataset
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


def test_snomed_cinc2020_expansion_codes():
    # Codes added with the CinC 2020 integration (2026-06-07): ischemia/ST→STTC,
    # atrial enlargement→HYP. These convert previously-dropped records into
    # supervision for the model's two weakest classes.
    assert diagnostic_superclasses_from_snomed(["164861001"]) == ["STTC"]  # ischemia
    assert diagnostic_superclasses_from_snomed(["55930002"]) == ["STTC"]   # ST changes
    assert diagnostic_superclasses_from_snomed(["67741000119109"]) == ["HYP"]  # LAE
    assert diagnostic_superclasses_from_snomed(["446358003"]) == ["HYP"]   # RAH
    # Rhythm / axis codes stay unmapped (belong to PTB-XL's non-diagnostic groups).
    assert diagnostic_superclasses_from_snomed(["164889003", "39732003"]) == []


def test_cinc2020_parser_walks_sources_and_excludes_ptbxl(tmp_path, monkeypatch):
    root = tmp_path / "cinc2020"
    for src in ("georgia", "ptb-xl"):
        d = root / "training" / src / "g1"
        d.mkdir(parents=True)
        hea = d / f"{src}_R1.hea"
        hea.write_text(f"{src}_R1 12 500 5000\n# Dx: 426783006,67741000119109\n", encoding="utf-8")
        hea.with_suffix(".mat").write_bytes(b"stub")

    # ptb-xl source is excluded by default → only the georgia record is emitted.
    monkeypatch.delenv("CINC2020_INCLUDE_PTBXL", raising=False)
    rows = list(cinc2020_dataset().parse(root))
    assert [r.record_id for r in rows] == ["georgia_R1"]
    assert rows[0].source_dataset == "cinc2020/georgia"
    assert rows[0].file_path.suffix == ".mat"
    assert rows[0].metadata["diagnostic_classes"] == ["HYP"]  # NORM dropped when abnormal co-occurs

    # Opt-in includes the ptb-xl copy.
    monkeypatch.setenv("CINC2020_INCLUDE_PTBXL", "1")
    rows2 = list(cinc2020_dataset().parse(root))
    assert {r.record_id for r in rows2} == {"georgia_R1", "ptb-xl_R1"}


def test_cinc2020_registered():
    assert REGISTRY["cinc2020"].license_class == "permissive"


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


def test_cinc2020_27class_taxonomy():
    from ml.datasets.labels import CINC2020_27_CLASSES, cinc2020_27_from_snomed
    # rhythm + diagnostic captured (was discarded by the 5-superclass head)
    assert cinc2020_27_from_snomed(["164889003"]) == ["AF"]          # atrial fib (rhythm!)
    assert cinc2020_27_from_snomed(["426783006"]) == ["SNR"]         # sinus rhythm
    # multi-label, returned in canonical order
    out = cinc2020_27_from_snomed(["59118001", "164889003", "164934002"])
    assert out == ["AF", "RBBB", "TAb"]
    # merged equivalents: VPB(17338001)->PVC, SVPB(63593006)->PAC
    assert cinc2020_27_from_snomed(["17338001"]) == ["PVC"]
    assert cinc2020_27_from_snomed(["63593006"]) == ["PAC"]
    assert len(CINC2020_27_CLASSES) >= 27  # CinC2020 27-set + a few blend extras
    assert cinc2020_27_from_snomed(["99999999"]) == []               # unknown -> empty


def test_cinc2020_27_from_ptbxl_scp():
    from ml.datasets.labels import cinc2020_27_from_ptbxl_scp
    # PTB-XL SCP codes map into the SAME 27-class space as SNOMED
    assert cinc2020_27_from_ptbxl_scp(["NORM"]) == ["SNR"]
    assert cinc2020_27_from_ptbxl_scp(["AFIB"]) == ["AF"]            # rhythm captured
    assert cinc2020_27_from_ptbxl_scp(["CRBBB"]) == ["RBBB"]         # merged equivalent
    out = cinc2020_27_from_ptbxl_scp(["AFIB", "1AVB", "IMI"])
    assert out == ["AF", "IAVB", "MI"]                              # canonical order
    assert cinc2020_27_from_ptbxl_scp(["UNKNOWN"]) == []
