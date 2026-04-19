"""SPH (Shandong Provincial Hospital) 12-lead ECG (CC BY 4.0).

25,770 records / 24,666 patients, 500 Hz, 10–60 s, AHA/ACC/HRS statements.
Mendeley Data, not PhysioNet.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Iterator

from ml.datasets._common import http_download
from ml.datasets.labels import map_sph
from ml.datasets.registry import CLASS_TO_ID, Dataset, Sample

_MENDELEY_LANDING = "https://data.mendeley.com/datasets/g23n565xh3/1"


def _download(target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    print(
        f"[manual] SPH is hosted on Mendeley Data ({_MENDELEY_LANDING}); "
        f"download the ZIPs manually and unpack into {target_dir} preserving the layout.",
        file=sys.stderr,
    )


def _parse(target_dir: Path) -> Iterator[Sample]:
    meta = target_dir / "metadata.csv"
    if not meta.is_file():
        raise FileNotFoundError(
            f"SPH metadata.csv not found at {meta}; download from {_MENDELEY_LANDING}."
        )
    with meta.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            statements = [s.strip() for s in (row.get("Statement", "") or "").split(";") if s.strip()]
            label = map_sph(statements)
            yield Sample(
                record_id=row["ECG_ID"],
                label=label,
                label_id=CLASS_TO_ID[label],
                source_dataset="sph",
                source_label=";".join(statements),
                file_path=target_dir / "records" / f"{row['ECG_ID']}.h5",
                sampling_rate_hz=500,
                n_leads=12,
                duration_s=float(row.get("ECG_Duration", 10.0)),
                patient_id=row.get("Patient_ID"),
                metadata={"age": row.get("Age"), "sex": row.get("Sex")},
            )


def dataset() -> Dataset:
    return Dataset(
        name="sph",
        version="1.0",
        homepage=_MENDELEY_LANDING,
        license="CC BY 4.0",
        license_class="permissive",
        citation="Liu H et al. A large-scale multi-label 12-lead ECG database with "
        "standardized diagnostic statements. Sci Data 2022.",
        expected_size_gb=8.0,
        download=_download,
        parse=_parse,
        notes="Mendeley host; manual download.",
    )
