"""12-lead diagnostic analysis — the *signal* wedge.

POST ``/api/v1/analyze/signal`` accepts a raw 12-lead ECG signal upload and
returns calibrated multi-label superclass findings from the strong
``ECGResNet1D`` model. This is the clinical-copilot, human-in-the-loop path:
the response surfaces probabilities and a conformal-style positive flag, never
an autonomous diagnosis.

Accepted upload formats (``file``):
* ``.npy`` — numpy array shaped ``(12, N)`` or ``(N, 12)``.
* ``.csv`` — 12 columns (one per lead) or 12 rows.

Form field ``sampling_rate_hz`` (default 500) tells us the input sample rate;
the model resamples internally to its training rate.
"""

from __future__ import annotations

import io
from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile

from app.api.deps import AnalyzeAuth, require_analyze_auth
from app.core.config import Settings, get_settings
from app.core.limiter import limiter
from app.schemas.diagnostic import DiagnosticFinding, DiagnosticResponse
from app.services import diagnostic_inference as diag

router = APIRouter(prefix="/api/v1", tags=["analyze"])

_NPY_MAGIC = b"\x93NUMPY"

DISCLAIMER = (
    "Axis is a clinical decision-support copilot. Findings are probabilistic "
    "aids for a qualified clinician and must be confirmed by human review. It does "
    "not provide an autonomous diagnosis and does not replace a full clinical ECG."
)

ANALYSIS_LIMITS = [
    "12-lead diagnostic superclasses only (NORM/MI/STTC/CD/HYP).",
    "Not a substitute for a cardiologist's over-read.",
    "Rhythm/interval measurements are not part of this endpoint.",
]


def _error(request: Request, status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={
            "error_code": code,
            "message": message,
            "request_id": getattr(request.state, "request_id", ""),
        },
    )


def _parse_signal(raw: bytes, request: Request) -> np.ndarray:
    """Decode an uploaded .npy or .csv payload to a float32 2-D array."""
    if raw[:6] == _NPY_MAGIC:
        try:
            arr = np.load(io.BytesIO(raw), allow_pickle=False)
        except Exception as exc:
            raise _error(request, 422, "INVALID_NPY", "Could not parse .npy payload") from exc
    else:
        try:
            text = raw.decode("utf-8", errors="strict")
            arr = np.genfromtxt(io.StringIO(text), delimiter=",", dtype=np.float32)
        except Exception as exc:
            raise _error(
                request, 415, "UNSUPPORTED_FORMAT", "Expected a .npy or comma-separated .csv 12-lead signal"
            ) from exc
    arr = np.asarray(arr, dtype=np.float32)
    if arr.ndim != 2:
        raise _error(request, 422, "BAD_SHAPE", "Signal must be 2-D (leads x samples)")
    if not np.isfinite(arr).all():
        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    if 12 not in arr.shape and min(arr.shape) > 12:
        raise _error(request, 422, "BAD_LEADS", "Expected a 12-lead signal (one axis of length 12)")
    return arr


@router.post("/analyze/signal", response_model=DiagnosticResponse)
@limiter.limit("120/minute")
async def analyze_signal(
    request: Request,
    auth: Annotated[AnalyzeAuth, Depends(require_analyze_auth)],
    settings: Annotated[Settings, Depends(get_settings)],
    file: UploadFile = File(...),
    sampling_rate_hz: Annotated[int, Form()] = 500,
    accept_language: Annotated[str | None, Header()] = None,
) -> DiagnosticResponse:
    raw = await file.read()
    if len(raw) > settings.max_upload_bytes:
        raise _error(request, 413, "PAYLOAD_TOO_LARGE", "Signal exceeds configured limit")
    if len(raw) < 16:
        raise _error(request, 422, "EMPTY_PAYLOAD", "Uploaded signal is empty")
    if sampling_rate_hz < 1 or sampling_rate_hz > 5000:
        raise _error(request, 422, "BAD_SAMPLE_RATE", "sampling_rate_hz must be between 1 and 5000")

    signal = _parse_signal(raw, request)

    if not diag.is_loaded():
        raise _error(
            request,
            503,
            "MODEL_UNAVAILABLE",
            "Diagnostic model not configured (set HEARTSCAN_DIAGNOSTIC_MODEL_PATH).",
        )

    try:
        result = diag.predict(signal, fs_in=sampling_rate_hz)
    except RuntimeError as exc:
        raise _error(request, 503, "MODEL_UNAVAILABLE", str(exc)) from exc

    return DiagnosticResponse(
        abnormal=result.abnormal,
        findings=[
            DiagnosticFinding(
                code=f.code,
                label=f.label,
                probability=round(f.probability, 4),
                positive=f.positive,
                threshold=f.threshold,
            )
            for f in result.findings
        ],
        n_leads=result.n_leads,
        sampling_rate_hz=result.sampling_rate_hz,
        model_version=result.model_version,
        pipeline_version=settings.pipeline_version,
        request_id=getattr(request.state, "request_id", ""),
        disclaimer=DISCLAIMER,
        analysis_limit=ANALYSIS_LIMITS,
    )
