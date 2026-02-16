"""Connection manager for processing websocket subscribers."""

import asyncio
import logging
from dataclasses import dataclass
from uuid import uuid4

from fastapi import WebSocket

from src.db import ProcessingUpdate

logger = logging.getLogger(__name__)
DEFAULT_MAX_CLIENT_QUEUE = 100


@dataclass(slots=True)
class ClientConnection:
    """Active websocket connection with bounded outgoing queue."""

    connection_id: str
    websocket: WebSocket
    send_queue: asyncio.Queue[ProcessingUpdate]
    sender_task: asyncio.Task[None]
    subscription_item_id: str | None = None


class ProcessingConnectionManager:
    """Broadcast manager for `/api/ws/processing` subscribers.

    Backpressure policy:
    - each client gets a bounded send queue
    - if a queue is full, that client is disconnected as a slow consumer
    """

    def __init__(self, max_client_queue: int = DEFAULT_MAX_CLIENT_QUEUE) -> None:
        self.max_client_queue = max_client_queue
        self._connections: dict[str, ClientConnection] = {}
        self._cleanup_tasks: set[asyncio.Task[None]] = set()

    @property
    def active_connection_count(self) -> int:
        """Current number of active websocket clients."""
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> ClientConnection:
        """Accept and register a new websocket connection."""
        await websocket.accept()
        connection_id = str(uuid4())
        send_queue: asyncio.Queue[ProcessingUpdate] = asyncio.Queue(
            maxsize=self.max_client_queue,
        )
        sender_task = asyncio.create_task(
            self._sender_loop(connection_id, websocket, send_queue)
        )
        connection = ClientConnection(
            connection_id=connection_id,
            websocket=websocket,
            send_queue=send_queue,
            sender_task=sender_task,
        )
        self._connections[connection_id] = connection
        return connection

    async def disconnect(self, connection_id: str) -> None:
        """Remove and close a websocket connection if still active."""
        connection = self._connections.pop(connection_id, None)

        if connection is None:
            return

        current_task = asyncio.current_task()
        if connection.sender_task is not current_task:
            connection.sender_task.cancel()
            await connection.sender_task
        else:
            connection.sender_task.cancel()

        try:
            await connection.websocket.close()
        except Exception:
            pass

    def set_subscription(self, connection_id: str, item_id: str | None) -> None:
        """Set per-connection item filter. None means subscribe to all items."""
        connection = self._connections.get(connection_id)
        if connection is not None:
            connection.subscription_item_id = item_id

    def broadcast(self, update: ProcessingUpdate) -> None:
        """Queue an update for all matching subscribers without blocking producers."""
        try:
            validated_update = ProcessingUpdate.model_validate(update)
        except Exception:
            logger.exception("Dropping invalid processing update payload")
            return

        stale_connection_ids: list[str] = []
        for connection in list(self._connections.values()):
            if (
                connection.subscription_item_id is not None
                and connection.subscription_item_id != validated_update.item_id
            ):
                continue
            try:
                connection.send_queue.put_nowait(validated_update)
            except asyncio.QueueFull:
                stale_connection_ids.append(connection.connection_id)

        for connection_id in stale_connection_ids:
            task = asyncio.create_task(self.disconnect(connection_id))
            self._cleanup_tasks.add(task)
            task.add_done_callback(self._cleanup_tasks.discard)

    async def shutdown(self) -> None:
        """Disconnect all active websocket clients."""
        connection_ids = list(self._connections.keys())
        await asyncio.gather(
            *(self.disconnect(connection_id) for connection_id in connection_ids),
            return_exceptions=True,
        )

    async def _sender_loop(
        self,
        connection_id: str,
        websocket: WebSocket,
        send_queue: asyncio.Queue[ProcessingUpdate],
    ) -> None:
        while True:
            queue_item_received = False
            try:
                update = await send_queue.get()
                queue_item_received = True
                payload = update.model_dump(mode="json")
                await websocket.send_json(payload)
            except asyncio.CancelledError:
                break
            except Exception:
                task = asyncio.create_task(self.disconnect(connection_id))
                self._cleanup_tasks.add(task)
                task.add_done_callback(self._cleanup_tasks.discard)
                break
            finally:
                if queue_item_received:
                    send_queue.task_done()
