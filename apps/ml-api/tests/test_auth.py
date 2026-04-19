import numpy as np
from fastapi.testclient import TestClient


def _fake_ecg_image() -> bytes:
    import cv2

    img = np.ones((200, 800, 3), dtype=np.uint8) * 255
    for x in range(800):
        y = int(100 + 30 * np.sin(x / 40.0))
        cv2.circle(img, (x, y), 2, (30, 30, 30), -1)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


def test_register_login_analyze_with_bearer(client: TestClient) -> None:
    email = "beta-user@example.com"
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "securepass123"})
    assert r.status_code == 201

    r = client.post("/api/v1/auth/login", json={"email": email, "password": "securepass123"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.post(
        "/api/v1/analyze",
        headers={"Authorization": f"Bearer {token}", "Accept-Language": "en"},
        files={"file": ("x.png", _fake_ecg_image(), "image/png")},
    )
    assert r.status_code == 200
    data = r.json()
    assert "pipeline_version" in data


def test_me_requires_bearer(client: TestClient) -> None:
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
