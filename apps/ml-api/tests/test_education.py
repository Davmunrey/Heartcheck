from fastapi.testclient import TestClient


def test_education_topics(client: TestClient) -> None:
    r = client.get("/api/v1/education/topics?locale=en")
    assert r.status_code == 200
    data = r.json()
    assert "topics" in data
    assert len(data["topics"]) >= 1
