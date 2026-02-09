"""Tests for processing websocket endpoint and connection manager."""

import asyncio
import time
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.routes.ws import router as ws_router
from src.api.websocket.manager import ProcessingConnectionManager
from src.db.models import ProcessingStatus, ProcessingStep, ProcessingUpdate
from src.services.processing import ProcessingQueue


def _update(
    *,
    item_id: str,
    step: ProcessingStep = ProcessingStep.CHUNKING,
    progress: float = 0.4,
    status: ProcessingStatus = ProcessingStatus.PROCESSING,
) -> ProcessingUpdate:
    return ProcessingUpdate(
        item_id=item_id,
        status=status,
        step=step,
        progress=progress,
        message=f"{step} update",
    )


def _build_test_app() -> tuple[FastAPI, ProcessingQueue, ProcessingConnectionManager]:
    app = FastAPI()
    app.include_router(ws_router, prefix="/api")

    queue = ProcessingQueue()
    manager = ProcessingConnectionManager(max_client_queue=10)
    queue.subscribe_processing_updates(manager.broadcast)

    app.state.processing_queue = queue
    app.state.processing_ws_manager = manager
    return app, queue, manager


class TestProcessingWebSocketEndpoint:
    """End-to-end websocket endpoint behavior."""

    def test_processing_ws_broadcasts_to_multiple_clients(self) -> None:
        """An emitted update should fan out to all connected subscribers."""
        app, queue, _ = _build_test_app()

        with TestClient(app) as client:
            with (
                client.websocket_connect("/api/ws/processing") as ws_one,
                client.websocket_connect("/api/ws/processing") as ws_two,
            ):
                queue.emit_processing_update(_update(item_id="item-1"))

                payload_one = ws_one.receive_json()
                payload_two = ws_two.receive_json()

        assert payload_one == payload_two
        assert payload_one["type"] == "processing_update"
        assert payload_one["item_id"] == "item-1"
        assert payload_one["step"] == "chunking"
        assert payload_one["status"] == "processing"

    def test_processing_ws_supports_item_subscription_filter(self) -> None:
        """Subscriber with item filter should only receive matching item updates."""
        app, queue, _ = _build_test_app()

        with TestClient(app) as client:
            with (
                client.websocket_connect("/api/ws/processing") as ws_all_items,
                client.websocket_connect("/api/ws/processing") as ws_filtered,
            ):
                ws_filtered.send_json({"subscribe": "item-2"})
                time.sleep(0.01)

                queue.emit_processing_update(_update(item_id="item-1"))
                all_first = ws_all_items.receive_json()

                queue.emit_processing_update(_update(item_id="item-2"))
                all_second = ws_all_items.receive_json()
                filtered = ws_filtered.receive_json()

        assert all_first["item_id"] == "item-1"
        assert all_second["item_id"] == "item-2"
        assert filtered["item_id"] == "item-2"


@dataclass
class _FailingSendWebSocket:
    """WebSocket double that fails every send attempt."""

    closed: bool = False

    async def accept(self) -> None:
        return None

    async def send_json(self, payload: dict) -> None:
        del payload
        raise RuntimeError("socket write failed")

    async def close(self) -> None:
        self.closed = True


@dataclass
class _BlockingSendWebSocket:
    """WebSocket double that blocks sends to simulate a slow consumer."""

    send_started: asyncio.Event
    release_send: asyncio.Event
    closed: bool = False

    async def accept(self) -> None:
        return None

    async def send_json(self, payload: dict) -> None:
        del payload
        self.send_started.set()
        await self.release_send.wait()

    async def close(self) -> None:
        self.closed = True
        self.release_send.set()


class TestProcessingConnectionManager:
    """Unit tests for connection manager cleanup and backpressure."""

    async def test_disconnects_broken_socket_during_send(self) -> None:
        """Broken send should remove stale connection during delivery attempt."""
        manager = ProcessingConnectionManager(max_client_queue=1)
        websocket = _FailingSendWebSocket()
        await manager.connect(websocket)  # type: ignore[arg-type]

        manager.broadcast(_update(item_id="item-1"))
        await asyncio.sleep(0.05)

        assert manager.active_connection_count == 0
        assert websocket.closed is True

    async def test_disconnects_slow_consumer_when_queue_is_full(self) -> None:
        """Slow consumers should be dropped when their bounded queue fills."""
        manager = ProcessingConnectionManager(max_client_queue=1)
        websocket = _BlockingSendWebSocket(
            send_started=asyncio.Event(),
            release_send=asyncio.Event(),
        )
        await manager.connect(websocket)  # type: ignore[arg-type]

        manager.broadcast(_update(item_id="item-1"))
        await websocket.send_started.wait()

        manager.broadcast(
            _update(item_id="item-1", step=ProcessingStep.EXTRACTING, progress=0.65)
        )
        manager.broadcast(
            _update(item_id="item-1", step=ProcessingStep.VALIDATING, progress=0.85)
        )
        await asyncio.sleep(0.05)

        assert manager.active_connection_count == 0
        assert websocket.closed is True
