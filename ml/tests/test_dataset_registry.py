from __future__ import annotations

from ml.datasets._common import md5_file, verify_md5
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
