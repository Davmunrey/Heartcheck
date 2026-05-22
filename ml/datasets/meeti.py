"""MEETI — multimodal ECG images/features/text derived from MIMIC-IV-ECG.

Zenodo record: https://zenodo.org/records/15893351

The public Zenodo package is CC BY 4.0 and contains ~10k multimodal samples.
It is useful for image/text/report workflows. The full MEETI corpus lives on
Hugging Face and is larger.
"""

from __future__ import annotations

import csv
import re
import zipfile
from pathlib import Path
from typing import Iterator

from ml.datasets._common import http_download
from ml.datasets.registry import CLASS_TO_ID, Dataset, Sample

_ZENODO_URL = "https://zenodo.org/records/15893351/files/MEETI.zip?download=1"
_MD5 = "5deb16ac5b50b08c43638544270a3115"


def _download(target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    zip_path = target_dir / "MEETI.zip"
    http_download(_ZENODO_URL, zip_path, expected_md5=_MD5)
    # Keep extraction explicit and idempotent; 3.3 GB zip can take time.
    extracted = target_dir / ".extracted"
    if not extracted.exists():
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(target_dir)
        extracted.write_text("ok\n", encoding="utf-8")


def _text_to_screening_label(text: str) -> str:
    s = text.lower()
    if re.search(r"\b(noise|artifact|poor quality|baseline wander)\b", s):
        return "noise"
    if re.search(
        r"\b(atrial fibrillation|flutter|tachycardia|bradycardia|premature|block|"
        r"infarct|ischemia|hypertrophy|st elevation|st depression|qt|qrs)\b",
        s,
    ):
        return "arrhythmia"
    if re.search(r"\b(normal|sinus rhythm)\b", s):
        return "normal"
    return "noise"


def _find_record_list(target_dir: Path) -> Path:
    candidates = list(target_dir.rglob("record_list.csv"))
    if not candidates:
        raise FileNotFoundError(
            f"MEETI record_list.csv not found under {target_dir}; download/extract MEETI.zip first."
        )
    return candidates[0]


def _parse(target_dir: Path) -> Iterator[Sample]:
    record_list = _find_record_list(target_dir)
    with record_list.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rel = row.get("path") or row.get("record_path") or row.get("file_path") or ""
            file_name = row.get("file_name") or row.get("study_id") or Path(rel).stem
            base = (record_list.parent / rel).with_suffix("") if rel else record_list.parent / file_name
            png = base.with_suffix(".png")
            mat = base.with_suffix(".mat")
            report = row.get("report") or row.get("interpretation") or row.get("LLM_Interpretation") or ""
            label = _text_to_screening_label(report)
            yield Sample(
                record_id=file_name,
                label=label,
                label_id=CLASS_TO_ID[label],
                source_dataset="meeti",
                source_label=report[:200],
                file_path=png if png.is_file() else mat,
                sampling_rate_hz=500,
                n_leads=12,
                duration_s=10.0,
                patient_id=row.get("subject_id"),
                metadata={
                    "record_list": str(record_list),
                    "mat_path": str(mat),
                    "png_path": str(png),
                    "report": report[:500],
                    "label_source": "rule_based_text_screening",
                },
            )


def dataset() -> Dataset:
    return Dataset(
        name="meeti",
        version="v1",
        homepage="https://zenodo.org/records/15893351",
        license="CC BY 4.0",
        license_class="permissive",
        citation="Zhang D, Lan X, Geng S, et al. MEETI: A Multimodal ECG Dataset from "
        "MIMIC-IV-ECG with Signals, Images, Features and Interpretations. Zenodo 2025.",
        expected_size_gb=3.3,
        download=_download,
        parse=_parse,
        notes="Multimodal ECG image/MAT/text subset; labels are rule-based from report text unless harmonized.",
    )
