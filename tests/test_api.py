from fastapi.testclient import TestClient

from b3_pulse.api.app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_is_logged(caplog):
    with caplog.at_level("INFO", logger="b3_pulse.api.app"):
        client.get("/health")

    assert "GET /health -> 200" in caplog.text
