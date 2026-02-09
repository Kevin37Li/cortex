"""WebSocket endpoints for realtime processing updates."""

import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from ..dependencies import get_processing_ws_manager
from ..websocket.manager import ProcessingConnectionManager

logger = logging.getLogger(__name__)
SUBSCRIBE_KEY = "subscribe"

router = APIRouter(prefix="/ws", tags=["ws"])


@router.websocket("/processing")
async def processing_updates(
    websocket: WebSocket,
    manager: ProcessingConnectionManager = Depends(get_processing_ws_manager),
) -> None:
    """Stream processing updates to connected clients."""
    connection = None
    try:
        connection = await manager.connect(websocket)
        while True:
            payload = await websocket.receive_json()
            if not isinstance(payload, dict):
                continue

            subscribe = payload.get(SUBSCRIBE_KEY)
            if not isinstance(subscribe, str):
                continue

            item_id = subscribe.strip() or None
            manager.set_subscription(connection.connection_id, item_id)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Processing websocket receive loop failed")
    finally:
        if connection is not None:
            await manager.disconnect(connection.connection_id)
