import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from heartscan_ml.api import app


def test_health():
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "pipeline_version" in body
