# Task: Implement Processing Queue Service

## Summary

Create an in-process background processing queue that manages the lifecycle of content processing jobs. When items are created, they're enqueued for processing. The queue spawns concurrent worker tasks (configurable), tracks in-memory status, and coordinates with the LangGraph workflow.

## Acceptance Criteria

- [ ] `services/processing.py` created with `ProcessingQueue` class
- [ ] `enqueue(item_id: str) -> bool` — Adds item to processing queue; returns True only when newly queued
- [ ] `get_queue_status() -> QueueStatus` — Returns current queue state (pending count, processing items, failed items)
- [ ] `retry_failed(item_id: str | None = None) -> int` — Re-enqueues failed items (specific or all), returns count
- [ ] Background worker: starts with FastAPI lifespan, processes items from queue
- [ ] Worker calls `process_item()` from the LangGraph workflow for each item
- [ ] Configurable max concurrent processing (default 2, from `settings.max_concurrent_processing`)
- [ ] Queue status model: `QueueStatus` with `pending_count`, `processing_items` (list of item_ids), `failed_count`, `completed_count`, `total_processed`
- [ ] Queue integrates with FastAPI lifespan: `start()` on startup, `stop()` on shutdown
- [ ] Queue automatically processes newly created items (hook into item creation endpoint)

## Dependencies

- Task 7: LangGraph processing workflow (`process_item()`)
- Phase 1: `ItemRepository` for status updates, FastAPI lifespan pattern

## Deferred to Later Tasks

- **API endpoints** (`/api/processing/queue`, `/api/processing/retry`) → Task 9
- **WebSocket progress events** (`/api/ws/processing/{item_id}`) → Task 10
- **Unit tests for queue behavior** → Task 11

## Technical Notes

### Queue Architecture

- Per `docs/developer/python-backend/architecture.md`: use simple in-process queue with `asyncio`
- Use `asyncio.Queue` for pending items and a fixed worker pool for concurrency control
- The queue should be a singleton managed via FastAPI's `app.state`
- Use `maxsize=1000` on the queue to prevent memory issues during bulk imports
- Use `await queue.put()` for built-in backpressure when the queue is full

### Concurrency Model

- Start a fixed worker pool sized to `settings.max_concurrent_processing`
- Each worker loops on `queue.get()` and processes one item at a time
- This caps concurrency with stable task count and lower task creation overhead
- Use `queue.task_done()` only after each item has fully finished processing

### Status Ownership

- **The LangGraph workflow owns `processing_status` updates** (in `classify_node`, `complete_node`, `handle_error_node`)
- The queue only tracks in-memory state for reporting; it does NOT duplicate DB status updates
- This avoids race conditions between queue and workflow

### Failed Item Tracking (Hybrid Approach)

- **During runtime**: Track failed items in memory (`self.failed_items: set[str]`)
- **On startup**: Query DB for items with `processing_status = 'failed'` to rebuild `failed_items`
- This ensures `retry_failed()` works correctly after restarts

### Startup Recovery

