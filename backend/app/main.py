"""FastAPI application entry point."""
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import init_db
from app.services.quiz import game
from app.services.tiktok_live import bridge
from app.websocket.routes import router as ws_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await init_db()
    clock = asyncio.create_task(game.run_clock())
    try:
        yield
    finally:
        await bridge.disconnect()
        clock.cancel()
        try:
            await clock
        except asyncio.CancelledError:
            pass


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
app.include_router(ws_router)
