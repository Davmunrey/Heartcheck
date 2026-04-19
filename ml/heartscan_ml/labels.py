"""PTB-XL SCP statement keys → screening classes (normal / arrhythmia / other).

Noise class is trained only via synthetic augmentation (no PhysioNet label).
References: PTB-XL paper (PMC7248071), PhysioNet ptbxl_database.csv scp_codes.
"""

from __future__ import annotations

import ast
from typing import Any

# Rhythm-related statements (subset of SCP-ECG used in PTB-XL; extend as needed).
ARRHYTHMIA_SCP: frozenset[str] = frozenset(
    {
        "AFIB",
        "AFLT",
        "SVTA",
        "PVC",
        "PAC",
        "TRIGU",
        "BIGU",
        "VTACH",
        "VFIB",
        "ABQRS",
        "PACE",
        "SVARR",
    }
)

NORMAL_SCP: frozenset[str] = frozenset({"NORM"})

CLASS_NAMES = ("normal", "arrhythmia", "noise")


def parse_scp_codes(raw: Any) -> dict[str, float]:
    if raw is None or (isinstance(raw, float) and str(raw) == "nan"):
        return {}
    if isinstance(raw, dict):
        return {str(k): float(v) for k, v in raw.items()}
    if isinstance(raw, str):
        try:
            d = ast.literal_eval(raw)
            if isinstance(d, dict):
                return {str(k): float(v) for k, v in d.items()}
        except (SyntaxError, ValueError):
            return {}
    return {}


def ptbxl_to_screening_class(scp_codes: dict[str, float], norm_threshold: float = 0.0) -> int:
    """3-class screening aligned with product: 0 normal, 1 abnormal screen, 2 noise (synthetic only).

    PhysioNet rows never use 2; class 2 is trained only via heavy augmentation in the loader.
    Abnormal includes rhythm SCP and any non-NORM diagnostic (MI, STTC, CD, HYP, …).
    """
    keys = set(scp_codes.keys())
    if not keys:
        return 1
    if keys <= NORMAL_SCP and scp_codes.get("NORM", 0) >= norm_threshold:
        return 0
    return 1
