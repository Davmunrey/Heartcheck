"""Icentia11k — single-lead Holter dataset (CC BY-NC-SA 4.0, NON-COMMERCIAL).

11,000 patients, 2 billion labelled beats. **Not usable in a commercial
build** of HeartScan. Useful for internal research and pretraining whose
weights never ship to the production app.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterator

from ml.datasets._common import physionet_wget
from ml.datasets.registry import CLASS_TO_ID, Dataset, Sample

_PHYSIONET_SLUG = "icentia11k-continuous-ecg/1.0"


def _download(target_dir: Path) -> None:
    print(
        "[license] Icentia11k is CC BY-NC-SA 4.0; verify with legal before any "
        "commercial use of derived weights.",
        file=sys.stderr,
    )
    physionet_wget(_PHYSIONET_SLUG, target_dir)


def _parse(target_dir: Path) -> Iterator[Sample]:
    # The dataset ships beat-level labels; record-level mapping is conservative.
    records = list((target_dir).rglob("*.hea"))
    if not records:
        raise FileNotFoundError(f"No WFDB headers found under {target_dir}")
    for hea in records:
        rec_id = hea.stem
        yield Sample(
            record_id=rec_id,
            label="arrhythmia",  # Holter from arrhythmia screening cohort
            label_id=CLASS_TO_ID["arrhythmia"],
            source_dataset="icentia11k",
            source_label="continuous_holter",
            file_path=hea.with_suffix(".dat"),
            sampling_rate_hz=250,
            n_leads=1,
            duration_s=1209600.0,  # up to 2 weeks
        )


def dataset() -> Dataset:
    return Dataset(
        name="icentia11k",
        version="1.0",
        homepage="https://physionet.org/content/icentia11k-continuous-ecg/1.0/",
        license="CC BY-NC-SA 4.0",
        license_class="non_commercial",
        citation="Tan S et al. Icentia11k: an Unsupervised Representation Learning "
        "Dataset for Arrhythmia Subtype Discovery. CinC 2021.",
        expected_size_gb=1100.0,
        download=_download,
        parse=_parse,
        notes="NON-COMMERCIAL. Shippable only after a license-cleared replacement is found.",
    )
