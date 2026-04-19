"""Georgia 12-Lead ECG Challenge Database (CC BY 4.0) — part of CinC 2020.

10,344 records 500 Hz, Emory Healthcare.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

from ml.datasets._common import physionet_wget
from ml.datasets.labels import map_chapman_codes  # SNOMED-CT shared with Chapman
from ml.datasets.registry import CLASS_TO_ID, Dataset, Sample

_PHYSIONET_SLUG = "challenge-2020/1.0.2/training/georgia"


def _download(target_dir: Path) -> None:
    physionet_wget(_PHYSIONET_SLUG, target_dir)


def _parse(target_dir: Path) -> Iterator[Sample]:
    summary = target_dir / "RECORDS"
    if not summary.is_file():
        raise FileNotFoundError(
            f"Georgia12 RECORDS file not found at {summary}; "
            f"run `python -m ml.datasets.cli download georgia12` first."
        )
    for line in summary.read_text(encoding="utf-8").splitlines():
        rec = line.strip()
        if not rec:
            continue
        hea = target_dir / f"{rec}.hea"
        if not hea.is_file():
            continue
        # Header lines starting with `# Dx:` carry SNOMED-CT codes.
        codes: list[str] = []
        for hl in hea.read_text(encoding="utf-8").splitlines():
            if hl.startswith("# Dx:"):
                codes.extend(c.strip() for c in hl.split(":", 1)[1].split(","))
        label = map_chapman_codes(codes) if codes else "noise"
        yield Sample(
            record_id=rec,
            label=label,
            label_id=CLASS_TO_ID[label],
            source_dataset="georgia12",
            source_label=";".join(codes),
            file_path=target_dir / f"{rec}.mat",
            sampling_rate_hz=500,
            n_leads=12,
            duration_s=10.0,
        )


def dataset() -> Dataset:
    return Dataset(
        name="georgia12",
        version="1.0.2",
        homepage="https://physionet.org/content/challenge-2020/1.0.2/",
        license="CC BY 4.0",
        license_class="permissive",
        citation="Perez Alday EA et al. Classification of 12-lead ECGs: PhysioNet/CinC "
        "Challenge 2020 (v1.0.2).",
        expected_size_gb=1.0,
        download=_download,
        parse=_parse,
    )
