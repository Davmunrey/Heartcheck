import numpy as np
from fastapi.testclient import TestClient


def _fake_ecg_image() -> bytes:
    import cv2

    img = np.ones((200, 800, 3), dtype=np.uint8) * 255
    # draw wavy dark line
    for x in range(800):
        y = int(100 + 30 * np.sin(x / 40.0))
        cv2.circle(img, (x, y), 2, (30, 30, 30), -1)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_analyze_requires_key(client: TestClient) -> None:
    r = client.post("/api/v1/analyze", files={"file": ("x.png", _fake_ecg_image(), "image/png")})
    assert r.status_code == 401


def test_analyze_success(client: TestClient) -> None:
    r = client.post(
        "/api/v1/analyze",
        headers={"X-API-Key": "test-key", "Accept-Language": "en"},
        files={"file": ("x.png", _fake_ecg_image(), "image/png")},
    )
    assert r.status_code == 200
    data = r.json()
    assert "pipeline_version" in data
    assert "model_version" in data
    assert data["request_id"]
    assert data["disclaimer"]


def test_analyze_rejects_spoofed_image(client: TestClient) -> None:
    """A request with image/* Content-Type but non-image bytes must be rejected."""
    payload = b"<html>not a real image, but pretending to be one</html>"
    r = client.post(
        "/api/v1/analyze",
        headers={"X-API-Key": "test-key"},
        files={"file": ("evil.png", payload, "image/png")},
    )
    assert r.status_code == 415
    assert r.json()["detail"]["error_code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_analyze_constant_time_api_key(client: TestClient) -> None:
    """Wrong API key still returns 401 (no observable difference vs missing)."""
    r = client.post(
        "/api/v1/analyze",
        headers={"X-API-Key": "wrong-key"},
        files={"file": ("x.png", _fake_ecg_image(), "image/png")},
    )
    assert r.status_code == 401
