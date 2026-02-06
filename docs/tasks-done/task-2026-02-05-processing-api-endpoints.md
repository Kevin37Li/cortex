# Task: Implement Processing Queue API Endpoints

## Summary

Create REST API endpoints for monitoring and managing the processing queue: get queue status and retry failed processing jobs. These endpoints allow the frontend to display processing progress and let users retry failed items with deterministic response behavior.

## Acceptance Criteria

- [ ] `api/processing.py` created with FastAPI router
- [ ] `ProcessingQueue.get_queue_status()` is async and used with `await` in the endpoint
- [ ] `GET /api/processing/queue` returns `QueueStatus` with:
  - `pending_count`
  - `processing_count`
  - `processing_items`
  - `failed_count`
  - `completed_count`
  - `total_processed`
- [ ] `POST /api/processing/retry` re-enqueues failed items and accepts optional `item_id` body param
- [ ] `ProcessingQueue.retry_failed()` returns a richer result model (not just `int`) to distinguish retry outcomes
- [ ] `POST /api/processing/retry` returns `{"retried_count": N}` with count of re-enqueued items
- [ ] `POST /api/processing/retry` returns 404 when a specific `item_id` does not exist
- [ ] Router registered in `main.py`
- [ ] Optional API export added in `api/__init__.py` for consistency with package-level router exports
- [ ] Proper 503 response when processing queue is unavailable (via existing dependency behavior)

## Dependencies

- Task 8: Processing queue service (`ProcessingQueue`, `QueueStatus`)
- Task 11: Backend tests for processing endpoints
- Phase 1: FastAPI router registration pattern

## Technical Notes

- Follow the same pattern as `api/items.py` and `api/health.py`
- Use dependency injection to get the `ProcessingQueue` from `deps.py`
- The retry endpoint should accept an optional JSON body: `{"item_id": "specific-id"}` — if omitted, retry all failed items
- Per MVP plan: `GET /api/processing/queue`, `POST /api/processing/retry`
- Keep request/response models in `db/models.py` (single source of truth for API models)

## Retry Result Contract

Add a richer service result model in `db/models.py`, for example:

```python
from typing import Literal

class RetryFailedResult(BaseModel):
    requested_item_id: str | None = None
    retried_count: int = 0
    outcome: Literal["retried", "already_queued", "not_in_queue"] = "retried"
```

Use it in `ProcessingQueue.retry_failed()` so the API layer can reliably map outcomes to HTTP responses without inspecting queue internals directly.

## Response Behavior Matrix

- `POST /api/processing/retry` with no `item_id`:
  - Always `200`, returns total `retried_count`
- `POST /api/processing/retry` with `item_id`:
  - `404` when item does not exist
  - `200` with `retried_count: 1` when re-enqueued
  - `200` with `retried_count: 0` when item exists but is not currently retryable (`not_failed` or `already_queued`)

## API Specification

```python
# api/processing.py
from fastapi import APIRouter, Body, Depends

router = APIRouter(prefix="/processing", tags=["processing"])

@router.get("/queue", response_model=QueueStatus)
async def get_queue_status(
    queue: ProcessingQueue = Depends(get_processing_queue),
) -> QueueStatus:
    """Get current processing queue status."""
    return await queue.get_queue_status()

class RetryRequest(BaseModel):
    item_id: str | None = None  # None = retry all failed

class RetryResponse(BaseModel):
    retried_count: int

@router.post("/retry", response_model=RetryResponse)
async def retry_failed(
    request: RetryRequest | None = Body(default=None),
    queue: ProcessingQueue = Depends(get_processing_queue),
) -> RetryResponse:
    """Retry failed processing jobs."""
    result = await queue.retry_failed(request.item_id if request else None)
    if result.not_found and result.requested_item_id is not None:
        raise ItemNotFoundError(item_id=result.requested_item_id)
    return RetryResponse(retried_count=result.retried_count)
```

## Files to Create/Modify

**Create:**

- `python-backend/src/api/processing.py` — Processing queue endpoints

**Modify:**

- `python-backend/src/main.py` — Register processing router
- `python-backend/src/api/__init__.py` — Optional export for `processing_router`
- `python-backend/src/services/processing.py` — Make `get_queue_status()` async and return richer retry result from `retry_failed()`
- `python-backend/src/db/models.py` — Add `RetryRequest`, `RetryResponse`, `RetryFailedResult`; add `processing_count` to `QueueStatus`

## Verification

```bash
bun run python:lint
bun run python:test

# Manual test:
# curl http://localhost:8742/api/processing/queue
# curl -X POST http://localhost:8742/api/processing/retry -H "Content-Type: application/json" -d '{}'
# curl -X POST http://localhost:8742/api/processing/retry -H "Content-Type: application/json" -d '{"item_id":"missing-id"}'  # expect 404
```

---

## Implementation Details

_Tracked: 2026-02-05_

### Files Changed

| File                                               | Change   | Description                                                                                                            |
| -------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------- |
| `python-backend/src/api/processing.py`             | Created  | Processing queue API router with `GET /queue` and `POST /retry` endpoints                                              |
| `python-backend/tests/test_api_processing.py`      | Created  | API-level tests for processing endpoints (5 tests)                                                                     |
| `python-backend/src/db/models.py`                  | Modified | Added `RetryFailedResult`, `RetryRequest`, `RetryResponse` models; added `processing_count` field to `QueueStatus`     |
| `python-backend/src/services/processing.py`        | Modified | Made `get_queue_status()` async; refactored `retry_failed()` to return `RetryFailedResult` with rich outcome semantics |
| `python-backend/src/main.py`                       | Modified | Registered `processing_router` with `/api` prefix                                                                      |
| `python-backend/src/api/__init__.py`               | Modified | Added `processing_router` to package exports                                                                           |
| `python-backend/tests/services/test_processing.py` | Modified | Added 7 new tests for retry outcome semantics (`not_in_queue`, `already_queued`, bulk retry, error restoration)        |

