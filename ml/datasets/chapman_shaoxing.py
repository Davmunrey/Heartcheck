"""Chapman / Shaoxing People's Hospital / Ningbo First Hospital 12-lead (CC BY 4.0).

45,152 records, 500 Hz, 10 s, 90 SNOMED-CT codes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ml.datasets._common import physionet_wget
from ml.datasets.labels import diagnostic_superclasses_from_snomed, map_chapman_codes
from ml.datasets.registry import CLASS_TO_ID, Dataset, Sample

_PHYSIONET_SLUG = "ecg-arrhythmia/1.0.0"


def _download(target_dir: Path) -> None:
    physionet_wget(_PHYSIONET_SLUG, target_dir)


def _parse(target_dir: Path) -> Iterator[Sample]:
    # PhysioNet wget commonly creates target/1.0.0/WFDBRecords. Older mirrors
    # may also include Diagnostics.csv; current release carries labels in .hea.
    root = target_dir
    nested = target_dir / "1.0.0"
    if nested.is_dir():
        root = nested
    wfdb_root = root / "WFDBRecords"
    if not wfdb_root.is_dir():
        raise FileNotFoundError(
            f"Chapman WFDBRecords not found at {wfdb_root}; "
            f"run `python -m ml.datasets.cli download chapman_shaoxing` first."
        )
    for hea in sorted(wfdb_root.rglob("*.hea")):
        codes: list[str] = []
        age: str | None = None
        sex: str | None = None
        for line in hea.read_text(encoding="utf-8").splitlines():
            if line.startswith("#Dx:"):
                codes.extend(c.strip() for c in line.split(":", 1)[1].split(",") if c.strip())
            elif line.startswith("#Age:"):
                age = line.split(":", 1)[1].strip()
            elif line.startswith("#Sex:"):
                sex = line.split(":", 1)[1].strip()
        label = map_chapman_codes(codes) if codes else "noise"
        file_id = hea.with_suffix("").name
        yield Sample(
            record_id=file_id,
            label=label,
            label_id=CLASS_TO_ID[label],
            source_dataset="chapman_shaoxing",
            source_label=";".join(codes),
            file_path=hea.with_suffix(".mat"),
            sampling_rate_hz=500,
            n_leads=12,
            duration_s=10.0,
            patient_id=file_id,
            metadata={
                "age": age,
                "sex": sex,
                "diagnostic_classes": diagnostic_superclasses_from_snomed(codes),
            },
        )


def dataset() -> Dataset:
    return Dataset(
        name="chapman_shaoxing",
        version="1.0.0",
        homepage="https://physionet.org/content/ecg-arrhythmia/1.0.0/",
        license="CC BY 4.0",
        license_class="permissive",
        citation="Zheng J, Guo H, Chu H. A large scale 12-lead electrocardiogram database "
        "for arrhythmia study (v1.0.0). PhysioNet 2022.",
        expected_size_gb=2.0,
        download=_download,
        parse=_parse,
        notes="Excellent rhythm-class diversity; SNOMED-CT codes mapped via labels.map_chapman_codes.",
    )
