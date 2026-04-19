"""MIMIC-IV-ECG — Diagnostic Electrocardiogram Matched Subset (ODbL v1.0).

~800,000 12-lead ECGs across ~160,000 unique patients, BIDMC Boston.
Requires PhysioNet credentialed access (CITI training certificate).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Iterator

from ml.datasets._common import physionet_wget
from ml.datasets.labels import map_chapman_codes
from ml.datasets.registry import CLASS_TO_ID, Dataset, Sample

_PHYSIONET_SLUG = "mimic-iv-ecg/1.0"


def _download(target_dir: Path) -> None:
    print(
        "[restricted] MIMIC-IV-ECG requires PhysioNet credentialed access:\n"
        "  1. Complete CITI 'Data or Specimens Only Research'.\n"
        "  2. Submit certificate to PhysioNet.\n"
        "  3. Sign the data use agreement.\n"
        "Then run wget with --user / --ask-password against PhysioNet.",
        file=sys.stderr,
    )
    physionet_wget(_PHYSIONET_SLUG, target_dir)


def _parse(target_dir: Path) -> Iterator[Sample]:
    meta = target_dir / "machine_measurements.csv"
    if not meta.is_file():
        raise FileNotFoundError(
            f"MIMIC-IV-ECG metadata not found at {meta}; ensure access + download completed."
        )
    with meta.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # `report` columns 0..17 hold human-readable statements; for
            # harmonisation we rely on the SNOMED-style mapping shared with
            # Chapman where applicable.
            statements = [v for k, v in row.items() if k.startswith("report_") and v]
            codes = []  # MIMIC-IV-ECG ships free text; downstream NLP needed
            label = map_chapman_codes(codes) if codes else "noise"
            yield Sample(
                record_id=row["study_id"],
                label=label,
                label_id=CLASS_TO_ID[label],
                source_dataset="mimic_iv_ecg",
                source_label=";".join(statements)[:200],
                file_path=target_dir / row["path"],
                sampling_rate_hz=500,
                n_leads=12,
                duration_s=10.0,
                patient_id=row.get("subject_id"),
                metadata={"ecg_time": row.get("ecg_time")},
            )


def dataset() -> Dataset:
    return Dataset(
        name="mimic_iv_ecg",
        version="1.0",
        homepage="https://physionet.org/content/mimic-iv-ecg/1.0/",
        license="ODbL v1.0 (database) + clinical content rights",
        license_class="restricted",
        citation="Gow B et al. MIMIC-IV-ECG: Diagnostic Electrocardiogram Matched Subset. "
        "PhysioNet 2023.",
        expected_size_gb=95.0,
        download=_download,
        parse=_parse,
        notes="Free-text reports require NLP to harmonise; consider running CardiX or "
        "rule-based extraction before training.",
    )
