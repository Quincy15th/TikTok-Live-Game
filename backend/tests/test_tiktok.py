"""Live bridge input, CommentEvent scoring, WebSocket broadcast, and localhost checks."""
import asyncio
import sys
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.routes.tiktok import require_local_client
from app.main import app
from app.services.quiz import QUESTIONS, game
from app.services.tiktok_live import USERNAME, TikTokBridge


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


def test_comment_event_scores_in_quiz_and_broadcasts_via_websocket() -> None:
    """Verify CommentEvent -> on_comment -> game.submit -> +10 score & WS broadcast."""

    class FakeConnectEvent:
        pass

    class FakeCommentEvent:
        pass

    class FakeDisconnectEvent:
        pass

    class FakeTikTokLiveClient:
        last_instance: "FakeTikTokLiveClient | None" = None

        def __init__(self, unique_id: str) -> None:
            self.unique_id = unique_id
            self.handlers: dict[Any, Any] = {}
            self._stop_event = asyncio.Event()
            self._web = SimpleNamespace(close=AsyncMock())
            FakeTikTokLiveClient.last_instance = self

        def on(self, event_cls: Any) -> Any:
            def decorator(fn: Any) -> Any:
                self.handlers[event_cls] = fn
                return fn

            return decorator

        async def start(self) -> asyncio.Task[None]:
            if FakeConnectEvent in self.handlers:
                await self.handlers[FakeConnectEvent](FakeConnectEvent())
            return asyncio.create_task(self._stop_event.wait())

        async def disconnect(self) -> None:
            self._stop_event.set()

    fake_pkg = ModuleType("TikTokLive")
    fake_pkg.TikTokLiveClient = FakeTikTokLiveClient  # type: ignore[attr-defined]
    fake_events = ModuleType("TikTokLive.events")
    fake_events.CommentEvent = FakeCommentEvent  # type: ignore[attr-defined]
    fake_events.ConnectEvent = FakeConnectEvent  # type: ignore[attr-defined]
    fake_events.DisconnectEvent = FakeDisconnectEvent  # type: ignore[attr-defined]

    async def scenario() -> None:
        local_bridge = TikTokBridge()
        broadcasts: list[dict[str, Any]] = []

        async def record_broadcast(payload: dict[str, Any]) -> None:
            broadcasts.append(payload)

        with (
            patch.dict(sys.modules, {"TikTokLive": fake_pkg, "TikTokLive.events": fake_events}),
            patch("app.services.tiktok_live.manager.broadcast", side_effect=record_broadcast),
            patch("app.services.quiz.manager.broadcast", side_effect=record_broadcast),
        ):
            status = await local_bridge.connect("@live_streamer")
            assert status["username"] == "live_streamer"
            await asyncio.sleep(0.05)
            assert local_bridge.status()["status"] == "connected"

            client = FakeTikTokLiveClient.last_instance
            assert client is not None
            on_comment = client.handlers[FakeCommentEvent]

            state_before = await game.get_state()
            correct_answer = {q["prompt"]: q["answer"] for q in QUESTIONS}[state_before["prompt"]]

            # 1. Wrong comment increments comments_received but does not score
            wrong_event = SimpleNamespace(
                user=SimpleNamespace(unique_id="live_viewer_1", display_id="live_viewer_1"),
                comment="wrong_word",
            )
            await on_comment(wrong_event)
            assert local_bridge.status()["comments_received"] == 1

            # 2. Correct comment (with v3 display_id/content fallback) awards +10 & broadcasts
            right_event = SimpleNamespace(
                user=SimpleNamespace(unique_id=None, display_id="live_viewer_1"),
                comment=None,
                content=f"  {correct_answer.upper()} ",
            )
            await on_comment(right_event)
            assert local_bridge.status()["comments_received"] == 2

            state_after = await game.get_state()
            assert any(
                p["name"] == "live_viewer_1" and p["score"] >= 10
                for p in state_after["leaderboard"]
            )
            assert any(
                m.get("type") == "game_state"
                and any(p["name"] == "live_viewer_1" for p in m["data"]["leaderboard"])
                for m in broadcasts
            )

            disc = await local_bridge.disconnect()
            assert disc["status"] == "disconnected"
            assert client._web.close.await_count >= 1

    asyncio.run(scenario())
