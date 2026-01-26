# Task: Implement Processing Queue API Endpoints

## Summary

Create REST API endpoints for monitoring and managing the processing queue: get queue status and retry failed processing jobs. These endpoints allow the frontend to display processing progress and let users retry failed items.

## Acceptance Criteria

- [ ] `api/processing.py` created with FastAPI router
- [ ] `GET /api/processing/queue` — Returns `QueueStatus` with pending, processing, failed, completed counts
- [ ] `POST /api/processing/retry` — Re-enqueues failed items, accepts optional `item_id` body param
- [ ] `POST /api/processing/retry` returns `{"retried_count": N}` with count of re-enqueued items
- [ ] Router registered in `main.py`
- [ ] Proper error responses: 404 if specific item_id not found for retry

## Dependencies

- Task 8: Processing queue service (`ProcessingQueue`, `QueueStatus`)
- Phase 1: FastAPI router registration pattern

## Technical Notes

- Follow the same pattern as `api/items.py` and `api/health.py`
- Use dependency injection to get the `ProcessingQueue` from `deps.py`
- The retry endpoint should accept an optional JSON body: `{"item_id": "specific-id"}` — if omitted, retry all failed items
- Per MVP plan: `GET /api/processing/queue`, `POST /api/processing/retry`

## API Specification

```python
# api/processing.py
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
    request: RetryRequest = RetryRequest(),
    queue: ProcessingQueue = Depends(get_processing_queue),
) -> RetryResponse:
    """Retry failed processing jobs."""
    count = await queue.retry_failed(request.item_id)
    return RetryResponse(retried_count=count)
```

## Files to Create/Modify

**Create:**

- `python-backend/src/api/processing.py` — Processing queue endpoints

**Modify:**

- `python-backend/src/main.py` — Register processing router
- `python-backend/src/db/models.py` — Add `RetryRequest`, `RetryResponse` models (or keep in api/processing.py)

## Verification

```bash
cd python-backend
uv run ruff check src/
uv run mypy src/

# Manual test:
# curl http://localhost:8742/api/processing/queue
# curl -X POST http://localhost:8742/api/processing/retry -H "Content-Type: application/json" -d '{}'
```
