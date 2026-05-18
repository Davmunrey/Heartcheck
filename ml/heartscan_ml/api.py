"""API HTTP para analisis de fotos ECG (y metadatos de servicio)."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from heartscan_ml import PIPELINE_VERSION
from heartscan_ml.ckpt import load_torch
from heartscan_ml.config import TrainConfig
from heartscan_ml.inference import analyze_photo_bytes

from heartscan_ml.cnn1d import ECGResNet1D, default_model_version


def _resolve_checkpoint_path() -> str | None:
    env = os.environ.get("HEARTSCAN_CHECKPOINT", "").strip()
    candidates = []
    if env:
        candidates.append(env)
    candidates.append("checkpoints/cnn1d_best.pt")
    here = Path(__file__).resolve().parent.parent
    candidates.append(str(here / "checkpoints" / "cnn1d_best.pt"))
    for p in candidates:
        if p and Path(p).is_file():
            return p
    return None


_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    device_s = os.environ.get("HEARTSCAN_DEVICE", "")
    if device_s:
        device = torch.device(device_s)
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    cfg = TrainConfig(ptbxl_dir=os.environ.get("PTBXL_DIR", "."))
    # ECGResNet1D: 1-channel input, matches pretrain.py and finetune_image.py
    model = ECGResNet1D(num_classes=3, length=cfg.crop_len).to(device)

    ckpt_path = _resolve_checkpoint_path()
    model_version = default_model_version()
    if ckpt_path:
        ckpt = load_torch(ckpt_path, device)
        payload = ckpt.get("state_dict") or ckpt.get("model_state") or ckpt
        if isinstance(payload, dict):
            model.load_state_dict(payload, strict=False)
        model_version = str(ckpt.get("version", model_version)).replace("-untrained", "-trained")
    model.set_eval_mode() if hasattr(model, "set_eval_mode") else model.eval()

    _state["model"] = model
    _state["device"] = device
    _state["cfg"] = cfg
    _state["model_version"] = model_version
    _state["checkpoint_loaded"] = ckpt_path is not None

    yield

    _state.clear()


app = FastAPI(title="HeartScan ML", version=PIPELINE_VERSION, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("HEARTSCAN_CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "pipeline_version": PIPELINE_VERSION,
        "checkpoint_loaded": _state.get("checkpoint_loaded", False),
    }


def _meta_payload() -> dict[str, Any]:
    return {
        "pipeline_version": PIPELINE_VERSION,
        "model_version": _state.get("model_version", "unknown"),
        "checkpoint_loaded": _state.get("checkpoint_loaded", False),
    }


async def _analyze_payload(file: UploadFile) -> dict[str, Any]:
    if not _state.get("model"):
        raise HTTPException(503, "Model not initialized")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")

    try:
        return analyze_photo_bytes(
            data,
            _state["model"],
            _state["device"],
            crop_len=_state["cfg"].crop_len,
            assumed_fs=float(_state["cfg"].sample_rate),
            model_version_label=_state["model_version"],
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {e!s}") from e


@app.get("/v1/meta")
@app.get("/api/v1/meta")
def meta() -> dict[str, Any]:
    return _meta_payload()


@app.post("/v1/analyze")
@app.post("/api/v1/analyze")
async def analyze(file: UploadFile = File(...)) -> dict[str, Any]:
    return await _analyze_payload(file)


def run_server() -> None:
    import uvicorn

    host = os.environ.get("HEARTSCAN_HOST", "0.0.0.0")
    port = int(os.environ.get("HEARTSCAN_PORT", "8000"))
    uvicorn.run(
        "heartscan_ml.api:app",
        host=host,
        port=port,
        factory=False,
    )


if __name__ == "__main__":
    run_server()
