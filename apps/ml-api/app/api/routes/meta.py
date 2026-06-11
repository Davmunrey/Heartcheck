"""Public service metadata for clients.

Mirrors the lightweight payload of ``/v1/meta`` exposed by the standalone
``heartscan_ml`` API so a single web client can target either backend through
the same ``/api/v1`` surface.

When a checkpoint manifest is loaded (see :mod:`app.ml.manifest`), additional
provenance is exposed: dataset name/version, architecture, headline metrics.
This is the contract the SPA / mobile clients use to surface "what model is
answering me".
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.services import diagnostic_inference as diag
from app.services import inference as inf

router = APIRouter(prefix="/api/v1", tags=["meta"])


@router.get("/meta")
def meta(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "pipeline_version": settings.pipeline_version,
        "model_version": inf.get_model_version(),
        "checkpoint_loaded": inf.get_model() is not None,
        "calibration": {
            "temperature": inf.get_temperature(),
            "conformal_threshold": inf.get_conformal_threshold(),
        },
    }
    manifest = inf.get_manifest()
    if manifest is not None:
        payload["model"] = manifest.public_meta()
    diag.is_loaded()  # ensure load attempted so _STATE reflects the served head
    payload["diagnostic_model"] = {
        "loaded": diag._STATE.model is not None,
        "version": diag.model_version(),
        "classes": list(diag._STATE.classes),  # actual served head (5 or 27)
        "n_classes": len(diag._STATE.classes),
        "macro_auroc": round(sum(diag._STATE.auroc.values()) / max(1, len(diag._STATE.auroc)), 4),
        "wedge": "signal-12-lead",
    }
    return payload
