from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rejects_invalid_upload_type() -> None:
    client = TestClient(app)
    response = client.post(
        "/jobs",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