- On startup, scan DB for items with `processing_status` in `('pending', 'processing', 'failed')`
- Re-enqueue `pending` and `processing` (interrupted) items
- Rebuild `failed_items` set from `failed` items (don't auto-enqueue these)
- **De-duplication**: Track IDs in `_in_queue` and `processing` sets to prevent double-processing
- **Backpressure**: Producers wait on `await queue.put(...)` when queue is full

### Documentation

- Update `docs/developer/python-backend/architecture.md` background processing section to reflect fixed worker pool concurrency design

## QueueStatus Model

Add to `db/models.py` for consistency with existing model patterns:

```python
class QueueStatus(BaseModel):
    """Current state of the processing queue."""
    pending_count: int
    processing_items: list[str]  # Item IDs currently being processed
    failed_count: int
    completed_count: int
    total_processed: int  # Lifetime total since startup
```

## ProcessingQueue Implementation

```python
# In services/processing.py
import asyncio
import logging

from src.config import settings
from src.db.database import db_connection
from src.db.repositories import item_repo
from src.workflows.processing import process_item

logger = logging.getLogger(__name__)


class ProcessingQueue:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1000)
        self._worker_tasks: list[asyncio.Task] = []
        self._stopping = False
        self._state_lock = asyncio.Lock()

        # In-memory tracking
        self._in_queue: set[str] = set()
        self.processing: set[str] = set()
        self.failed_items: set[str] = set()
        self.completed_count: int = 0
        self.total_processed: int = 0

    async def enqueue(self, item_id: str) -> bool:
        """Add an item to the queue with dedupe and backpressure."""
        async with self._state_lock:
            if item_id in self._in_queue or item_id in self.processing:
                return False
            self._in_queue.add(item_id)

        # Backpressure: await when queue is at maxsize.
        await self.queue.put(item_id)
        return True

    async def _process_one(self, item_id: str) -> None:
        """Process a single item."""
        async with self._state_lock:
            self.processing.add(item_id)

        try:
            result = await process_item(item_id)
            async with self._state_lock:
                if result.get("error"):
                    self.failed_items.add(item_id)
                else:
                    self.completed_count += 1
        except Exception:
            logger.exception(f"Error processing item {item_id}")
            async with self._state_lock:
                self.failed_items.add(item_id)
        finally:
            async with self._state_lock:
                self.processing.discard(item_id)
                self.total_processed += 1

    async def _worker(self) -> None:
        """Worker loop for fixed-size processing pool."""
        while True:
            if self._stopping and self.queue.empty():
                break

            try:
                item_id = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            async with self._state_lock:
                self._in_queue.discard(item_id)

            try:
                await self._process_one(item_id)
            finally:
                self.queue.task_done()

    async def start(self) -> None:
        """Start worker pool and recover items from DB."""
        async with db_connection() as db:
            # Re-enqueue pending and interrupted items.
            pending = await item_repo.get_by_status(db, "pending")
            processing = await item_repo.get_by_status(db, "processing")
            for item in pending + processing:
                await self.enqueue(item.id)

            # Rebuild failed_items set (don't auto-enqueue).
            failed = await item_repo.get_by_status(db, "failed")
            self.failed_items = {item.id for item in failed}

        self._stopping = False
        worker_count = max(1, settings.max_concurrent_processing)
        self._worker_tasks = [
            asyncio.create_task(self._worker()) for _ in range(worker_count)
        ]

    async def stop(self) -> None:
        """Gracefully stop the queue."""
        self._stopping = True

        # Let workers finish queued/in-flight items.
        try:
            await asyncio.wait_for(self.queue.join(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Queue shutdown timeout; cancelling workers")

        # Stop workers
        for task in self._worker_tasks:
            task.cancel()
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)

        logger.info("Processing queue stopped")

    def get_queue_status(self) -> "QueueStatus":
        """Return current queue status."""
        from src.db.models import QueueStatus

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
            if item_id in self.failed_items:
                self.failed_items.discard(item_id)
                await self.enqueue(item_id)
                return 1
            return 0

        # Retry all failed
        count = len(self.failed_items)
        for fid in list(self.failed_items):
            self.failed_items.discard(fid)
            await self.enqueue(fid)
        return count
```

## Integration with Item Creation

```python
# In api/items.py — after creating an item, enqueue it
@router.post("/", response_model=Item, status_code=201)
async def create_item(
    data: ItemCreate,
    db: aiosqlite.Connection = Depends(get_db_connection),
    repo: ItemRepository = Depends(get_item_repo),
    queue: ProcessingQueue = Depends(get_processing_queue),
) -> Item:
    item = await repo.create(db, data)
    await db.commit()  # Commit before enqueue so worker can see the item
    try:
        await queue.enqueue(item.id)
    except Exception:
        logger.exception(f"Failed to enqueue item {item.id} after create")
    return item
```

## Dependency Provider

```python
# In api/deps.py
from fastapi import HTTPException
from starlette.requests import Request

from src.services.processing import ProcessingQueue


def get_processing_queue(request: Request) -> ProcessingQueue:
    """Get the processing queue singleton from app state."""
    queue = getattr(request.app.state, "processing_queue", None)
    if queue is None:
        raise HTTPException(status_code=503, detail="Processing queue is not available")
    return queue
```

## Lifespan Integration

```python
# In main.py
from src.services.processing import ProcessingQueue

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    queue = ProcessingQueue()
    app.state.processing_queue = queue
    await queue.start()
    yield
    await queue.stop()
```

## Files to Create/Modify

**Create:**

- `python-backend/src/services/processing.py` — Processing queue service

**Modify:**

- `python-backend/src/db/models.py` — Add `QueueStatus` model
- `python-backend/src/services/__init__.py` — Export `ProcessingQueue`
- `python-backend/src/main.py` — Integrate queue with lifespan
- `python-backend/src/api/deps.py` — Add `get_processing_queue()` dependency
- `python-backend/src/api/items.py` — Enqueue items after creation

## Verification

```bash
cd python-backend
uv run ruff check src/
uv run mypy src/
uv run pytest -v  # Existing tests still pass
```

---

## Implementation Details

_Tracked: 2026-02-03_

### Files Changed

| File                                               | Change   | Description                                                                                                                                   |
| -------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `python-backend/src/services/processing.py`        | Created  | `ProcessingQueue` class — asyncio-based background queue with fixed worker pool, backpressure, dedup, startup recovery, and graceful shutdown |
| `python-backend/tests/services/test_processing.py` | Created  | 5 behavioral tests covering backpressure, dedup, success/failure tracking, retry error handling, and start/stop idempotency                   |
| `python-backend/src/db/models.py`                  | Modified | Added `QueueStatus` Pydantic model with pending_count, processing_items, failed_count, completed_count, total_processed                       |
| `python-backend/src/services/__init__.py`          | Modified | Exported `ProcessingQueue` in `__all__`                                                                                                       |
| `python-backend/src/main.py`                       | Modified | Integrated `ProcessingQueue` into FastAPI lifespan (create, start on startup, stop on shutdown)                                               |
| `python-backend/src/api/deps.py`                   | Modified | Added `get_processing_queue()` dependency that retrieves singleton from `app.state`                                                           |
| `python-backend/src/api/items.py`                  | Modified | Added queue injection to `create_item` endpoint; auto-enqueues after commit with error isolation                                              |
| `python-backend/tests/conftest.py`                 | Modified | Added `AsyncMock(spec=ProcessingQueue)` to `client` fixture so tests don't require a real queue                                               |
| `python-backend/tests/test_api_items.py`           | Modified | Added assertions verifying enqueue is called on successful create and not called on validation error                                          |
| `docs/developer/python-backend/architecture.md`    | Modified | Updated Task Queue section to reflect fixed worker pool design with key design decisions                                                      |

### Acceptance Criteria Status

- [x] `services/processing.py` created with `ProcessingQueue` class — `python-backend/src/services/processing.py`
- [x] `enqueue(item_id: str) -> bool` — dedup + backpressure, lines 43-65
- [x] `get_queue_status() -> QueueStatus` — returns in-memory state snapshot, lines 159-167
- [x] `retry_failed(item_id: str | None = None) -> int` — re-enqueues with error recovery, lines 169-195
- [x] Background worker: fixed pool started in `start()`, loops on `queue.get()`, lines 92-110
- [x] Worker calls `process_item()` from the LangGraph workflow, line 74
- [x] Configurable max concurrent processing via `settings.max_concurrent_processing`, line 131
- [x] `QueueStatus` model added to `db/models.py` with all specified fields
- [x] Queue integrates with FastAPI lifespan: `start()` on startup, `stop()` on shutdown — `main.py`
- [x] Queue automatically processes newly created items via `create_item` endpoint — `items.py`

---

## Learning Report

_Generated: 2026-02-03_

### Summary

Implemented an in-process background processing queue (`ProcessingQueue`) that manages the lifecycle of content processing jobs in the Cortex Python backend. The queue uses `asyncio.Queue` with a fixed worker pool for bounded concurrency, integrates with the FastAPI lifespan, and automatically enqueues items on creation. All 10 acceptance criteria were met across 2 new files and 8 modified files (342 lines added, 46 removed).

### Patterns & Decisions

1. **Fixed worker pool over task-per-item**: Workers loop on `queue.get()` rather than spawning a task per item. This caps concurrency with stable task count and lower creation overhead — matches the architecture doc recommendation.

2. **No `asyncio.Lock` for in-memory tracking**: The implementation removed the `_state_lock` from the task spec's reference implementation. Since asyncio is single-threaded and all state mutations are between `await` points, an `asyncio.Lock` is unnecessary overhead. This is a deliberate simplification.

3. **CancelledError propagation**: Both `enqueue()` and `_process_one()` explicitly re-raise `asyncio.CancelledError` to ensure clean shutdown. The worker also catches `CancelledError` from `queue.get()` to break cleanly.

4. **Error isolation in item creation**: The `create_item` endpoint commits the DB transaction before enqueuing and wraps the enqueue call in a try/except. This ensures item creation succeeds even if the queue is unavailable — the item will be recovered on next startup.

5. **Mock queue in test fixtures**: Rather than starting a real queue, tests use `AsyncMock(spec=ProcessingQueue)` on `app.state`. This avoids the need for background task management in test teardown.

6. **Idempotent start/stop**: `start()` is a no-op if workers already exist; `stop()` is a no-op if no workers. This prevents double-start issues in lifespan and allows safe repeated calls.

7. **`processed` flag in `_process_one`**: The method uses a local `processed` boolean to avoid incrementing `total_processed` if the item was cancelled before any processing attempt. This gives accurate lifetime metrics.

### Challenges & Solutions

1. **Backpressure cleanup on cancellation**: If `queue.put()` is cancelled while the item ID is already in `_in_queue`, the item would be permanently "phantom-queued." Solved by catching `CancelledError` in `enqueue()` and discarding from `_in_queue` before re-raising.

2. **Test isolation without lifespan**: The `client` fixture bypasses FastAPI's lifespan, so `app.state.processing_queue` wouldn't exist. Solved by manually setting a mock queue on `app.state` in the fixture.

3. **Retry failure recovery**: If `retry_failed("item-1")` removes the item from `failed_items` but `enqueue()` then raises, the item is lost from both sets. Solved by restoring the item to `failed_items` in the except block.

### Lessons Learned

- **What worked well**: The task spec provided a nearly complete reference implementation with clear architecture constraints. Having the status ownership rule (LangGraph owns DB status, queue only tracks in-memory) prevented a whole class of race condition bugs.
- **What could be improved**: The deferred unit tests (Task 11) mean the current test file was created anyway to cover key behaviors. Future tasks should consider whether "deferred tests" actually save scope or just shift it.
- **Recommendation**: For similar background service tasks, always include startup recovery and graceful shutdown in the initial implementation — they're much harder to retrofit.

### Documentation Impact

- **Updated**: `docs/developer/python-backend/architecture.md` — Task Queue section rewritten to reflect fixed worker pool concurrency design with key design decisions
- **Potentially affected**: Any docs referencing item creation flow should note the automatic enqueue behavior
- **New pattern worth documenting**: The mock queue fixture pattern in `conftest.py` for testing endpoints that depend on background services
