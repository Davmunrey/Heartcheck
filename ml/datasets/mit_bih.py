"""MIT-BIH Arrhythmia Database — historical benchmark (open).

48 half-hour 2-channel recordings, 360 Hz, ~110k beat annotations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ml.datasets._common import physionet_wget
from ml.datasets.registry import CLASS_TO_ID, Dataset, Sample

_PHYSIONET_SLUG = "mitdb/1.0.0"

# MIT-BIH records whose dominant rhythm is normal sinus rhythm (NSR).
# These 8 records were selected from the 48 total as predominantly NSR by
# Moody & Mark; the remaining 40 were specifically selected for arrhythmia
# content and should remain labelled "arrhythmia".
MIT_BIH_NSR_RECORDS = {100, 103, 105, 111, 112, 113, 121, 122}


def _download(target_dir: Path) -> None:
    physionet_wget(_PHYSIONET_SLUG, target_dir)


def _data_root(target_dir: Path) -> Path:
    if (target_dir / "RECORDS").is_file():
        return target_dir
    nested = target_dir / "1.0.0"
    if (nested / "RECORDS").is_file():
        return nested
    return target_dir


def _parse(target_dir: Path) -> Iterator[Sample]:
    data_root = _data_root(target_dir)
    records = data_root / "RECORDS"
    if not records.is_file():
        raise FileNotFoundError(f"MIT-BIH RECORDS file not found at {records}")
    for rec in records.read_text(encoding="utf-8").splitlines():
        rec = rec.strip()
        if not rec:
            continue
        # Derive label from record number: a small subset of MIT-BIH records
        # are predominantly normal sinus rhythm; the rest are arrhythmia.
        try:
            rec_num = int(rec)
        except ValueError:
            rec_num = -1
        label = "normal" if rec_num in MIT_BIH_NSR_RECORDS else "arrhythmia"
        yield Sample(
            record_id=rec,
            label=label,
            label_id=CLASS_TO_ID[label],
            source_dataset="mit_bih",
            source_label="nsr_record" if label == "normal" else "arrhythmia_record",
            file_path=data_root / f"{rec}.dat",
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
