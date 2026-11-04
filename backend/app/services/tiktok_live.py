"""Optional TikTok LIVE comment bridge.

The TikTokLive third-party library is deliberately imported only when a live
connection is requested, so demo mode works without extra dependencies.
"""
import asyncio
import logging
import re
from typing import Any

from app.services.quiz import game
from app.websocket.manager import manager

logger = logging.getLogger(__name__)
USERNAME = re.compile(r"^@?[A-Za-z0-9._]{2,30}$")


async def _close_client(client: Any) -> None:
    """Safely close a TikTokLiveClient inside a running asyncio event loop.

    Note: ``client.close()`` in TikTokLive 7.x calls ``_clean_tasks()``, which
    invokes ``loop.run_until_complete()`` and raises ``RuntimeError: This event
    loop is already running`` when called from an async server like FastAPI.
    """
    try:
        await asyncio.wait_for(client.disconnect(), timeout=5)
    except Exception as exc:
        logger.debug("TikTok LIVE disconnect: %s", exc)
    web = getattr(client, "_web", None)
    if web is not None and hasattr(web, "close"):
        try:
            await asyncio.wait_for(web.close(), timeout=5)
        except Exception as exc:
            logger.debug("TikTok LIVE web close: %s", exc)


class TikTokBridge:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self._client: Any = None
        self._stop_requested = False
        self._username: str | None = None
        self._state = "disconnected"
        self._error: str | None = None
        self._comments = 0

    def status(self) -> dict[str, Any]:
        return {
            "status": self._state,
            "username": self._username,
            "error": self._error,
            "comments_received": self._comments,
        }

    async def _notify(self) -> None:
        await manager.broadcast({"type": "tiktok_status", "data": self.status()})

    async def connect(self, username: str) -> dict[str, Any]:
        username = username.strip().lstrip("@")
        if not USERNAME.fullmatch(username):
            raise ValueError("Invalid TikTok username.")
        # Import before mutating state; demo continues working without TikTokLive.
        try:
            from TikTokLive import TikTokLiveClient
            from TikTokLive.events import CommentEvent, ConnectEvent, DisconnectEvent
        except ImportError as exc:
            raise RuntimeError(
                "TikTokLive is missing. Install backend/requirements-live.txt."
            ) from exc

        async with self._lock:
            if self._task is not None and not self._task.done():
                raise RuntimeError("Disconnect the current TikTok LIVE first.")
            self._stop_requested = False
            self._username = username
            self._error = None
            self._comments = 0
            self._state = "connecting"
            client = TikTokLiveClient(unique_id=f"@{username}")
            self._client = client

            @client.on(ConnectEvent)
            async def on_connect(_event: Any) -> None:
                self._state = "connected"
                self._error = None
                await self._notify()

            @client.on(CommentEvent)
            async def on_comment(event: Any) -> None:
                # Use unique_id (or v3 display_id / nickname fallback) as the player key.
                user = getattr(event, "user", None)
                identity = (
                    getattr(user, "unique_id", None)
                    or getattr(user, "display_id", None)
                    or getattr(user, "nickname", None)
                )
                text = getattr(event, "comment", None)
                if not isinstance(text, str):
                    text = getattr(event, "content", None)
                if not identity or not isinstance(text, str):
                    return
                self._comments += 1
                await game.submit(str(identity), text)
                if self._comments % 10 == 0:
                    await self._notify()

            @client.on(DisconnectEvent)
            async def on_disconnect(_event: Any) -> None:
                if not self._stop_requested:
                    self._state = "disconnected"
                    await self._notify()

            self._task = asyncio.create_task(self._run(client))
        await self._notify()
        return self.status()

    async def _run(self, client: Any) -> None:
        # A bounded reconnect loop prevents tight error loops when offline.
        try:
            for attempt in range(3):
                if self._stop_requested:
                    break
                if attempt:
                    self._state = "reconnecting"
                    await self._notify()
                    await asyncio.sleep(min(2 ** attempt, 8))
                try:
                    # Prefer client.start() + awaiting the returned task when available so
                    # cancelling self._task does not trigger TikTokLive 7.x's synchronous
                    # _clean_tasks() (which calls loop.run_until_complete on a running loop).
                    if hasattr(client, "start"):
                        ws_task = await client.start()
                        await ws_task
                    else:
                        await client.connect()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning("TikTok LIVE connection failed: %s", exc)
                    self._error = str(exc)[:240]
                if self._stop_requested:
                    break
            if not self._stop_requested:
                self._state = "error" if self._error else "disconnected"
        finally:
            if not self._stop_requested:
                await _close_client(client)
                await self._notify()

    async def disconnect(self) -> dict[str, Any]:
        async with self._lock:
            self._stop_requested = True
            task = self._task
            client = self._client
            self._task = None
            self._client = None
            self._state = "disconnected"
            self._error = None
            self._username = None
        if client is not None:
            await _close_client(client)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await self._notify()
        return self.status()


bridge = TikTokBridge()