### Dependencies Added

None — all new code uses existing FastAPI, Pydantic, and aiosqlite dependencies.

### Acceptance Criteria Status

- [x] `api/processing.py` created with FastAPI router — `python-backend/src/api/processing.py`
- [x] `ProcessingQueue.get_queue_status()` is async and used with `await` — `processing.py:159`
- [x] `GET /api/processing/queue` returns `QueueStatus` with `pending_count`, `processing_count`, `processing_items`, `failed_count`, `completed_count`, `total_processed` — `api/processing.py:15-20`
- [x] `POST /api/processing/retry` re-enqueues failed items with optional `item_id` body param — `api/processing.py:23-55`
- [x] `ProcessingQueue.retry_failed()` returns `RetryFailedResult` (rich result model) — `processing.py:173-221`
- [x] `POST /api/processing/retry` returns `{"retried_count": N, "outcome": ...}` — `api/processing.py:55`
- [x] `POST /api/processing/retry` returns 404 when specific `item_id` does not exist in DB — `api/processing.py:50-53`
- [x] Router registered in `main.py` — `main.py:100`
- [x] API export added in `api/__init__.py` — `__init__.py:4`
- [x] 503 response when processing queue unavailable — via `deps.py:80-88` (existing `get_processing_queue` dependency)

---

## Learning Report

_Generated: 2026-02-05_

### Summary

Implemented two REST endpoints for processing queue monitoring and management: `GET /api/processing/queue` for status snapshots and `POST /api/processing/retry` for re-enqueuing failed items. The implementation involved creating a new API router, adding 3 Pydantic models, making `get_queue_status()` async, and refactoring `retry_failed()` to return a rich result model for deterministic HTTP status mapping. Total: 8 files changed (2 created, 6 modified), ~200 lines of production code, ~200 lines of test code, 12 new tests added (5 API, 7 service).

### Patterns & Decisions

1. **Rich service result model (`RetryFailedResult`)**: Instead of returning a plain `int` from `retry_failed()`, the service now returns a structured result with `outcome` field (`"retried"`, `"already_queued"`, `"not_in_queue"`). This lets the API layer map outcomes to HTTP responses without inspecting queue internals. The API layer only needs to check `outcome == "not_in_queue"` + DB lookup to distinguish 404 from 200.

2. **Two-layer existence check for 404**: The queue service only knows about in-memory state. When `retry_failed()` returns `"not_in_queue"`, the API endpoint does a secondary DB lookup via `ItemRepository.get()` to determine whether to return 404 (item doesn't exist at all) or 200 with `outcome="not_in_queue"` (item exists but isn't in queue). This keeps the service layer database-agnostic.

3. **Async `get_queue_status()`**: Made async for forward compatibility even though current implementation is purely in-memory. This avoids a breaking API change when future database queries are added.

4. **Response includes `outcome` field**: The `RetryResponse` model includes `outcome` alongside `retried_count`, giving the frontend richer context than just a count (e.g., "this item is already being processed" vs "this item isn't tracked").

5. **Followed existing patterns**: Router structure mirrors `api/items.py` and `api/health.py`. Dependency injection via `deps.py`. Models in `db/models.py`. Exception handling via `ItemNotFoundError` and the existing exception handler in `main.py`.

### Challenges & Solutions

1. **Retry semantics for non-failed items**: The original spec only considered the case where an item is in `failed_items`. The implementation handles three states: items in `_in_queue` (pending), `processing` (active), and `failed_items`. Items that are pending or processing return `"already_queued"` rather than incorrectly being re-enqueued.

2. **Error rollback in single-item retry**: If `enqueue()` fails after removing an item from `failed_items`, the implementation only restores it if it was actually in `failed_items` before (using `was_failed` flag). This prevents items that were in `_in_queue` or `processing` from being incorrectly added to `failed_items` on error.

3. **Atomicity note**: Single-item checks and mutations in `retry_failed()` happen before the first `await` (the `enqueue()` call), so they execute atomically within the asyncio event loop — no lock needed.

### Lessons Learned

1. **What worked well**: The task spec's "Response Behavior Matrix" and "Retry Result Contract" sections made the implementation straightforward — every edge case was pre-specified. The `RetryFailedResult` model was an effective pattern for separating service-layer logic from HTTP semantics.

2. **Test coverage approach**: API tests mock the `ProcessingQueue` at `app.state` level, while service tests directly exercise `ProcessingQueue` methods. This gives clean separation — API tests verify HTTP contract, service tests verify business logic.

3. **Pattern to reuse**: The "rich result model" pattern (returning a structured object from service methods instead of primitive types) should be used for any service method where the API layer needs to make HTTP-level decisions based on the outcome.

### Documentation Impact

- `docs/developer/python-backend/architecture.md` may need an update to document the processing API endpoints and the rich result model pattern.
- The response behavior matrix from this task spec is a useful reference for the retry endpoint's contract — worth preserving in API documentation.
