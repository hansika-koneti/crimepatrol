"""
CrimePatrol — WebSocket Dashboard Endpoint
Subscribes to Redis pub/sub channel 'dashboard:updates'
and broadcasts prediction updates to all connected dashboard clients.
"""
import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.observability.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Track active WebSocket connections
_connections: set[WebSocket] = set()


@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    await websocket.accept()
    _connections.add(websocket)
    client = websocket.client.host if websocket.client else "unknown"
    logger.info("ws_client_connected", client=client, total=len(_connections))

    try:
        # Start listening to Redis pub/sub in background
        listener_task = asyncio.create_task(_listen_and_forward(websocket))

        # Keep connection alive — wait for client messages or disconnect
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if msg == "ping":
                    await websocket.send_text(json.dumps({"event": "pong"}))
            except asyncio.TimeoutError:
                # Send keepalive
                await websocket.send_text(json.dumps({"event": "keepalive"}))

    except WebSocketDisconnect:
        logger.info("ws_client_disconnected", client=client)
    except Exception as exc:
        logger.warning("ws_error", error=str(exc), client=client)
    finally:
        _connections.discard(websocket)
        listener_task.cancel()


async def _listen_and_forward(websocket: WebSocket) -> None:
    """Subscribe to Redis channel and forward messages to this WebSocket client."""
    try:
        from backend.infrastructure.cache.redis_client import get_pubsub
        pubsub = get_pubsub()
        await pubsub.subscribe("dashboard:updates")

        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message.get("data", "")
                try:
                    await websocket.send_text(data)
                except Exception:
                    break   # client disconnected

    except asyncio.CancelledError:
        pass
    except Exception as exc:
        logger.warning("ws_pubsub_error", error=str(exc))
