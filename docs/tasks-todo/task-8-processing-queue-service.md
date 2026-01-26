# Task: Implement Processing Queue Service

## Summary

Create an in-process background processing queue that manages the lifecycle of content processing jobs. When items are created, they're enqueued for processing. The queue runs a worker that processes items sequentially (configurable concurrency), tracks status, and emits progress events.

## Acceptance Criteria

- [ ] `services/processing.py` created with `ProcessingQueue` class
- [ ] `enqueue(item_id: str) -> None` — Adds item to processing queue
- [ ] `get_queue_status() -> QueueStatus` — Returns current queue state (pending count, processing items, failed items)
- [ ] `retry_failed(item_id: str | None = None) -> int` — Re-enqueues failed items (specific or all), returns count
- [ ] Background worker: starts with FastAPI lifespan, processes items from queue
- [ ] Worker calls `process_item()` from the LangGraph workflow for each item
- [ ] Configurable max concurrent processing (default 2, from `settings.max_concurrent_processing`)
- [ ] Queue status model: `QueueStatus` with `pending_count`, `processing_items` (list of item_ids), `failed_count`, `completed_count`
- [ ] Queue integrates with FastAPI lifespan: `start()` on startup, `stop()` on shutdown
- [ ] Queue automatically processes newly created items (hook into item creation endpoint)

## Dependencies

- Task 7: LangGraph processing workflow (`process_item()`)
- Phase 1: `ItemRepository` for status updates, FastAPI lifespan pattern

## Technical Notes

- Per `docs/developer/python-backend/architecture.md`: use simple in-process queue with `asyncio`
- Use `asyncio.Queue` for the pending queue and `asyncio.Semaphore` for concurrency control
- Store processing state in memory (not persisted across restarts) — on restart, re-scan for `pending` and `processing` status items
- Worker should update item `processing_status` to `'processing'` when it starts, `'completed'` or `'failed'` when done
- On startup, scan DB for items with `processing_status = 'processing'` (interrupted) and re-enqueue them
- The queue should be a singleton managed via FastAPI's `app.state`

## QueueStatus Model

```python
class QueueStatus(BaseModel):
    """Current state of the processing queue."""
    pending_count: int
    processing_items: list[str]  # Item IDs currently being processed
    failed_count: int
    completed_count: int
    total_processed: int  # Lifetime total since startup
```

## Integration with Item Creation

```python
# In api/items.py — after creating an item, enqueue it
@router.post("/", response_model=Item, status_code=201)
async def create_item(
    data: ItemCreate,
    repo: ItemRepository = Depends(get_item_repository),
    queue: ProcessingQueue = Depends(get_processing_queue),
) -> Item:
    item = await repo.create(data)
    await queue.enqueue(item.id)
    return item
```

## Lifespan Integration

```python
# In main.py
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
