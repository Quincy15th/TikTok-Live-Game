from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_websocket_connects() -> None:
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        assert ws.receive_json() == {"type": "connected"}
