import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket.manager import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "connected"})
        while True:
            raw = await websocket.receive_text()
            try:
                _message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "reason": "invalid_json"})
                continue
            # TODO: route incoming messages to game services.
    except WebSocketDisconnect:
        pass
    finally:
        # Always release the connection, including on unexpected errors.
        manager.disconnect(websocket)
