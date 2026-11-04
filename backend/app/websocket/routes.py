from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket.manager import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    await websocket.send_json({"type": "connected"})
    try:
        while True:
            _message = await websocket.receive_json()
            # TODO: route incoming messages to game services.
    except WebSocketDisconnect:
        manager.disconnect(websocket)
