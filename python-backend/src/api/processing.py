"""Processing queue monitoring and management endpoints."""

import aiosqlite
from fastapi import APIRouter, Body, Depends

from ..db.models import QueueStatus, RetryRequest, RetryResponse
from ..db.repositories import ItemRepository
from ..exceptions import ItemNotFoundError
from ..services.processing import ProcessingQueue
from .deps import get_db_connection, get_item_repo, get_processing_queue

router = APIRouter(prefix="/processing", tags=["processing"])


@router.get("/queue", response_model=QueueStatus)
async def get_queue_status(
    queue: ProcessingQueue = Depends(get_processing_queue),
) -> QueueStatus:
    """Get current processing queue status."""
    return await queue.get_queue_status()


@router.post(
    "/retry",
    response_model=RetryResponse,
    responses={404: {"description": "Item not found"}},
)
async def retry_failed(
    request: RetryRequest | None = Body(default=None),
    queue: ProcessingQueue = Depends(get_processing_queue),
    db: aiosqlite.Connection = Depends(get_db_connection),
    repo: ItemRepository = Depends(get_item_repo),
) -> RetryResponse:
    """Retry failed processing jobs.

    If item_id is provided, retries that specific item.
    If omitted (or body is empty/null), retries all failed items.

    Queue-only outcome semantics:
    - "not_in_queue": item is not currently tracked in pending/processing/failed sets
    - "already_queued": item is already pending/processing

    For specific item retries, the API distinguishes:
    - 404 when item does not exist in the database
    - 200 with outcome="not_in_queue" when item exists but is not in queue state
    """
    item_id = request.item_id if request else None
    result = await queue.retry_failed(item_id)

    if item_id is not None and result.outcome == "not_in_queue":
        item = await repo.get(db, item_id)
        if item is None:
            raise ItemNotFoundError(item_id=item_id)

    return RetryResponse(retried_count=result.retried_count, outcome=result.outcome)
