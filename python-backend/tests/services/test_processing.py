"""Tests for ProcessingQueue service."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

import pytest
from src.config import settings
from src.db.models import ProcessingStatus, ProcessingStep, ProcessingUpdate
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

    async def test_process_one_passes_emit_callback_to_workflow(self) -> None:
        """Queue should pass its relay callback into workflow execution."""
        queue = ProcessingQueue()
        process_item_mock = AsyncMock(return_value={})

        with patch("src.services.processing.process_item", new=process_item_mock):
            await queue._process_one("item-1")

        assert process_item_mock.await_count == 1
        assert process_item_mock.await_args.args == ("item-1",)
        emit_update = process_item_mock.await_args.kwargs["emit_update"]
        assert emit_update.__self__ is queue
        assert emit_update.__func__ is queue.emit_processing_update.__func__

    async def test_emit_processing_update_relays_and_unsubscribes(self) -> None:
        """Relay should fan out to listeners and honor unsubscribe cleanup."""
        queue = ProcessingQueue()
        received: list[ProcessingUpdate] = []
        unsubscribe = queue.subscribe_processing_updates(received.append)
        update = ProcessingUpdate(
            item_id="item-1",
            status=ProcessingStatus.PROCESSING,
            step=ProcessingStep.CHUNKING,
            progress=0.4,
            message="Chunking content",
        )

        queue.emit_processing_update(update)
        unsubscribe()
        queue.emit_processing_update(update)

        assert received == [update]

    async def test_emit_processing_update_removes_failing_listener(self) -> None:
        """A failing listener should be removed so future relays continue cleanly."""
        queue = ProcessingQueue()
        calls = 0

        def bad_listener(_update: ProcessingUpdate) -> None:
            nonlocal calls
            calls += 1
            raise RuntimeError("listener failure")

        queue.subscribe_processing_updates(bad_listener)
        update = ProcessingUpdate(
            item_id="item-1",
            status=ProcessingStatus.PROCESSING,
            step=ProcessingStep.VALIDATING,
            progress=0.85,
            message="Validating extracted content",
        )

        queue.emit_processing_update(update)
        queue.emit_processing_update(update)

        assert calls == 1

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

    async def test_retry_failed_does_not_add_non_failed_item_to_failed_on_error(
        self,
    ) -> None:
        """If item was in _in_queue (not failed), enqueue error should not add it to failed_items."""
        queue = ProcessingQueue()
        queue._in_queue.add("item-1")

        with patch.object(
            queue,
            "enqueue",
            new=AsyncMock(side_effect=RuntimeError("queue unavailable")),
        ):
            with pytest.raises(RuntimeError):
                await queue.retry_failed("item-1")

        assert "item-1" not in queue.failed_items

    async def test_retry_failed_returns_zero_when_item_already_in_queue(self) -> None:
        """Specific retry returns retried_count=0 when item was not newly enqueued."""
        queue = ProcessingQueue()
        queue.failed_items.add("item-1")

        with patch.object(queue, "enqueue", new=AsyncMock(return_value=False)):
            result = await queue.retry_failed("item-1")
            assert result.retried_count == 0
            assert result.requested_item_id == "item-1"

    async def test_retry_failed_not_in_queue_for_unknown_item(self) -> None:
        """Retry of an unknown in-memory item returns outcome='not_in_queue'."""
        queue = ProcessingQueue()

        result = await queue.retry_failed("unknown-id")

        assert result.outcome == "not_in_queue"
        assert result.requested_item_id == "unknown-id"
        assert result.retried_count == 0

    async def test_retry_failed_already_queued_when_in_queue(self) -> None:
        """Retry of a pending item returns outcome='already_queued'."""
        queue = ProcessingQueue()
        queue._in_queue.add("queued-item")

        result = await queue.retry_failed("queued-item")

        assert result.outcome == "already_queued"
        assert result.requested_item_id == "queued-item"

    async def test_retry_failed_already_queued_when_processing(self) -> None:
        """Retry of a currently processing item returns outcome='already_queued'."""
        queue = ProcessingQueue()
        queue.processing.add("processing-item")

        result = await queue.retry_failed("processing-item")

        assert result.outcome == "already_queued"
        assert result.requested_item_id == "processing-item"

    async def test_retry_failed_all_retries_multiple_items(self) -> None:
        """Retry-all re-enqueues all failed items and returns count."""
        queue = ProcessingQueue()
        queue.failed_items = {"fail-1", "fail-2", "fail-3"}

        result = await queue.retry_failed(None)

        assert result.outcome == "retried"
        assert result.retried_count == 3
        assert len(queue.failed_items) == 0

    async def test_retry_failed_all_restores_on_enqueue_failure(self) -> None:
        """Retry-all restores items to failed_items when enqueue raises."""
        queue = ProcessingQueue()
        queue.failed_items = {"ok-item", "bad-item"}

        original_enqueue = queue.enqueue

        async def selective_enqueue(item_id: str) -> bool:
            if item_id == "bad-item":
                raise RuntimeError("queue full")
            return await original_enqueue(item_id)

        with patch.object(queue, "enqueue", side_effect=selective_enqueue):
            result = await queue.retry_failed(None)

        assert result.retried_count == 1
        assert "bad-item" in queue.failed_items
        assert "ok-item" not in queue.failed_items

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
