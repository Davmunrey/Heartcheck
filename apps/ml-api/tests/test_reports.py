from fastapi.testclient import TestClient


def _sample_payload() -> dict:
    return {
        "analysis": {
            "status": "green",
            "bpm": 72.0,
            "message": "Test interpretation line for PDF wrapping and content.",
            "confidence_score": 0.8,
            "rhythm_regularity": "regular",
            "class_label": "normal",
            "disclaimer": "Educational only.",
            "pipeline_version": "0.1.0",
            "model_version": "test",
            "extraction_quality": 0.9,
            "request_id": "rid-test-001",
            "education_topic_ids": ["topic_a"],
            "supported_findings": ["rhythm_estimate"],
            "measurement_basis": "ASSUMED_PAPER_SPEED",
        },
        "app_version": "0.1.0",
        "locale": "en",
    }


def test_report_pdf_with_api_key(client: TestClient) -> None:
    r = client.post(
        "/api/v1/reports/pdf",
        json=_sample_payload(),
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")


def test_report_pdf_with_bearer(client: TestClient) -> None:
    email = "pdf-bearer@example.com"
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass123"},
    ).status_code == 201
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass123"},
    ).json()["access_token"]
    r = client.post(
        "/api/v1/reports/pdf",
        json=_sample_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")
