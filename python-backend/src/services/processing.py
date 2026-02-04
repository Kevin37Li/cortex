"""Background processing queue for content processing jobs.

Manages the lifecycle of content processing: enqueue items, process them
through the LangGraph workflow with a fixed worker pool, and track status.
"""

import asyncio
import logging

from src.config import settings
from src.db.database import db_connection
from src.db.models import QueueStatus
from src.db.repositories import item_repo
from src.workflows.processing import process_item

logger = logging.getLogger(__name__)

QUEUE_MAXSIZE = 1000


class ProcessingQueue:
    """In-process background processing queue.

    Uses asyncio.Queue with a fixed worker pool for bounded concurrency.
    Tracks in-memory state for reporting; the LangGraph workflow owns
    database status updates.

    Managed as a singleton via FastAPI's app.state.
    """

    def __init__(self) -> None:
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
        self._worker_tasks: list[asyncio.Task[None]] = []
        self._stopping = False

        # In-memory tracking
        self._in_queue: set[str] = set()  # Items pending in (or waiting to enter) queue
        self.processing: set[str] = set()
        self.failed_items: set[str] = set()
        self.completed_count: int = 0
        self.total_processed: int = 0

    async def enqueue(self, item_id: str) -> bool:
        """Enqueue item with backpressure/dedupe; returns True only if newly queued."""
        if self._stopping:
            raise RuntimeError("Processing queue is stopping")

        if item_id in self._in_queue or item_id in self.processing:
            logger.debug(f"Item {item_id} already enqueued or processing, skipping")
            return False
        # Reserve early so concurrent producers dedupe while put() is blocked.
        self._in_queue.add(item_id)

        try:
            # Proper backpressure: wait for capacity when queue is full.
            await self.queue.put(item_id)
        except asyncio.CancelledError:
            self._in_queue.discard(item_id)
            raise
        except Exception:
            self._in_queue.discard(item_id)
            logger.exception(f"Failed to enqueue item {item_id}")
            raise

        return True

    async def _process_one(self, item_id: str) -> None:
        """Process a single item through the LangGraph workflow."""
        processed = False

        self.processing.add(item_id)

        try:
            result = await process_item(item_id)
            processed = True

            if result.get("error"):
                self.failed_items.add(item_id)
            else:
                self.completed_count += 1
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(f"Error processing item {item_id}")
            processed = True
            self.failed_items.add(item_id)
        finally:
            self.processing.discard(item_id)
            if processed:
                self.total_processed += 1

    async def _worker(self) -> None:
        """Worker loop for fixed-size processing pool."""
        while True:
            if self._stopping and self.queue.empty():
                break

            try:
                item_id = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            self._in_queue.discard(item_id)

            try:
                await self._process_one(item_id)
            finally:
                self.queue.task_done()

    async def start(self) -> None:
        """Start worker pool and recover items from DB."""
        if self._worker_tasks:
            logger.debug("Processing queue already started")
            return

        self._stopping = False

        async with db_connection() as db:
            # Re-enqueue pending and interrupted items.
            pending = await item_repo.get_by_status(db, "pending")
            processing = await item_repo.get_by_status(db, "processing")
            for item in pending + processing:
                await self.enqueue(item.id)

            # Rebuild failed_items set (don't auto-enqueue).
            failed = await item_repo.get_by_status(db, "failed")
            self.failed_items = {item.id for item in failed}

        worker_count = max(1, settings.max_concurrent_processing)
        self._worker_tasks = [
            asyncio.create_task(self._worker()) for _ in range(worker_count)
        ]

        logger.info(f"Processing queue started with {worker_count} workers")

    async def stop(self) -> None:
        """Gracefully stop the queue."""
        if not self._worker_tasks:
            logger.debug("Processing queue already stopped")
            return

        self._stopping = True

        # Let workers finish queued/in-flight items.
        try:
            await asyncio.wait_for(self.queue.join(), timeout=5.0)
        except TimeoutError:
            logger.warning("Queue shutdown timeout; cancelling workers")

        for task in self._worker_tasks:
            task.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks = []

        logger.info("Processing queue stopped")

    def get_queue_status(self) -> QueueStatus:
        """Return current queue status."""
        return QueueStatus(
            pending_count=len(self._in_queue),
            processing_items=list(self.processing),
            failed_count=len(self.failed_items),
            completed_count=self.completed_count,
            total_processed=self.total_processed,
        )

    async def retry_failed(self, item_id: str | None = None) -> int:
        """Re-enqueue failed items. Returns count of items re-enqueued."""
        if item_id:
            if item_id not in self.failed_items:
                return 0
            self.failed_items.discard(item_id)

            try:
                enqueued = await self.enqueue(item_id)
            except Exception:
                self.failed_items.add(item_id)
                raise
            return 1 if enqueued else 0

        failed_ids = list(self.failed_items)
        self.failed_items.clear()

        retried = 0
        for failed_id in failed_ids:
            try:
                if await self.enqueue(failed_id):
                    retried += 1
            except Exception:
                logger.exception(f"Failed to re-enqueue failed item {failed_id}")
                self.failed_items.add(failed_id)

        return retried
