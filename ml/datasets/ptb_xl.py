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


def _load_scp_statements(target_dir: Path) -> dict[str, dict[str, str]]:
    path = target_dir / "scp_statements.csv"
    if not path.is_file():
        return {}
    out: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = str(row.get("") or "").strip()
            if code:
                out[code] = row
    return out


def _download(target_dir: Path) -> None:
    physionet_wget(_PHYSIONET_SLUG, target_dir)


def _data_root(target_dir: Path) -> Path:
    candidates = [
        target_dir,
        target_dir / "1.0.3",
        target_dir / "ptb-xl-a-large-publicly-available-electrocardiography-dataset-1.0.3",
    ]
    valid = [
        candidate
        for candidate in candidates
        if (candidate / "ptbxl_database.csv").is_file() and (candidate / "records100").is_dir()
    ]
    if not valid:
        return target_dir
    return max(valid, key=lambda p: sum(1 for _ in (p / "records100").rglob("*.dat")))


def _parse(target_dir: Path) -> Iterator[Sample]:
    data_root = _data_root(target_dir)
    csv_path = data_root / "ptbxl_database.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"PTB-XL CSV not found at {csv_path}; run "
            f"`python -m ml.datasets.cli download ptb_xl` first."
        )
    scp_statements = _load_scp_statements(data_root)
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            scp = ast.literal_eval(row["scp_codes"]) if row.get("scp_codes") else {}
            label = map_ptbxl_codes(scp.keys())
            scp_codes = sorted(str(code) for code in scp)
            diagnostic_classes = sorted(
                {
                    str(scp_statements.get(code, {}).get("diagnostic_class") or "").strip()
                    for code in scp_codes
                    if str(scp_statements.get(code, {}).get("diagnostic") or "").strip() == "1.0"
                }
                - {""}
            )
            diagnostic_subclasses = sorted(
                {
                    str(scp_statements.get(code, {}).get("diagnostic_subclass") or "").strip()
                    for code in scp_codes
                    if str(scp_statements.get(code, {}).get("diagnostic") or "").strip() == "1.0"
                }
                - {""}
            )
            rec_path = data_root / row["filename_lr"]  # 100 Hz
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
                    "scp_codes": scp,
                    "scp_code_list": scp_codes,
                    "diagnostic_classes": diagnostic_classes,
                    "diagnostic_subclasses": diagnostic_subclasses,
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
