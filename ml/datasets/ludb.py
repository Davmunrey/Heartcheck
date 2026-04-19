"""Lobachevsky University Database (LUDB) — 200 records with cardiologist
delineation of P/QRS/T (open via PhysioNet).

Used by HeartScan to validate R-peak detection and to seed segmentation
training for the U-Net trace extractor.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ml.datasets._common import physionet_wget
from ml.datasets.registry import CLASS_TO_ID, Dataset, Sample

_PHYSIONET_SLUG = "ludb/1.0.1"


def _download(target_dir: Path) -> None:
    physionet_wget(_PHYSIONET_SLUG, target_dir)


def _parse(target_dir: Path) -> Iterator[Sample]:
    records = target_dir / "RECORDS"
    if not records.is_file():
        raise FileNotFoundError(f"LUDB RECORDS file not found at {records}")
    for rec in records.read_text(encoding="utf-8").splitlines():
        rec = rec.strip()
        if not rec:
            continue
        yield Sample(
            record_id=rec,
            label="normal",  # placeholder; LUDB is for delineation, not classification
            label_id=CLASS_TO_ID["normal"],
            source_dataset="ludb",
            source_label="delineation",
            file_path=target_dir / "data" / f"{rec}.dat",
            sampling_rate_hz=500,
            n_leads=12,
            duration_s=10.0,
            metadata={"annotation_role": "P/QRS/T_delineation"},
        )


def dataset() -> Dataset:
    return Dataset(
        name="ludb",
        version="1.0.1",
        homepage="https://physionet.org/content/ludb/1.0.1/",
        license="ODC-By v1.0 (open)",
        license_class="permissive",
        citation="Kalyakulina AI et al. LUDB: a new open-access validation tool for "
        "ECG delineation algorithms. PhysioNet 2021.",
        expected_size_gb=0.05,
        download=_download,
        parse=_parse,
        notes="Critical for R-peak / Pan-Tompkins validation and U-Net mask training.",
    )
