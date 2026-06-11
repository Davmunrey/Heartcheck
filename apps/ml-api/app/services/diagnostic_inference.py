"""12-lead diagnostic inference (PTB-XL superclasses).

This serves the strong *signal* model (``ECGResNet1D``, 5 multi-label
superclasses) used by the **signal wedge** of the product — distinct from the
single-lead photo screening pipeline in :mod:`app.services.inference`.

Design notes
------------
* **Lazy load.** Torch and the checkpoint are imported/loaded on first use so
  the API and static pages bind immediately on cold start.
* **Safe load.** ``torch.load(weights_only=True)`` prevents pickle RCE.
* **Self-contained preprocessing.** Mirrors ``ml.training.data`` (resample to
  ``target_fs``, centre crop/pad to ``target_len``, per-lead z-score) so the
  input distribution matches training without importing the training package.
* **Calibrated thresholds** ship inside the checkpoint (per-class, tuned on a
  validation split). They are the decision boundary for "positive".
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)

# PTB-XL diagnostic superclasses, in checkpoint order.
SUPERCLASS_ORDER = ("NORM", "MI", "STTC", "CD", "HYP")

# Human-readable, copilot-friendly labels (non-diagnostic phrasing).
SUPERCLASS_LABELS: dict[str, str] = {
    "NORM": "Normal ECG",
    "MI": "Myocardial infarction (possible)",
    "STTC": "ST/T change",
    "CD": "Conduction disturbance",
    "HYP": "Hypertrophy",
}

# Per-class discrimination quality (macro-AUROC 0.852) measured on the held-out
# PTB-XL slice — the honest, threshold-independent quality signal surfaced to
# clinicians alongside each finding (see docs/MODEL_CARD.md). AUROC, not F1, is
# the headline metric: the model ranks well even where a fixed threshold trades
# precision for recall.
MODEL_AUROC: dict[str, float] = {
    "NORM": 0.879, "MI": 0.844, "STTC": 0.858, "CD": 0.873, "HYP": 0.806,
}
MACRO_AUROC = round(sum(MODEL_AUROC.values()) / len(MODEL_AUROC), 4)

# Conformal-style abstention: when a calibrated probability sits within this
# band of its decision threshold the model is near its boundary -> mark the
# finding uncertain and recommend human review instead of a hard call. Safety
# over coverage; overridable via env for tuning.
UNCERTAINTY_MARGIN = float(os.environ.get("HEARTSCAN_UNCERTAINTY_MARGIN", "0.10"))

# Candidate checkpoint locations, first hit wins. Overridable via env.
_DEFAULT_CANDIDATES = (
    "runs/auto/ptbxl_georgia_full/finetune_12e_from_8857/checkpoint.pt",
    "runs/auto/ptbxl_georgia_chapman/finetune_12e_from_georgia_full/checkpoint.pt",
)


@dataclass
class _DiagState:
    model: Any = None
    extra_models: list = field(default_factory=list)  # ensemble: averaged with `model`
    auroc: dict = field(default_factory=lambda: dict(MODEL_AUROC))
    classes: tuple[str, ...] = SUPERCLASS_ORDER
    thresholds: list[float] = field(default_factory=lambda: [0.5] * 5)
    target_len: int = 1024
    target_fs: int = 100
    version: str = "unloaded"
    loaded: bool = False
    checkpoint_path: str | None = None


_STATE = _DiagState()


def _resolve_checkpoint() -> Path | None:
    env = os.environ.get("HEARTSCAN_DIAGNOSTIC_MODEL_PATH")
    candidates = [env] if env else list(_DEFAULT_CANDIDATES)
    repo_root = Path(__file__).resolve().parents[4]  # app/services -> repo root (…/Heartcheck)
    for c in candidates:
        if not c:
            continue
        p = Path(c)
        for base in (p, repo_root / c):
            if base.is_file():
                return base
    return None


def load_diagnostic_model() -> bool:
    """Load the 12-lead model once. Returns True if a checkpoint was loaded."""
    if _STATE.loaded:
        return _STATE.model is not None
    ckpt = _resolve_checkpoint()
    if ckpt is None:
        _STATE.loaded = True
        logger.info("diagnostic_model_absent", reason="no_checkpoint")
        return False
    import torch
    from heartscan_ml.cnn1d import build_model

    state = torch.load(ckpt, map_location="cpu", weights_only=True)
    classes = tuple(state.get("classes", SUPERCLASS_ORDER))
    target_len = int(state.get("target_len", 1024))
    target_fs = int(state.get("target_fs", 100))
    arch = str(state.get("arch", "resnet"))  # "deep" for the 27-class model
    model = build_model(arch, num_classes=len(classes), length=target_len, in_channels=12)
    model.load_state_dict(state["state_dict"], strict=True)
    model.eval()

    _STATE.model = model
    _STATE.classes = classes
    _STATE.thresholds = list(state.get("thresholds") or [0.5] * len(classes))
    _STATE.target_len = target_len
    _STATE.target_fs = target_fs
    _STATE.version = str(state.get("version", state.get("task", "ecg-multilabel")))
    _STATE.checkpoint_path = str(ckpt)
    # Per-class AUROC from the checkpoint (complete model ships per_class_auroc);
    # fall back to the 5-superclass reference for the legacy head.
    _STATE.auroc = dict(state.get("per_class_auroc") or MODEL_AUROC)

    # Optional ensemble: extra checkpoints averaged with the primary at predict
    # time (comma-separated paths). Improves AUROC ~+0.6pt incl. HYP (see
    # docs/MODEL_CARD.md). Must share class order / target_len.
    extra_env = os.environ.get("HEARTSCAN_DIAGNOSTIC_ENSEMBLE_PATHS", "")
    for raw in (p.strip() for p in extra_env.split(",") if p.strip()):
        ep = Path(raw)
        ep = ep if ep.is_file() else (Path(__file__).resolve().parents[4] / raw)
        if not ep.is_file():
            logger.info("diagnostic_ensemble_skip", path=raw, reason="not_found")
            continue
        es = torch.load(ep, map_location="cpu", weights_only=True)
        em = build_model(str(es.get("arch", arch)), num_classes=len(classes), length=target_len, in_channels=12)
        em.load_state_dict(es["state_dict"], strict=True)
        em.eval()
        _STATE.extra_models.append(em)
    if _STATE.extra_models:
        _STATE.version = f"{_STATE.version}+ensemble{len(_STATE.extra_models)}"
    _STATE.loaded = True
    logger.info(
        "diagnostic_model_loaded",
        version=_STATE.version,
        classes=list(classes),
        checkpoint=str(ckpt),
    )
    return True


def is_loaded() -> bool:
    if not _STATE.loaded:
        load_diagnostic_model()
    return _STATE.model is not None


def model_version() -> str:
    return _STATE.version


# ---------------------------------------------------------------------------
# Preprocessing — keep in lockstep with ml.training.data.PTBXLDiagnosticDataset
# ---------------------------------------------------------------------------


def _to_channel_first(raw: np.ndarray) -> np.ndarray:
    if raw.ndim == 1:
        raw = raw[:, np.newaxis]
    # Orient to (samples, leads): more samples than leads.
    if raw.shape[0] < raw.shape[1]:
        raw = raw.T
    if raw.shape[1] >= 12:
        raw = raw[:, :12]
    else:
        raw = np.pad(raw, ((0, 0), (0, 12 - raw.shape[1])), mode="constant")
    return raw.T  # (12, samples)


def _resample(lead: np.ndarray, fs_in: int, fs_out: int) -> np.ndarray:
    if fs_in == fs_out or len(lead) < 2:
        return lead
    n_out = round(len(lead) * fs_out / fs_in)
    if n_out < 2:
        return lead
    x_in = np.linspace(0.0, 1.0, num=len(lead))
    x_out = np.linspace(0.0, 1.0, num=n_out)
    return np.interp(x_out, x_in, lead).astype(np.float32)


def _crop_or_pad(lead: np.ndarray, target_len: int) -> np.ndarray:
    if len(lead) >= target_len:
        start = (len(lead) - target_len) // 2
        return lead[start : start + target_len]
    pad = target_len - len(lead)
    return np.pad(lead, (pad // 2, pad - pad // 2), mode="reflect" if len(lead) > 1 else "constant")


def preprocess(signal: np.ndarray, fs_in: int) -> np.ndarray:
    """(leads, samples) or (samples, leads) raw -> (12, target_len) z-scored."""
    chf = _to_channel_first(np.asarray(signal, dtype=np.float32))
    out = []
    for lead in chf:
        x = _resample(lead, fs_in, _STATE.target_fs)
        x = _crop_or_pad(x, _STATE.target_len)
        x = x - x.mean()
        x = x / (x.std() + 1e-6)
        out.append(x.astype(np.float32))
    return np.stack(out)


@dataclass
class Finding:
    code: str
    label: str
    probability: float
    positive: bool
    threshold: float
    uncertain: bool
    confidence: str  # "high" | "low"
    auroc: float


@dataclass
class DiagnosticResult:
    findings: list[Finding]
    model_version: str
    n_leads: int
    sampling_rate_hz: int
    abnormal: bool
    requires_review: bool
    macro_auroc: float


def predict(signal: np.ndarray, fs_in: int) -> DiagnosticResult:
    """Run the 12-lead model. Raises RuntimeError if no model is loaded."""
    if not is_loaded():
        raise RuntimeError("diagnostic model not available")
    import torch

    x = preprocess(signal, fs_in)
    xt = torch.from_numpy(x).unsqueeze(0)
    with torch.no_grad():
        outs = [_STATE.model(xt).numpy()[0]]
        outs += [m(xt).numpy()[0] for m in _STATE.extra_models]
    logits = np.mean(outs, axis=0)  # ensemble = mean logits (1 model if no extras)
    probs = 1.0 / (1.0 + np.exp(-logits))

    findings: list[Finding] = []
    for code, p, thr in zip(_STATE.classes, probs, _STATE.thresholds):
        p = float(p)
        uncertain = abs(p - float(thr)) < UNCERTAINTY_MARGIN
        findings.append(
            Finding(
                code=code,
                label=SUPERCLASS_LABELS.get(code, code),
                probability=p,
                positive=bool(p >= thr),
                threshold=float(thr),
                uncertain=uncertain,
                confidence="low" if uncertain else "high",
                auroc=_STATE.auroc.get(code, 0.0),
            )
        )
    abnormal = any(f.positive for f in findings if f.code != "NORM")
    # Copilot is non-diagnostic: always route abnormal or any near-boundary
    # (uncertain) finding to a human. NORM uncertainty also warrants review.
    requires_review = abnormal or any(f.uncertain for f in findings)
    return DiagnosticResult(
        findings=findings,
        model_version=_STATE.version,
        n_leads=12,
        sampling_rate_hz=int(fs_in),
        abnormal=abnormal,
        requires_review=requires_review,
        macro_auroc=round(sum(_STATE.auroc.values()) / max(1, len(_STATE.auroc)), 4),
    )
