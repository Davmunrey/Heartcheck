"""Cross-dataset label harmonisation to the three HeartScan classes.

Each upstream dataset uses its own coding system (SCP-ECG, SNOMED-CT,
ad-hoc challenge labels). These helpers normalise everything to
``{normal, arrhythmia, noise}`` with documented, auditable rules.

Multi-label rule: a record that contains *any* code mapped to
``arrhythmia`` is labelled ``arrhythmia`` (the app errs on the side of
caution; full doc lives in ``docs/LABEL_HARMONIZATION.md``).
"""

from __future__ import annotations

from typing import Iterable

NORMAL = "normal"
ARRHYTHMIA = "arrhythmia"
NOISE = "noise"


# ---- PTB-XL (SCP-ECG) ------------------------------------------------------

PTBXL_NORMAL_SCP = {"NORM", "SR"}

PTBXL_ARRHYTHMIA_SCP = {
    # supraventricular
    "AFIB", "AFLT", "PSVT", "PAC", "STACH", "SBRAD", "SARRH", "SVTAC",
    # ventricular
    "PVC", "VTAC", "VFL", "BIGU", "TRIGU",
    # conduction
    "1AVB", "2AVB", "3AVB", "LBBB", "RBBB", "CLBBB", "CRBBB", "ILBBB", "IRBBB",
    "WPW", "LPFB", "LAFB",
    # ischemia / infarct (not strictly arrhythmia but flagged for caution)
    "AMI", "IMI", "LMI", "PMI", "ASMI", "ALMI", "ILMI", "IPMI", "IPLMI",
    "ISC_", "ISCAL", "ISCAS", "ISCIN", "ISCIL", "ISCAN", "ISCLA",
}


def map_ptbxl_codes(scp_codes: Iterable[str]) -> str:
    """Map a list of SCP codes to a HeartScan class with the multi-label rule."""
    codes = set(scp_codes)
    if codes & PTBXL_ARRHYTHMIA_SCP:
        return ARRHYTHMIA
    if codes & PTBXL_NORMAL_SCP:
        return NORMAL
    return NOISE


# ---- Chapman / Shaoxing (SNOMED-CT subset) --------------------------------

CHAPMAN_SR_SNOMED = {"426783006"}  # sinus rhythm
CHAPMAN_ARRHYTHMIA_SNOMED = {
    # rhythm
    "164889003",  # atrial fibrillation
    "164890007",  # atrial flutter
    "426761007",  # supraventricular tachycardia
    "164909002",  # left bundle branch block
    "59118001",   # right bundle branch block
    "164931005",  # st elevation
    "164934002",  # t wave abnormal
    "39732003",   # left axis deviation
    "164873001",  # left ventricular hypertrophy
    "270492004",  # 1st degree AV block
    "284470004",  # premature atrial contraction
    "427172004",  # premature ventricular contractions
    "164917005",  # q wave abnormal
    "55827005",   # left ventricular hypertrophy
    "428750005",  # nonspecific st-t abnormality
    "63593006",   # supraventricular premature beats
    "17338001",   # ventricular premature beats
    "164912004",  # p wave abnormal
}


def map_chapman_codes(snomed_codes: Iterable[str]) -> str:
    codes = {str(c) for c in snomed_codes}
    if codes & CHAPMAN_ARRHYTHMIA_SNOMED:
        return ARRHYTHMIA
    if codes & CHAPMAN_SR_SNOMED:
        return NORMAL
    return NOISE


# ---- CinC 2017 (single-letter labels) -------------------------------------

CINC2017_MAP = {
    "N": NORMAL,
    "A": ARRHYTHMIA,
    "O": ARRHYTHMIA,  # "Other rhythm" — treat as arrhythmia for caution
    "~": NOISE,
}


def map_cinc2017(label: str) -> str:
    return CINC2017_MAP.get(str(label).strip(), NOISE)


# ---- CODE-15% (six explicit binary codes) ---------------------------------

CODE15_FIELDS = ("1dAVb", "RBBB", "LBBB", "SB", "ST", "AF")


def map_code15(row: dict) -> str:
    """``row`` is a dict from the CSV; values are 0/1."""
    arrhythmia = any(int(row.get(k, 0)) == 1 for k in CODE15_FIELDS)
    return ARRHYTHMIA if arrhythmia else NORMAL


# ---- SPH (AHA / ACC / HRS) ------------------------------------------------

SPH_NORMAL = {"AECG: Normal ECG"}
SPH_ARRHYTHMIA_PREFIXES = (
    "AECG: Atrial fibrillation",
    "AECG: Atrial flutter",
    "AECG: Atrial premature complex",
    "AECG: Ventricular premature complex",
    "AECG: Sinus tachycardia",
    "AECG: Sinus bradycardia",
    "AECG: First degree AV block",
    "AECG: Second degree AV block",
    "AECG: Third degree AV block",
    "AECG: Right bundle branch block",
    "AECG: Left bundle branch block",
    "AECG: Left anterior fascicular block",
    "AECG: Left posterior fascicular block",
    "AECG: Wolff-Parkinson-White",
)


def map_sph(statements: Iterable[str]) -> str:
    s = list(statements)
    if any(any(x.startswith(p) for p in SPH_ARRHYTHMIA_PREFIXES) for x in s):
        return ARRHYTHMIA
    if any(x in SPH_NORMAL for x in s):
        return NORMAL
    return NOISE
