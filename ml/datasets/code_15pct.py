"""CODE-15% — large Brazilian 12-lead ECG dataset (CC BY).

345,779 ECGs from 233,770 patients, sampled at 400 Hz, six labelled abnormalities.
Hosted on Zenodo (DOI 10.5281/zenodo.4916206).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Iterator

from ml.datasets._common import http_download
from ml.datasets.labels import map_code15
from ml.datasets.registry import CLASS_TO_ID, Dataset, Sample

_ZENODO_LANDING = "https://zenodo.org/records/4916206"
_ZENODO_FILES = [
    "exams.csv",
    "exams_part0.hdf5",
    "exams_part1.hdf5",
    # ... actual list pinned on the Zenodo record page.
]


def _download(target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    print(
        f"[manual] CODE-15% lives on Zenodo: {_ZENODO_LANDING}.\n"
        f"        Download every exams_partN.hdf5 (~50 GB total) and exams.csv into {target_dir}.",
        file=sys.stderr,
    )


def _parse(target_dir: Path) -> Iterator[Sample]:
    meta = target_dir / "exams.csv"
    if not meta.is_file():
        raise FileNotFoundError(
            f"CODE-15% exams.csv not found at {meta}; see {_ZENODO_LANDING}."
        )
    with meta.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            label = map_code15(row)
            yield Sample(
                record_id=row["exam_id"],
                label=label,
                label_id=CLASS_TO_ID[label],
                source_dataset="code_15pct",
                source_label=";".join(k for k in ("1dAVb", "RBBB", "LBBB", "SB", "ST", "AF") if int(row.get(k, 0)) == 1) or "normal",
                file_path=target_dir / row["trace_file"],
                sampling_rate_hz=400,
                n_leads=12,
                duration_s=float(row.get("seconds", 10.0)),
                patient_id=row.get("patient_id"),
                metadata={
                    "age": row.get("age"),
                    "is_male": row.get("is_male"),
                    "death": row.get("death"),
                },
            )


def dataset() -> Dataset:
    return Dataset(
        name="code_15pct",
        version="1.0",
        homepage=_ZENODO_LANDING,
        license="CC BY 4.0",
        license_class="permissive",
        citation="Ribeiro AH et al. CODE-15%: a large scale annotated dataset of 12-lead "
        "ECGs (Zenodo 4916206).",
        expected_size_gb=50.0,
        download=_download,
        parse=_parse,
        notes="Brazilian population diversity; complement to PTB-XL/Chapman.",
    )
