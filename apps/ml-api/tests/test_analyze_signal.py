"""Tests for the 12-lead diagnostic (signal wedge) endpoint and preprocessing."""

import io

import numpy as np
from fastapi.testclient import TestClient


def _npy_bytes(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    np.save(buf, arr.astype(np.float32))
    return buf.getvalue()


def _fake_12lead(samples: int = 1000) -> np.ndarray:
    t = np.linspace(0, 10, samples)
    base = 0.1 * np.sin(2 * np.pi * 1.2 * t)
    return np.stack([base + 0.01 * i for i in range(12)])  # (12, samples)


def test_signal_requires_key(client: TestClient) -> None:
    r = client.post(
        "/api/v1/analyze/signal",
        files={"file": ("ecg.npy", _npy_bytes(_fake_12lead()), "application/octet-stream")},
        data={"sampling_rate_hz": "100"},
    )
    assert r.status_code == 401


def test_signal_bad_sample_rate(client: TestClient) -> None:
    r = client.post(
        "/api/v1/analyze/signal",
        headers={"X-API-Key": "test-key"},
        files={"file": ("ecg.npy", _npy_bytes(_fake_12lead()), "application/octet-stream")},
        data={"sampling_rate_hz": "0"},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "BAD_SAMPLE_RATE"


def test_signal_success_or_unavailable(client: TestClient) -> None:
    """With a checkpoint present -> 200 + calibrated findings; without -> 503."""
    r = client.post(
        "/api/v1/analyze/signal",
        headers={"X-API-Key": "test-key", "Accept-Language": "en"},
        files={"file": ("ecg.npy", _npy_bytes(_fake_12lead()), "application/octet-stream")},
        data={"sampling_rate_hz": "100"},
    )
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        body = r.json()
        assert isinstance(body["abnormal"], bool)
        assert len(body["findings"]) == 5
        codes = {f["code"] for f in body["findings"]}
        assert codes == {"NORM", "MI", "STTC", "CD", "HYP"}
        for f in body["findings"]:
            assert 0.0 <= f["probability"] <= 1.0
            assert isinstance(f["positive"], bool)
        assert body["n_leads"] == 12
        assert body["disclaimer"]
        assert body["request_id"]


def test_preprocess_outputs_channel_first_target_len() -> None:
    from app.services import diagnostic_inference as diag

    # (12, 500) at 100 Hz -> padded/cropped to (12, target_len)
    x = diag.preprocess(_fake_12lead(500), fs_in=100)
    assert x.shape == (12, diag._STATE.target_len)
    # per-lead z-score: near-zero mean, unit-ish std
    assert abs(float(x[0].mean())) < 1e-3


def test_preprocess_accepts_samples_first_orientation() -> None:
    from app.services import diagnostic_inference as diag

    # (N, 12) should be transposed to (12, target_len)
    x = diag.preprocess(_fake_12lead(800).T, fs_in=100)
    assert x.shape == (12, diag._STATE.target_len)


def test_preprocess_pads_fewer_than_12_leads() -> None:
    from app.services import diagnostic_inference as diag

    x = diag.preprocess(_fake_12lead(600)[:3], fs_in=100)  # 3 leads -> padded to 12
    assert x.shape == (12, diag._STATE.target_len)
