from fastapi.testclient import TestClient


def test_landing_page(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "HeartScan" in r.text


def test_web_app_page(client: TestClient) -> None:
    r = client.get("/app")
    assert r.status_code == 200
    assert "Analizar" in r.text or "demo" in r.text.lower()
