from fastapi.testclient import TestClient


def test_meta_public(client: TestClient) -> None:
    r = client.get("/api/v1/meta")
    assert r.status_code == 200
    body = r.json()
    assert "pipeline_version" in body
    assert "model_version" in body
    assert "checkpoint_loaded" in body
    assert isinstance(body["checkpoint_loaded"], bool)


def test_meta_does_not_require_auth(client: TestClient) -> None:
    r = client.get("/api/v1/meta")
    assert r.status_code == 200
