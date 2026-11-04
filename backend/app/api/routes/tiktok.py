"""Local-only administration of optional TikTok LIVE connection."""
import ipaddress

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.tiktok_live import bridge

router = APIRouter(prefix="/tiktok", tags=["tiktok"])


def require_local_client(request: Request) -> None:
    address = request.client.host if request.client else ""
    try:
        if not ipaddress.ip_address(address).is_loopback:
            raise ValueError("Not loopback")
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Local access only.") from exc


class ConnectRequest(BaseModel):
    username: str = Field(min_length=2, max_length=31)


@router.get("/status")
async def status() -> dict:
    return bridge.status()


@router.post("/connect", dependencies=[Depends(require_local_client)])
async def connect(payload: ConnectRequest) -> dict:
    try:
        return await bridge.connect(payload.username)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/disconnect", dependencies=[Depends(require_local_client)])
async def disconnect() -> dict:
    return await bridge.disconnect()
