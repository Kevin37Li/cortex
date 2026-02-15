"""Tests for processing workflow orchestration and routing."""

from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from src.db.database import db_connection, init_database
from src.db.models import (
    ChunkResult,
    ExtractedMetadata,
    ItemCreate,
    ProcessingStatus,
    ProcessingStep,
)
from src.db.repositories import chunk_repo, item_repo
from src.workflows import processing as workflow

from tests.fakes.providers import MockAIProvider


@pytest.fixture(scope="function")
async def workflow_db(temp_db_path: Path) -> AsyncIterator[None]:
    """Use a temporary database path for workflow integration tests."""
    with patch("src.config.settings.db_path", temp_db_path):
        await init_database()
        yield


async def _create_item(
    *,
    title: str = "Workflow item",
    content: str = "This is workflow content for processing tests.",
    content_type: str = "note",
) -> str:
    async with db_connection() as db:
        item = await item_repo.create(
            db,
            ItemCreate(
                title=title,
                content=content,
                content_type=content_type,
            ),
        )
        await db.commit()
        return item.id


@pytest.mark.integration
class TestProcessItem:
    """End-to-end and retry-path tests for process_item()."""

    async def test_process_item_happy_path_completes_and_persists_data(
        self, workflow_db
    ) -> None:
        """Happy path should complete and persist metadata/chunks."""
        del workflow_db
        item_id = await _create_item(
            title="Happy path item",
            content="Paragraph one.\n\nParagraph two with additional content.",
        )
        provider = MockAIProvider(
            chat_response='{"summary":"Done","concepts":["ai"],"entities":["Cortex"]}'
        )

        with patch("src.workflows.processing.OllamaProvider", return_value=provider):
            result = await workflow.process_item(item_id)

        assert result.get("error") is None
        assert result.get("embeddings_stored") is True
        assert len(result.get("chunks", [])) >= 1

        async with db_connection() as db:
            item = await item_repo.get(db, item_id)
            chunks = await chunk_repo.get_by_item(db, item_id)

        assert item is not None
        assert item.processing_status == ProcessingStatus.COMPLETED
        assert item.metadata is not None
        assert item.metadata.summary == "Done"
        assert item.metadata.concepts == ["ai"]
        assert len(chunks) >= 1

    async def test_process_item_retries_validation_then_succeeds(
        self, workflow_db
    ) -> None:
        """First validation failure should retry and then complete on success."""
        del workflow_db
        item_id = await _create_item(content="Retry path content.")
        provider = MockAIProvider()
        metadata = ExtractedMetadata(summary="Retry success", concepts=["retry"])
        chunk_side_effect = [
            [],
            [ChunkResult(content="chunk after retry", chunk_index=0, token_count=3)],
        ]

        with (
            patch("src.workflows.processing.OllamaProvider", return_value=provider),
            patch.object(
                workflow.ChunkingService,
                "chunk_text",
                side_effect=chunk_side_effect,
            ) as chunk_text_mock,
            patch.object(
                workflow.MetadataExtractor,
                "extract",
                new=AsyncMock(return_value=metadata),
            ),
            patch.object(
                workflow.EmbeddingService,
                "embed_chunks",
                new=AsyncMock(return_value=None),
            ),
        ):
            result = await workflow.process_item(item_id)

        assert chunk_text_mock.call_count == 2
        assert result.get("validation_passed") is True
        assert result.get("retry_count") == 1

        async with db_connection() as db:
            item = await item_repo.get(db, item_id)

        assert item is not None
        assert item.processing_status == ProcessingStatus.COMPLETED

    async def test_process_item_marks_failed_after_max_validation_retries(
        self, workflow_db
    ) -> None:
        """Exhausted validation retries should route to error handler and fail item."""
        del workflow_db
        item_id = await _create_item(content="Retry failure content.")
        provider = MockAIProvider()
        metadata = ExtractedMetadata(summary="Unused", concepts=["unused"])

        with (
            patch("src.workflows.processing.OllamaProvider", return_value=provider),
            patch.object(
                workflow.ChunkingService,
                "chunk_text",
                return_value=[],
            ),
            patch.object(
                workflow.MetadataExtractor,
                "extract",
                new=AsyncMock(return_value=metadata),
            ),
        ):
            result = await workflow.process_item(item_id)

        assert "Validation failed after 3 retries" in result["error"]
        assert result["error_step"] == ProcessingStep.VALIDATING
        assert result["retry_count"] == workflow.MAX_RETRIES

        async with db_connection() as db:
            item = await item_repo.get(db, item_id)

        assert item is not None
        assert item.processing_status == ProcessingStatus.FAILED
        assert item.metadata is not None
        assert item.metadata.processing_error is not None
        assert "Validation failed after 3 retries" in item.metadata.processing_error
        assert item.metadata.error_step == ProcessingStep.VALIDATING

    async def test_process_item_missing_item_routes_to_error_handling(
        self, workflow_db
    ) -> None:
        """Missing item from classify node should end with error in final state."""
        del workflow_db
        provider = MockAIProvider()

        with patch("src.workflows.processing.OllamaProvider", return_value=provider):
            result = await workflow.process_item("missing-item-id")

        assert result["error"] == "Item not found: missing-item-id"
        assert result["error_step"] == ProcessingStep.CLASSIFY


