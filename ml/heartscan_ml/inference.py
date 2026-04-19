from __future__ import annotations

import argparse
import json
import uuid
from typing import Any

import numpy as np
import torch
import wfdb

from heartscan_ml import MODEL_FAMILY, PIPELINE_VERSION
from heartscan_ml.ckpt import load_torch
from heartscan_ml.config import GuardConfig, TrainConfig, default_guard_config
from heartscan_ml.guards import apply_guards
from heartscan_ml.labels import CLASS_NAMES
from heartscan_ml.messages import DISCLAIMER_ES, screening_message
from heartscan_ml.model_cnn1d import CNN1D12Lead
from heartscan_ml.preprocess import crop_center, resample_linear, zscore_per_lead
from heartscan_ml.rhythm import estimate_bpm_multilead, estimate_rr_regularity


def load_signal_from_wfdb(path_without_ext: str, target_fs: int, crop_len: int) -> np.ndarray:
    record = wfdb.rdrecord(path_without_ext)
    sig = record.p_signal.T.astype(np.float32)
    fs = int(record.fs)
    if fs != target_fs:
        sig = resample_linear(sig, fs, target_fs)
    sig = sig[:12]
    sig = crop_center(sig, crop_len)
    return zscore_per_lead(sig)


def run_inference(
    signal_12: np.ndarray,
    fs: float,
    model: CNN1D12Lead,
    device: torch.device,
    guard_cfg: GuardConfig | None = None,
    extraction_quality: int = 3,
    model_version_label: str | None = None,
) -> dict[str, Any]:
    """Inferencia base; `model_version_label` sobreescribe el sufijo de versión si se pasa."""
    guard_cfg = guard_cfg or default_guard_config()
    x = torch.from_numpy(signal_12).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = model(x)
        probs = torch.softmax(logits, dim=1).squeeze(0).cpu().numpy()
    pred_idx = int(probs.argmax())
    confidence = float(probs[pred_idx])
    class_label = CLASS_NAMES[pred_idx]

    raw_bpm, n_beats = estimate_bpm_multilead(signal_12, fs)
    if n_beats < 3:
        raw_bpm = None

    lead_ii = signal_12[1] if signal_12.shape[0] > 1 else signal_12[0]
    rhythm_regularity = estimate_rr_regularity(lead_ii, fs)
    if raw_bpm is None:
        rhythm_regularity = "unknown"

    gr = apply_guards(
        raw_bpm=raw_bpm,
        model_confidence=confidence,
        extraction_quality=extraction_quality,
        predicted_class=class_label,
        cfg=guard_cfg,
    )

    status = "green"
    if class_label == "arrhythmia" or pred_idx == 1:
        status = "red"
    elif class_label == "noise" or pred_idx == 2:
        status = "yellow"

    if not gr.reportable:
        status = "unknown"

    mv = model_version_label or f"{MODEL_FAMILY}-trained"
    return {
        "status": status,
        "bpm": gr.bpm,
        "confidence_score": gr.confidence_score,
        "class_label": class_label,
        "rhythm_regularity": rhythm_regularity,
        "pipeline_version": PIPELINE_VERSION,
        "model_version": mv,
        "extraction_quality": extraction_quality,
        "non_reportable_reason": gr.non_reportable_reason,
        "supported_findings": [
            "rhythm_regularity_proxy",
            "three_class_screening_normal_arrhythmia_noise",
        ],
        "raw_probs": {CLASS_NAMES[i]: float(probs[i]) for i in range(3)},
    }


def education_topic_ids(class_label: str, status: str) -> list[str]:
    if status == "red" or class_label == "arrhythmia":
        return ["rhythm_arrhythmia_intro"]
    return []


def build_full_response(
    core: dict[str, Any],
    *,
    request_id: str | None = None,
    from_photo: bool = False,
    measurement_basis: str = "ASSUMED_UNIFORM_TIME_AXIS",
) -> dict[str, Any]:
    """Envuelve la salida del modelo con campos de API (mensaje, disclaimer, límites)."""
    rid = request_id or str(uuid.uuid4())
    status = core["status"]
    class_label = core["class_label"]
    msg = screening_message(class_label, status)

    limits: list[str] = [measurement_basis] if measurement_basis else []
    if from_photo:
        limits.append("SINGLE_LEAD_PHOTO")

    out: dict[str, Any] = {
        "status": core["status"],
        "bpm": core["bpm"],
        "message": msg,
        "confidence_score": core["confidence_score"],
        "rhythm_regularity": core["rhythm_regularity"],
        "class_label": core["class_label"],
        "disclaimer": DISCLAIMER_ES,
        "pipeline_version": core["pipeline_version"],
        "model_version": core["model_version"],
        "extraction_quality": core["extraction_quality"],
        "request_id": rid,
        "non_reportable_reason": core["non_reportable_reason"],
        "analysis_limit": limits,
        "supported_findings": core["supported_findings"],
        "measurement_basis": measurement_basis,
        "education_topic_ids": education_topic_ids(class_label, status),
    }
    return out


def analyze_photo_bytes(
    data: bytes,
    model: CNN1D12Lead,
    device: torch.device,
    crop_len: int = 1000,
    assumed_fs: float = 100.0,
    guard_cfg: GuardConfig | None = None,
    model_version_label: str | None = None,
) -> dict[str, Any]:
    from heartscan_ml.image_extract import (
        bytes_to_gray,
        extract_lead_1d_from_gray,
        extraction_quality_score,
        single_lead_to_12,
    )

    gray = bytes_to_gray(data)
    lead, coverage = extract_lead_1d_from_gray(gray, target_len=crop_len)
    q = extraction_quality_score(coverage)
    sig12 = single_lead_to_12(lead)
    sig12 = zscore_per_lead(sig12)
    core = run_inference(
        sig12,
        assumed_fs,
        model,
        device,
        guard_cfg=guard_cfg,
        extraction_quality=q,
        model_version_label=model_version_label,
    )
    return build_full_response(core, from_photo=True)


def analyze_wfdb_path(
    path_without_ext: str,
    model: CNN1D12Lead,
    device: torch.device,
    cfg: TrainConfig,
    guard_cfg: GuardConfig | None = None,
    model_version_label: str | None = None,
) -> dict[str, Any]:
    sig = load_signal_from_wfdb(path_without_ext, cfg.sample_rate, cfg.crop_len)
    core = run_inference(
        sig,
        float(cfg.sample_rate),
        model,
        device,
        guard_cfg=guard_cfg,
        extraction_quality=3,
        model_version_label=model_version_label,
    )
    return build_full_response(core, from_photo=False)


def main() -> None:
    p = argparse.ArgumentParser(description="Run inference on one WFDB record (PTB-XL style path).")
    p.add_argument("--record", required=True, help="Path to record without extension")
    p.add_argument("--checkpoint", default="checkpoints/cnn1d_best.pt")
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--fs", type=int, default=100)
    args = p.parse_args()

    cfg = TrainConfig(ptbxl_dir=".")
    device = torch.device(args.device)
    ckpt = load_torch(args.checkpoint, device)
    mv = None
    if isinstance(ckpt.get("meta"), dict):
        mv = f"{ckpt['meta'].get('model_family', MODEL_FAMILY)}-trained"
    model = CNN1D12Lead(seq_len=cfg.crop_len, num_classes=3).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    path = args.record
    if path.endswith(".hea"):
        path = path[:-4]
    out = analyze_wfdb_path(path, model, device, cfg, model_version_label=mv)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
