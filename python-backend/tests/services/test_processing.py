"""Tests for ProcessingQueue service."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

import pytest
from src.config import settings
from src.services.processing import ProcessingQueue


@dataclass
class _ItemStub:
    id: str


class TestProcessingQueue:
    """Behavioral tests for ProcessingQueue."""

    async def test_enqueue_applies_backpressure_when_queue_is_full(self) -> None:
        """Second enqueue should wait until there is queue capacity."""
        queue = ProcessingQueue()
        queue.queue = asyncio.Queue(maxsize=1)

        assert await queue.enqueue("item-1") is True

        second_enqueue = asyncio.create_task(queue.enqueue("item-2"))
        await asyncio.sleep(0.01)
        assert not second_enqueue.done()

        first_item = await queue.queue.get()
        assert first_item == "item-1"
        queue.queue.task_done()

        assert await asyncio.wait_for(second_enqueue, timeout=0.2) is True

    async def test_enqueue_returns_false_for_duplicate_item(self) -> None:
        """Duplicate enqueue should be ignored and return False."""
        queue = ProcessingQueue()

        assert await queue.enqueue("item-1") is True
        assert await queue.enqueue("item-1") is False

    async def test_process_one_tracks_success_and_failures(self) -> None:
        """Queue counters should reflect successful and failed processing."""
        queue = ProcessingQueue()

        with patch(
            "src.services.processing.process_item",
            new=AsyncMock(return_value={}),
        ):
            await queue._process_one("ok-item")

        with patch(
            "src.services.processing.process_item",
            new=AsyncMock(return_value={"error": "failed"}),
        ):
            await queue._process_one("failed-item")

        with patch(
            "src.services.processing.process_item",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            await queue._process_one("exception-item")

        assert queue.completed_count == 1
        assert queue.total_processed == 3
        assert "failed-item" in queue.failed_items
        assert "exception-item" in queue.failed_items

    async def test_retry_failed_readds_item_when_enqueue_fails(self) -> None:
        """retry_failed(item_id=...) should restore failed state on enqueue failure."""
        queue = ProcessingQueue()
        queue.failed_items.add("item-1")

        with patch.object(
            queue,
            "enqueue",
            new=AsyncMock(side_effect=RuntimeError("queue unavailable")),
        ):
            with pytest.raises(RuntimeError):
                await queue.retry_failed("item-1")

        assert "item-1" in queue.failed_items

    async def test_retry_failed_returns_zero_when_item_already_in_queue(self) -> None:
        """Specific retry returns 0 when item was not newly enqueued."""
        queue = ProcessingQueue()
        queue.failed_items.add("item-1")

        with patch.object(queue, "enqueue", new=AsyncMock(return_value=False)):
            assert await queue.retry_failed("item-1") == 0

    async def test_start_and_stop_are_idempotent(self) -> None:
        """Repeated start/stop calls should not create duplicate workers or crash."""
        queue = ProcessingQueue()

        @asynccontextmanager
        async def fake_db_connection():
            yield object()

        get_by_status = AsyncMock(
            side_effect=[[_ItemStub("pending-1")], [], []],
        )

        with (
            patch("src.services.processing.db_connection", fake_db_connection),
            patch("src.services.processing.item_repo.get_by_status", get_by_status),
            patch.object(settings, "max_concurrent_processing", 1),
            patch(
                "src.services.processing.process_item", new=AsyncMock(return_value={})
            ),
        ):
            await queue.start()
            first_worker_count = len(queue._worker_tasks)

            await queue.start()
            assert len(queue._worker_tasks) == first_worker_count

            await queue.stop()
            await queue.stop()

        assert queue._worker_tasks == []
