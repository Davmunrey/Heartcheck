"""Brno University of Technology ECG Quality Database (BUT QDB) — CC BY 4.0.

18 long-term single-lead ECG recordings with 3-class quality annotations
(usable / partially-usable / unusable). Used to train HeartScan's quality gate.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

from ml.datasets._common import physionet_wget
from ml.datasets.registry import CLASS_TO_ID, Dataset, Sample

_PHYSIONET_SLUG = "butqdb/1.0.0"


def _download(target_dir: Path) -> None:
    physionet_wget(_PHYSIONET_SLUG, target_dir)


def _parse(target_dir: Path) -> Iterator[Sample]:
    """Yield one Sample per annotated quality segment.

    We don't predict class here (quality DB has no normal/arrhythmia labels);
    everything is yielded as ``noise`` and consumed by the quality-gate
    training pipeline separately. Downstream code can filter on
    ``metadata['quality_class']``.
    """
    ann_csv = target_dir / "annotation_summary.csv"
    if not ann_csv.is_file():
        raise FileNotFoundError(
            f"BUT QDB summary CSV not found at {ann_csv}; "
            f"run `python -m ml.datasets.cli download but_qdb` first."
        )
    with ann_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield Sample(
                record_id=row["record"],
                label="noise",
                label_id=CLASS_TO_ID["noise"],
                source_dataset="but_qdb",
                source_label=row.get("quality_class", ""),
                file_path=target_dir / row["record"],
                sampling_rate_hz=1000,
                n_leads=1,
                duration_s=float(row.get("duration_s", 0.0) or 0.0),
                metadata={"quality_class": row.get("quality_class")},
            )


def dataset() -> Dataset:
    return Dataset(
        name="but_qdb",
        version="1.0.0",
        homepage="https://physionet.org/content/butqdb/1.0.0/",
        license="CC BY 4.0",
        license_class="permissive",
        citation="Nemcova A et al. BUT QDB: Brno University of Technology ECG Quality "
        "Database. PhysioNet 2020.",
        expected_size_gb=2.5,
        download=_download,
        parse=_parse,
        notes="Used to train the quality gate (PHOTO_BLURRY / SIGNAL_EXTRACTION_POOR).",
    )
