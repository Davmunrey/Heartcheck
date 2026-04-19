"""Orchestrate preprocessing, quality, R-R, model and guardrails.

Pipeline overview
-----------------

1. Decode photo to grayscale.
2. Rectify perspective (fallback: identity).
3. Pick the dominant lead strip (when multi-lead is detected).
4. Estimate fine-grid pitch with FFT (used to compute *measured* BPM and to
   parameterise grid suppression).
5. Suppress grid (FFT notch when calibration available; legacy adaptive
   threshold otherwise).
6. Extract 1D trace, compute R-R intervals.
7. Compute legacy signal-quality score and the multi-signal Quality Gate v2.
8. Run the classifier (with TTA and calibration), produce the conformal
   prediction set, and apply the post-model guardrails.
9. Compose the :class:`AnalysisResponse`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.schemas.analysis import AnalysisResponse

from app.services import grid_suppression, photo_geometry, preprocess, quality_gate, trace_extract
from app.services import inference as inf
from app.services.heuristic_classify import heuristic_label
from app.services.rr_intervals import analyze_rr

DISCLAIMER_EN = (
    "HeartScan provides educational information only. It does not replace professional "
    "medical advice, diagnosis, or treatment. Always consult a qualified healthcare provider."
)
DISCLAIMER_ES = (
    "HeartScan ofrece información educativa únicamente. No sustituye el consejo médico "
    "profesional, el diagnóstico ni el tratamiento. Consulte siempre a un profesional sanitario."
)

# Guardrail thresholds (kept top-level for visibility in code review).
ARRHYTHMIA_DOWNGRADE_BELOW = 0.60
NORMAL_GREEN_AT_LEAST = 0.55
NORMAL_GREEN_REQUIRES_QUALITY = 0.45
ABSTAIN_QUALITY_BELOW = 0.30
BPM_PHYSIOLOGICAL = (25.0, 220.0)


@dataclass
class _MessagePack:
    msg: str
    disclaimer: str


def _disclaimer(lang: str) -> str:
    return DISCLAIMER_ES if lang.startswith("es") else DISCLAIMER_EN


def _localize_reasons(lang: str, reasons: dict[str, str]) -> dict[str, str]:
    """Translate stable reason codes to user-facing copy."""
    es = lang.startswith("es")
    table = {
        quality_gate.REASON_BLUR: ("Foto borrosa: repítela con la cámara enfocada.", reasons.get(quality_gate.REASON_BLUR, "")),
        quality_gate.REASON_GLARE: ("Reflejos fuertes: evita brillos sobre el papel.", reasons.get(quality_gate.REASON_GLARE, "")),
        quality_gate.REASON_TILT: ("Foto inclinada: alinea la tira en horizontal.", reasons.get(quality_gate.REASON_TILT, "")),
        quality_gate.REASON_LOW_CONTRAST: ("Contraste bajo: mejora la iluminación.", reasons.get(quality_gate.REASON_LOW_CONTRAST, "")),
        quality_gate.REASON_NO_GRID: ("No se detecta cuadrícula: el BPM es orientativo.", reasons.get(quality_gate.REASON_NO_GRID, "")),
        quality_gate.REASON_NO_SIGNAL: ("No se pudo extraer el trazo de la imagen.", reasons.get(quality_gate.REASON_NO_SIGNAL, "")),
    }
    return {code: (table[code][0] if es else table[code][1]) for code in reasons if code in table}


def _message_for(
    lang: str,
    *,
    class_label: str,
    rhythm: str,
    extraction_quality: float,
    prediction_set: list[str],
    downgraded: bool,
) -> str:
    es = lang.startswith("es")
    if class_label == "noise":
        return (
            "La calidad de la señal extraída es insuficiente. Intente otra foto con mejor luz y encuadre."
            if es
            else "Extracted signal quality is insufficient. Try another photo with better light and framing."
        )
    if downgraded or len(prediction_set) > 1:
        if es:
            return (
                "El modelo no es concluyente: el resultado podría ser " + " o ".join(prediction_set) + ". "
                "Consulte con un profesional si tiene síntomas."
            )
        return (
            "The model is not conclusive: the result could be " + " or ".join(prediction_set) + ". "
            "Please consult a clinician if you have symptoms."
        )
    if class_label == "arrhythmia":
        return (
            "El patrón sugiere irregularidad del ritmo o un hallazgo que conviene comentar con un profesional."
            if es
            else "The pattern suggests rhythm irregularity or a finding worth discussing with a clinician."
        )
    if rhythm == "irregular" and class_label == "normal":
        return (
            "Hay variación entre latidos; conviene valoración profesional si hay síntomas."
            if es
            else "Beat-to-beat variation is present; seek professional assessment if you have symptoms."
        )
    return (
        "El patrón es compatible con un ritmo regular en este análisis limitado. No es un diagnóstico."
        if es
        else "The pattern is compatible with a regular rhythm in this limited analysis. Not a diagnosis."
    )


def _traffic_light(
    *,
    class_label: str,
    confidence: float,
    quality_score: float,
    reportable: bool,
    prediction_set_size: int,
) -> str:
    if not reportable or class_label == "noise":
        return "red"
    if prediction_set_size > 1:
        return "yellow"
    if class_label == "arrhythmia" and confidence >= 0.5:
        return "red"
    if (
        class_label == "normal"
        and confidence >= NORMAL_GREEN_AT_LEAST
        and quality_score >= NORMAL_GREEN_REQUIRES_QUALITY
    ):
        return "green"
    return "yellow"


def run_analysis(image_bytes: bytes, settings: Settings, request_id: str, accept_language: str) -> AnalysisResponse:
    lang = accept_language.split(",")[0].strip() or "en"

    # 1) decode + 2) perspective rectification.
    raw_gray = preprocess.decode_image_to_gray(image_bytes)
    rect = photo_geometry.correct_perspective(raw_gray)
    gray = rect.image

    # 3) pick the dominant lead strip if multiple are visible.
    strip, lead_count = photo_geometry.dominant_strip(gray)

    # 4) grid pitch + 5) grid suppression (FFT notch when grid is confident).
    grid_cal = photo_geometry.estimate_grid_pitch(strip)
    binary = (
        grid_suppression.suppress_grid_v2(strip, calibration=grid_cal)
        if grid_suppression.active_variant() == "v2"
        else grid_suppression.suppress_grid(strip)
    )

    # 6) extract 1D trace and analyse R-R.
    _, y_signal = trace_extract.extract_trace_1d(binary)
    w = int(strip.shape[1])
    rr = analyze_rr(
        y_signal,
        image_width_px=w,
        assumed_strip_duration_sec=settings.assumed_strip_duration_sec,
    )

    # 7) quality gate v1 + v2.
    signal_score = quality_gate.extraction_quality_score(y_signal, rr.peak_count)
    photo_q = photo_geometry.photo_quality_signals(strip, tilt_deg=rect.tilt_deg)
    gate = quality_gate.quality_gate_v2(signal_score, photo_q, grid_cal)
    final_quality = gate.score

    signal = trace_extract.resample_signal(y_signal, target_len=1024)

    # 8) classifier — deep when checkpoint is loaded, heuristic otherwise.
    use_nn = inf.get_model() is not None and Path(settings.model_path or "").is_file()
    tta = 5 if use_nn and os.environ.get("HEARTSCAN_TTA", "0") == "1" else 1
    if final_quality < ABSTAIN_QUALITY_BELOW:
        class_label = "noise"
        confidence = 0.95
        prediction_set = ["noise"]
        probs: dict[str, float] = {"noise": 0.95}
    elif use_nn:
        dist = inf.predict_distribution(signal, tta=tta)
        probs = dist["probs"]
        prediction_set = dist["prediction_set"]
        confidence = dist["calibrated_confidence"]
        class_label = max(probs, key=probs.get)
    else:
        class_label, confidence = heuristic_label(rr, final_quality)
        probs = {class_label: confidence}
        prediction_set = [class_label]

    # 8b) post-model guardrails.
    downgraded = False
    if class_label == "arrhythmia" and confidence < ARRHYTHMIA_DOWNGRADE_BELOW:
        downgraded = True
    if "arrhythmia" in prediction_set and "normal" in prediction_set:
        downgraded = True

    rhythm = rr.regularity if class_label != "noise" else "unknown"

    # BPM: prefer measured; fall back to assumed if grid not confident; null if quality low.
    bpm: float | None = rr.bpm
    measurement_basis = rr.measurement_basis
    measured_bpm, measured_basis = photo_geometry.bpm_from_calibration(
        rr.mean_rr_samples, w, grid_cal
    )
    if measured_bpm is not None:
        bpm = measured_bpm
        measurement_basis = measured_basis

    if not settings.use_assumed_time_axis_for_bpm and measurement_basis != "GRID_CALIBRATED":
        bpm = None
        measurement_basis = None
    if bpm is not None and not (BPM_PHYSIOLOGICAL[0] <= bpm <= BPM_PHYSIOLOGICAL[1]):
        bpm = None
        measurement_basis = None
    if final_quality < 0.40 and measurement_basis != "GRID_CALIBRATED":
        bpm = None
        measurement_basis = None

    # 9) compose response.
    non_rep: dict[str, str] | None = None
    localized = _localize_reasons(lang, gate.reasons)
    if not gate.reportable or class_label == "noise":
        non_rep = localized or {"quality": "Image not reportable"}
    elif localized:
        # informational reasons (no abstention needed)
        non_rep = {k: v for k, v in localized.items() if k in {quality_gate.REASON_NO_GRID, quality_gate.REASON_TILT}}
        if not non_rep:
            non_rep = None

    limits: list[str] = []
    if measurement_basis == "GRID_CALIBRATED":
        limits.append("GRID_CALIBRATED_BPM")
    elif measurement_basis is not None:
        limits.append("ASSUMED_UNIFORM_TIME_AXIS")
    limits.append("SINGLE_LEAD_PHOTO")
    if rect.rectified:
        limits.append("PERSPECTIVE_CORRECTED")
    if lead_count > 1:
        limits.append(f"MULTI_LEAD_DETECTED:{lead_count}")

    status = _traffic_light(
        class_label=class_label,
        confidence=confidence,
        quality_score=final_quality,
        reportable=gate.reportable,
        prediction_set_size=len(prediction_set),
    )

    education_ids: list[str] = []
    if class_label == "arrhythmia":
        education_ids.append("rhythm_arrhythmia_intro")
    elif class_label == "noise":
        education_ids.append("capture_quality")

    supported = [
        "rhythm_regularity_proxy",
        "three_class_screening_normal_arrhythmia_noise",
    ]
    if measurement_basis == "GRID_CALIBRATED":
        supported.append("bpm_grid_calibrated")

    message = _message_for(
        lang,
        class_label=class_label,
        rhythm=rhythm,
        extraction_quality=final_quality,
        prediction_set=prediction_set,
        downgraded=downgraded,
    )

    return AnalysisResponse(
        status=status,  # type: ignore[arg-type]
        bpm=bpm,
        message=message,
        confidence_score=round(min(1.0, max(0.0, confidence)), 4),
        rhythm_regularity=rhythm if rhythm in ("regular", "irregular") else "unknown",
        class_label=class_label if class_label in ("normal", "arrhythmia", "noise") else "noise",  # type: ignore[arg-type]
        disclaimer=_disclaimer(lang),
        pipeline_version=settings.pipeline_version,
        model_version=inf.get_model_version(),
        extraction_quality=round(final_quality, 4),
        request_id=request_id,
        non_reportable_reason=non_rep,
        analysis_limit=limits,
        supported_findings=supported,
        measurement_basis=measurement_basis,
        education_topic_ids=education_ids,
        prediction_set=prediction_set,
        calibrated_confidence=round(confidence, 4),
        quality_reasons=list(gate.reasons.keys()) or None,
        lead_count_detected=lead_count,
    )
