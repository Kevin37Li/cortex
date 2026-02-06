"""Tests for processing queue API endpoints."""

from httpx import AsyncClient
from src.db.models import QueueStatus, RetryFailedResult
from src.main import app


class TestQueueStatusEndpoint:
    """Tests for GET /api/processing/queue."""

    async def test_get_queue_status_returns_snapshot(self, client: AsyncClient) -> None:
        """Queue status endpoint should return all queue counters and processing items."""
        app.state.processing_queue.get_queue_status.return_value = QueueStatus(
            pending_count=2,
            processing_count=1,
            processing_items=["item-processing-1"],
            failed_count=3,
            completed_count=7,
            total_processed=10,
        )

        response = await client.get("/api/processing/queue")

        assert response.status_code == 200
        assert response.json() == {
            "pending_count": 2,
            "processing_count": 1,
            "processing_items": ["item-processing-1"],
            "failed_count": 3,
            "completed_count": 7,
            "total_processed": 10,
        }
        app.state.processing_queue.get_queue_status.assert_awaited_once()

    async def test_get_queue_status_returns_503_when_queue_unavailable(
        self, client: AsyncClient
    ) -> None:
        """Dependency should return 503 if processing queue is missing from app state."""
        original_queue = app.state.processing_queue
        delattr(app.state, "processing_queue")
        try:
            response = await client.get("/api/processing/queue")
        finally:
            app.state.processing_queue = original_queue

        assert response.status_code == 503
        assert response.json()["detail"] == "Processing queue is not available"


class TestRetryEndpoint:
    """Tests for POST /api/processing/retry."""

    async def test_retry_all_failed_returns_count_and_outcome(
        self, client: AsyncClient
    ) -> None:
        """Retry-all should return retried_count and outcome from service result."""
        app.state.processing_queue.retry_failed.return_value = RetryFailedResult(
            retried_count=3,
            outcome="retried",
        )

        response = await client.post("/api/processing/retry", json={})

        assert response.status_code == 200
        assert response.json() == {"retried_count": 3, "outcome": "retried"}
        app.state.processing_queue.retry_failed.assert_awaited_once_with(None)

    async def test_retry_specific_item_returns_not_in_queue_for_existing_item(
        self, client: AsyncClient
    ) -> None:
        """Existing DB item but absent from queue state returns 200 not_in_queue."""
        create_response = await client.post(
            "/api/items/",
            json={
                "title": "Retry Target",
                "content": "content",
                "content_type": "note",
            },
        )
        item_id = create_response.json()["id"]

        app.state.processing_queue.retry_failed.return_value = RetryFailedResult(
            requested_item_id=item_id,
            retried_count=0,
            outcome="not_in_queue",
        )

        response = await client.post(
            "/api/processing/retry",
            json={"item_id": item_id},
        )

        assert response.status_code == 200
        assert response.json() == {"retried_count": 0, "outcome": "not_in_queue"}
        app.state.processing_queue.retry_failed.assert_awaited_once_with(item_id)

    async def test_retry_specific_item_returns_404_when_item_missing_from_db(
        self, client: AsyncClient
    ) -> None:
        """Missing DB item should return ItemNotFoundError even if queue says not_in_queue."""
        item_id = "missing-item-id"
        app.state.processing_queue.retry_failed.return_value = RetryFailedResult(
            requested_item_id=item_id,
            retried_count=0,
            outcome="not_in_queue",
        )

        response = await client.post(
            "/api/processing/retry",
            json={"item_id": item_id},
        )

        assert response.status_code == 404
        assert response.json() == {
            "error": "item_not_found",
            "message": f"Item not found: {item_id}",
        }
