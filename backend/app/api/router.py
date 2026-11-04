"""Aggregates REST routers under /api."""
from fastapi import APIRouter

from app.api.routes import game, health, tiktok

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(game.router)
api_router.include_router(tiktok.router)
