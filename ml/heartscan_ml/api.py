"""API HTTP para análisis de fotos ECG (y metadatos de servicio)."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from heartscan_ml import MODEL_FAMILY, PIPELINE_VERSION
from heartscan_ml.ckpt import load_torch
from heartscan_ml.config import TrainConfig
from heartscan_ml.inference import analyze_photo_bytes
from heartscan_ml.model_cnn1d import CNN1D12Lead


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
    model = CNN1D12Lead(seq_len=cfg.crop_len, num_classes=3).to(device)

    ckpt_path = _resolve_checkpoint_path()
    model_version = f"{MODEL_FAMILY}-0.1.0-untrained"
    if ckpt_path:
        ckpt = load_torch(ckpt_path, device)
        model.load_state_dict(ckpt["model_state"])
        meta = ckpt.get("meta") or {}
        model_version = f"{meta.get('model_family', MODEL_FAMILY)}-trained"
    model.eval()

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
