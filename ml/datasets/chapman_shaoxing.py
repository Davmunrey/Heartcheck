"""Chapman / Shaoxing People's Hospital / Ningbo First Hospital 12-lead (CC BY 4.0).

45,152 records, 500 Hz, 10 s, 90 SNOMED-CT codes.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

from ml.datasets._common import physionet_wget
from ml.datasets.labels import map_chapman_codes
from ml.datasets.registry import CLASS_TO_ID, Dataset, Sample

_PHYSIONET_SLUG = "ecg-arrhythmia/1.0.0"


def _download(target_dir: Path) -> None:
    physionet_wget(_PHYSIONET_SLUG, target_dir)


def _parse(target_dir: Path) -> Iterator[Sample]:
    # The PhysioNet release ships a master condition.csv plus per-record
    # WFDB triplets under WFDBRecords/.
    cond_csv = target_dir / "ConditionNames_SNOMED-CT.csv"
    diag_csv = target_dir / "Diagnostics.csv"
    if not diag_csv.is_file():
        raise FileNotFoundError(
            f"Chapman Diagnostics.csv not found at {diag_csv}; "
            f"run `python -m ml.datasets.cli download chapman_shaoxing` first."
        )
    with diag_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            codes = [c.strip() for c in (row.get("Rhythm", "") + ";" + row.get("Beat", "")).split(";") if c.strip()]
            label = map_chapman_codes(codes)
            file_id = row["FileName"]
            yield Sample(
                record_id=file_id,
                label=label,
                label_id=CLASS_TO_ID[label],
                source_dataset="chapman_shaoxing",
                source_label=";".join(codes),
                file_path=target_dir / "WFDBRecords" / f"{file_id}.mat",
                sampling_rate_hz=500,
                n_leads=12,
                duration_s=10.0,
                patient_id=file_id,
                metadata={"age": row.get("PatientAge"), "sex": row.get("Gender")},
            )
    # cond_csv kept for reference; not used at parse time
    _ = cond_csv


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