class TestEmitProcessingUpdate:
    """Contract tests for emit_processing_update()."""

    def test_emit_processing_update_emits_status_step_progress_and_default_message(
        self,
    ) -> None:
        """Emit should include mapped status/progress/message values."""
        updates = []
        state: workflow.ProcessingState = {
            "item_id": "item-1",
            "emit_update": updates.append,
            "last_progress": 0.0,
        }

        progress = workflow.emit_processing_update(state, ProcessingStep.PARSING)

        assert progress == workflow.STEP_PROGRESS[ProcessingStep.PARSING]
        assert len(updates) == 1
        update = updates[0]
        assert update.step == ProcessingStep.PARSING
        assert update.status == ProcessingStatus.PROCESSING
        assert update.progress == workflow.STEP_PROGRESS[ProcessingStep.PARSING]
        assert update.message == workflow.STEP_MESSAGES[ProcessingStep.PARSING]

    def test_emit_processing_update_failed_uses_last_progress_and_message_override(
        self,
    ) -> None:
        """Failed step should keep last progress and honor explicit message."""
        updates = []
        state: workflow.ProcessingState = {
            "item_id": "item-2",
            "emit_update": updates.append,
            "last_progress": 0.65,
        }

        progress = workflow.emit_processing_update(
            state,
            ProcessingStep.FAILED,
            message="custom failure",
        )

        assert progress == 0.65
        assert len(updates) == 1
        update = updates[0]
        assert update.step == ProcessingStep.FAILED
        assert update.status == ProcessingStatus.FAILED
        assert update.progress == 0.65
        assert update.message == "custom failure"

    def test_emit_processing_update_returns_none_when_emitter_or_item_missing(
        self,
    ) -> None:
        """Emit should no-op when required state fields are missing."""
        assert workflow.emit_processing_update({}, ProcessingStep.CLASSIFY) is None
        assert (
            workflow.emit_processing_update(
                {"item_id": "item-3"}, ProcessingStep.CLASSIFY
            )
            is None
        )


class TestRoutingHelpers:
    """Tests for routing helper functions."""

    def test_route_or_error_routes_to_next_node_when_no_error(self) -> None:
        """Router should continue to next node when no error is present."""
        router = workflow.route_or_error("parse")

        assert router({"item_id": "item-1"}) == "parse"

    def test_route_or_error_routes_to_handle_error_when_error_exists(self) -> None:
        """Router should jump to handle_error when error is present."""
        router = workflow.route_or_error("parse")

        assert router({"item_id": "item-1", "error": "boom"}) == "handle_error"

    def test_route_after_validation_routes_to_handle_error_on_error(self) -> None:
        """Validation router should prioritize explicit errors."""
        assert workflow.route_after_validation({"error": "boom"}) == "handle_error"

    def test_route_after_validation_routes_to_persist_on_success(self) -> None:
        """Validation router should persist when validation passes."""
        assert workflow.route_after_validation({"validation_passed": True}) == "persist"

    def test_route_after_validation_routes_to_retry_before_max_retries(self) -> None:
        """Validation router should retry while retry_count is below max."""
        assert workflow.route_after_validation({"retry_count": 1}) == "retry"

    def test_route_after_validation_routes_to_handle_error_at_max_retries(self) -> None:
        """Validation router should fail once max retries are exhausted."""
        assert (
            workflow.route_after_validation({"retry_count": workflow.MAX_RETRIES})
            == "handle_error"
        )
