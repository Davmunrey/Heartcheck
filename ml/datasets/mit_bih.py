"""MIT-BIH Arrhythmia Database — historical benchmark (open).

48 half-hour 2-channel recordings, 360 Hz, ~110k beat annotations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ml.datasets._common import physionet_wget
from ml.datasets.registry import CLASS_TO_ID, Dataset, Sample

_PHYSIONET_SLUG = "mitdb/1.0.0"


def _download(target_dir: Path) -> None:
    physionet_wget(_PHYSIONET_SLUG, target_dir)


def _parse(target_dir: Path) -> Iterator[Sample]:
    records = target_dir / "RECORDS"
    if not records.is_file():
        raise FileNotFoundError(f"MIT-BIH RECORDS file not found at {records}")
    for rec in records.read_text(encoding="utf-8").splitlines():
        rec = rec.strip()
        if not rec:
            continue
        # Beat-level labels live in the .atr; for record-level harmonisation
        # to the 3 HeartScan classes, we conservatively label every record as
        # `arrhythmia` (the database is curated for arrhythmia detection).
        label = "arrhythmia"
        yield Sample(
            record_id=rec,
            label=label,
            label_id=CLASS_TO_ID[label],
            source_dataset="mit_bih",
            source_label="arrhythmia_record",
            file_path=target_dir / f"{rec}.dat",
            sampling_rate_hz=360,
            n_leads=2,
            duration_s=1800.0,
        )


def dataset() -> Dataset:
    return Dataset(
        name="mit_bih",
        version="1.0.0",
        homepage="https://physionet.org/content/mitdb/1.0.0/",
        license="ODC-By v1.0 (open)",
        license_class="permissive",
        citation="Moody GB, Mark RG. The impact of the MIT-BIH Arrhythmia Database. "
        "IEEE Eng Med Biol Mag 2001.",
        expected_size_gb=0.1,
        download=_download,
        parse=_parse,
        notes="Historical benchmark; small but obligatory for comparability.",
    )
