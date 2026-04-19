"""ECG-Image-Database (PhysioNet 2024 Challenge) — CC BY 4.0.

35,595 software-labeled ECG images with real-world artifacts: noise, wrinkles,
stains, perspective, photographs of computer monitors. Built from PTB-XL +
Emory Healthcare. **The most directly relevant dataset for HeartScan**.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

from ml.datasets._common import physionet_wget
from ml.datasets.labels import map_ptbxl_codes
from ml.datasets.registry import CLASS_TO_ID, Dataset, Sample

_PHYSIONET_SLUG = "ecg-image-database/1.0.0"


def _download(target_dir: Path) -> None:
    physionet_wget(_PHYSIONET_SLUG, target_dir)


def _parse(target_dir: Path) -> Iterator[Sample]:
    manifest = target_dir / "manifest.csv"
    if not manifest.is_file():
        raise FileNotFoundError(
            f"ECG-Image-Database manifest not found at {manifest}; "
            f"run `python -m ml.datasets.cli download ecg_image_database` first."
        )
    with manifest.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            codes = [c.strip() for c in (row.get("scp_codes") or "").split(";") if c.strip()]
            label = map_ptbxl_codes(codes) if codes else "noise"
            yield Sample(
                record_id=row["image_id"],
                label=label,
                label_id=CLASS_TO_ID[label],
                source_dataset="ecg_image_database",
                source_label=";".join(codes),
                file_path=target_dir / row["image_path"],
                sampling_rate_hz=100,
                n_leads=12,
                duration_s=10.0,
                patient_id=row.get("patient_id"),
                metadata={"artifact": row.get("artifact"), "source": row.get("source")},
            )


def dataset() -> Dataset:
    return Dataset(
        name="ecg_image_database",
        version="1.0.0",
        homepage="https://moody-challenge.physionet.org/2024/",
        license="CC BY 4.0",
        license_class="permissive",
        citation="Reyna MA et al. ECG-Image-Database: a foundation for computerized ECG "
        "image digitization and analysis (PhysioNet/CinC 2024).",
        expected_size_gb=60.0,
        download=_download,
        parse=_parse,
        notes="Critical: image domain matches HeartScan exactly; use for fine-tuning.",
    )
