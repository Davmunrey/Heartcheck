"""Registry of every ECG dataset HeartScan can train against.

This module is the canonical truth about *which* datasets exist, *what*
their licenses are, and *how* to download them. The CLI and the training
scripts both consult this registry instead of hardcoding URLs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator, Literal

LicenseClass = Literal[
    "permissive",        # CC BY 4.0, CC0, MIT-style
    "share_alike",       # CC BY-SA, ODbL
    "non_commercial",    # CC BY-NC*, blocks shipping in a paid product
    "restricted",        # MTA, registration, CITI course, etc.
]

# Harmonised HeartScan classes — keep in sync with apps/ml-api/app/services/inference.py
HEARTSCAN_CLASSES = ("normal", "arrhythmia", "noise")
CLASS_TO_ID = {n: i for i, n in enumerate(HEARTSCAN_CLASSES)}


@dataclass
class Sample:
    """One harmonised ECG sample ready for training."""

    record_id: str
    label: str
    label_id: int
    source_dataset: str
    source_label: str  # raw label/code from the upstream dataset
    file_path: Path
    sampling_rate_hz: int
    n_leads: int
    duration_s: float
    patient_id: str | None = None
    metadata: dict = field(default_factory=dict)


SampleStream = Iterator[Sample]
DownloadFn = Callable[[Path], None]
ParseFn = Callable[[Path], SampleStream]


@dataclass
class Dataset:
    name: str
    version: str
    homepage: str
    license: str
    license_class: LicenseClass
    citation: str
    expected_size_gb: float
    download: DownloadFn
    parse: ParseFn
    notes: str = ""

    def commercial_safe(self) -> bool:
        return self.license_class in ("permissive",)


# ---------------------------------------------------------------------------
# Lazy registration: import the per-dataset modules to avoid cycles when the
# CLI just lists datasets without calling any of them.
# ---------------------------------------------------------------------------


def _build_registry() -> dict[str, Dataset]:
    from ml.datasets import (  # local imports keep side effects scoped
        but_qdb,
        chapman_shaoxing,
        cinc2017,
        code_15pct,
        ecg_image_database,
        georgia12,
        icentia11k,
        ludb,
        mimic_iv_ecg,
        mit_bih,
        ptb_xl,
        ptb_xl_image_17k,
        sph,
    )

    items: list[Dataset] = [
        ptb_xl.dataset(),
        chapman_shaoxing.dataset(),
        cinc2017.dataset(),
        but_qdb.dataset(),
        ecg_image_database.dataset(),
        ptb_xl_image_17k.dataset(),
        georgia12.dataset(),
        sph.dataset(),
        code_15pct.dataset(),
        mit_bih.dataset(),
        ludb.dataset(),
        icentia11k.dataset(),
        mimic_iv_ecg.dataset(),
    ]
    return {d.name: d for d in items}


REGISTRY: dict[str, Dataset] = _build_registry()


def get(name: str) -> Dataset:
    if name not in REGISTRY:
        raise KeyError(f"Unknown dataset {name!r}. Available: {sorted(REGISTRY)}")
    return REGISTRY[name]
