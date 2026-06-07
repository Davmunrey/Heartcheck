"""PhysioNet/CinC 2020 Challenge — 12-lead ECG, multi-source (CC BY 4.0).

43,101 records across six source databases, all WFDB ``.mat`` + ``.hea`` with
SNOMED-CT diagnosis codes in the ``# Dx:`` header line. We harmonise those codes
to the five PTB-XL diagnostic superclasses (NORM/MI/STTC/CD/HYP) via
:func:`ml.datasets.labels.diagnostic_superclasses_from_snomed`.

Why this dataset matters: the multi-source blend (CPSC, Georgia, INCART, PTB)
contributes thousands of records for the classes the PTB-XL-only model is weak
on — left-atrial/ventricular hypertrophy (HYP) and ischemic ST/T change (STTC).

The ``ptb-xl`` source folder is **excluded by default**: we already train against
the full native PTB-XL 1.0.3 (21,799 records at 100/500 Hz) as its own dataset,
so re-emitting the CinC2020 copy would duplicate records across a blended
manifest. Set ``CINC2020_INCLUDE_PTBXL=1`` to override.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

from ml.datasets.labels import diagnostic_superclasses_from_snomed, map_chapman_codes
from ml.datasets.registry import CLASS_TO_ID, Dataset, Sample

# Source sub-databases shipped under ``training/``. Per-source sampling rates
# differ (INCART is 257 Hz, the rest 500 Hz) — read from each header instead.
_SOURCES = (
    "cpsc_2018",
    "cpsc_2018_extra",
    "georgia",
    "ptb",
    "st_petersburg_incart",
    # "ptb-xl" intentionally excluded; see module docstring.
)


def _download(target_dir: Path) -> None:  # pragma: no cover - large manual download
    raise NotImplementedError(
        "CinC2020 is large (~3 GB). Download the PhysioNet release manually "
        "(challenge-2020/1.0.2) and point the manifest --root at it."
    )


def _training_root(target_dir: Path) -> Path:
    """Find the directory that contains the source sub-folders."""
    for candidate in (target_dir / "training", target_dir):
        if any((candidate / s).is_dir() for s in _SOURCES):
            return candidate
    return target_dir


def _read_header(hea: Path) -> tuple[list[str], int]:
    """Return (SNOMED codes, sampling_rate_hz) from a WFDB header."""
    codes: list[str] = []
    fs = 500
    lines = hea.read_text(encoding="utf-8", errors="ignore").splitlines()
    if lines:
        parts = lines[0].split()
        if len(parts) >= 3 and parts[2].replace(".", "").isdigit():
            fs = int(float(parts[2]))
    for hl in lines:
        if hl.startswith("# Dx:"):
            codes.extend(c.strip() for c in hl.split(":", 1)[1].split(",") if c.strip())
    return codes, fs


def _parse(target_dir: Path) -> Iterator[Sample]:
    root = _training_root(target_dir)
    sources = list(_SOURCES)
    if os.environ.get("CINC2020_INCLUDE_PTBXL") == "1":
        sources.append("ptb-xl")
    found_any = False
    for src in sources:
        src_dir = root / src
        if not src_dir.is_dir():
            continue
        # Records may sit directly under the source or in g1/g2/... shards.
        headers = sorted(src_dir.glob("*/*.hea")) or sorted(src_dir.glob("*.hea"))
        for hea in headers:
            found_any = True
            codes, fs = _read_header(hea)
            label = map_chapman_codes(codes) if codes else "noise"
            yield Sample(
                record_id=hea.with_suffix("").name,
                label=label,
                label_id=CLASS_TO_ID[label],
                source_dataset=f"cinc2020/{src}",
                source_label=";".join(codes),
                file_path=hea.with_suffix(".mat"),
                sampling_rate_hz=fs,
                n_leads=12,
                duration_s=10.0,
                metadata={"diagnostic_classes": diagnostic_superclasses_from_snomed(codes)},
            )
    if not found_any:
        raise FileNotFoundError(
            f"No CinC2020 WFDB headers under {root}; expected source folders "
            f"{_SOURCES}. Point --root at the challenge-2020/1.0.2 release."
        )


def dataset() -> Dataset:
    return Dataset(
        name="cinc2020",
        version="1.0.2",
        homepage="https://physionet.org/content/challenge-2020/1.0.2/",
        license="CC BY 4.0",
        license_class="permissive",
        citation="Perez Alday EA et al. Classification of 12-lead ECGs: the "
        "PhysioNet/Computing in Cardiology Challenge 2020 (v1.0.2). "
        "Physiol Meas 2020.",
        expected_size_gb=3.0,
        download=_download,
        parse=_parse,
        notes="Multi-source 12-lead blend; ptb-xl source excluded by default to "
        "avoid duplication with the native ptb_xl dataset.",
    )
