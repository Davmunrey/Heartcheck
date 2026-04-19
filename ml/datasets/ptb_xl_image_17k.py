"""PTB-XL-Image-17K — synthetic 12-lead ECG image dataset (CC BY 4.0).

17,271 ECG images rendered from PTB-XL with grid/no-grid variants,
pixel-level masks, YOLO bounding boxes, full ground-truth waveform.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ml.datasets._common import http_download
from ml.datasets.registry import CLASS_TO_ID, Dataset, Sample

_ARCHIVE_URL = "https://figshare.com/ndownloader/files/PTBXL-Image-17K.zip"  # placeholder; actual URL pinned in docs


def _download(target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    archive = target_dir / "PTBXL-Image-17K.zip"
    if not archive.is_file():
        http_download(_ARCHIVE_URL, archive)
    # Caller is expected to unzip; we don't auto-extract to keep audit trail.


def _parse(target_dir: Path) -> Iterator[Sample]:
    manifest = target_dir / "metadata.csv"
    if not manifest.is_file():
        raise FileNotFoundError(
            f"PTB-XL-Image-17K manifest not found at {manifest}; "
            f"unzip the archive after running download."
        )
    import csv

    from ml.datasets.labels import map_ptbxl_codes

    with manifest.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            codes = [c.strip() for c in (row.get("scp_codes") or "").split(";") if c.strip()]
            label = map_ptbxl_codes(codes) if codes else "noise"
            yield Sample(
                record_id=row["image_id"],
                label=label,
                label_id=CLASS_TO_ID[label],
                source_dataset="ptb_xl_image_17k",
                source_label=";".join(codes),
                file_path=target_dir / row["image_path"],
                sampling_rate_hz=100,
                n_leads=12,
                duration_s=10.0,
                metadata={
                    "has_grid": row.get("has_grid"),
                    "paper_speed_mm_s": row.get("paper_speed_mm_s"),
                },
            )


def dataset() -> Dataset:
    return Dataset(
        name="ptb_xl_image_17k",
        version="1.0",
        homepage="https://arxiv.org/abs/2602.07446",
        license="CC BY 4.0",
        license_class="permissive",
        citation="PTB-XL-Image-17K: synthetic ECG image dataset for digitization (2026).",
        expected_size_gb=20.0,
        download=_download,
        parse=_parse,
        notes="Synthetic but with comprehensive ground truth; pair with ECG-Image-Database.",
    )
