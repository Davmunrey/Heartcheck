"""PTB-XL — gold standard 12-lead clinical ECG (CC BY 4.0).

21,837 records / 18,885 patients, 10 s, 500/100 Hz.
Annotated by up to two cardiologists with 71 SCP-ECG statements.
"""

from __future__ import annotations

import ast
import csv
from pathlib import Path
from typing import Iterator

from ml.datasets._common import physionet_wget
from ml.datasets.labels import map_ptbxl_codes
from ml.datasets.registry import CLASS_TO_ID, Dataset, Sample

_PHYSIONET_SLUG = "ptb-xl/1.0.3"


def _download(target_dir: Path) -> None:
    physionet_wget(_PHYSIONET_SLUG, target_dir)


def _parse(target_dir: Path) -> Iterator[Sample]:
    csv_path = target_dir / "ptbxl_database.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"PTB-XL CSV not found at {csv_path}; run "
            f"`python -m ml.datasets.cli download ptb_xl` first."
        )
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            scp = ast.literal_eval(row["scp_codes"]) if row.get("scp_codes") else {}
            label = map_ptbxl_codes(scp.keys())
            rec_path = target_dir / row["filename_lr"]  # 100 Hz
            yield Sample(
                record_id=str(row["ecg_id"]),
                label=label,
                label_id=CLASS_TO_ID[label],
                source_dataset="ptb_xl",
                source_label=";".join(scp.keys()),
                file_path=rec_path,
                sampling_rate_hz=100,
                n_leads=12,
                duration_s=10.0,
                patient_id=str(row.get("patient_id") or ""),
                metadata={
                    "age": row.get("age"),
                    "sex": row.get("sex"),
                    "strat_fold": row.get("strat_fold"),
                    "report": row.get("report", "")[:200],
                },
            )


def dataset() -> Dataset:
    return Dataset(
        name="ptb_xl",
        version="1.0.3",
        homepage="https://physionet.org/content/ptb-xl/1.0.3/",
        license="CC BY 4.0",
        license_class="permissive",
        citation="Wagner P, Strodthoff N, Bousseljot RD, et al. PTB-XL, a large publicly "
        "available electrocardiography dataset (v1.0.3). PhysioNet 2022.",
        expected_size_gb=3.2,
        download=_download,
        parse=_parse,
        notes="Gold standard for benchmarking; ships pre-built train/val/test stratified folds (1-10).",
    )
