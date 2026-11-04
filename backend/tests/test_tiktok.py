"""Live bridge input and localhost-only admin checks; never access TikTok."""
from fastapi.testclient import TestClient

from app.api.routes.tiktok import require_local_client
from app.main import app
from app.services.tiktok_live import USERNAME


def test_username_validation() -> None:
    assert USERNAME.fullmatch("@sample_user")
    assert USERNAME.fullmatch("demo.123")
    assert not USERNAME.fullmatch("@bad user")
    assert not USERNAME.fullmatch("")


def test_status_endpoint_is_available_without_live_dependency() -> None:
    with TestClient(app) as client:
        response = client.get("/api/tiktok/status")
        assert response.status_code == 200
        assert response.json()["status"] == "disconnected"


def test_live_connection_rejects_invalid_username() -> None:
    # Starlette TestClient uses 'testclient', not a loopback IP address.
    app.dependency_overrides[require_local_client] = lambda: None
    try:
        with TestClient(app) as client:
            response = client.post("/api/tiktok/connect", json={"username": "bad user"})
            assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(require_local_client, None)
