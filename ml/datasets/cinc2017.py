"""PhysioNet/CinC Challenge 2017 — single-lead AF classification (CC BY 4.0).

8,528 training records (private hidden test 3,658). 30 s mean,
sampled by AliveCor handheld 300 Hz nominal.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

from ml.datasets._common import physionet_wget
from ml.datasets.labels import map_cinc2017
from ml.datasets.registry import CLASS_TO_ID, Dataset, Sample

_PHYSIONET_SLUG = "challenge-2017/1.0.0"


def _download(target_dir: Path) -> None:
    physionet_wget(_PHYSIONET_SLUG, target_dir)


def _parse(target_dir: Path) -> Iterator[Sample]:
    ref = target_dir / "training" / "REFERENCE-v3.csv"
    if not ref.is_file():
        ref = target_dir / "training2017" / "REFERENCE-v3.csv"
    if not ref.is_file():
        raise FileNotFoundError(
            f"CinC2017 REFERENCE-v3.csv not found under {target_dir}; "
            f"run `python -m ml.datasets.cli download cinc2017` first."
        )
    base = ref.parent
    with ref.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 2:
                continue
            rec, code = row[0].strip(), row[1].strip()
            label = map_cinc2017(code)
            yield Sample(
                record_id=rec,
                label=label,
                label_id=CLASS_TO_ID[label],
                source_dataset="cinc2017",
                source_label=code,
                file_path=base / f"{rec}.mat",
                sampling_rate_hz=300,
                n_leads=1,
                duration_s=30.0,
            )


def dataset() -> Dataset:
    return Dataset(
        name="cinc2017",
        version="1.0.0",
        homepage="https://physionet.org/content/challenge-2017/1.0.0/",
        license="CC BY 4.0",
        license_class="permissive",
        citation="Clifford GD, Liu C, Moody B, et al. AF Classification from a Short Single "
        "Lead ECG Recording: PhysioNet/CinC Challenge 2017.",
        expected_size_gb=0.4,
        download=_download,
        parse=_parse,
        notes="Single-lead — ideal benchmark for HeartScan's photo-derived 1D signal.",
    )
