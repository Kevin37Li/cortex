"""Tests for EmbeddingService."""

from datetime import datetime
from unittest.mock import patch

import aiosqlite
import pytest
from src.db.database import EMBEDDING_DIMENSION
from src.db.models import Chunk
from src.exceptions import (
    AIProviderError,
    EmbeddingError,
    EmbeddingModelMismatchError,
)
from src.services.embeddings import (
    DEFAULT_BATCH_SIZE,
    EMBEDDING_MODEL_KEY,
    EmbeddingService,
)

from tests.fakes.providers import MockAIProvider


class TestEmbedChunks:
    """Tests for embed_chunks method."""

    async def test_embeds_empty_list_does_nothing(
        self, embedding_service: EmbeddingService, db_with_vec: aiosqlite.Connection
    ) -> None:
        """Empty chunk list should return immediately without errors."""
        await embedding_service.embed_chunks(db_with_vec, [])
        # Should not raise and should not call provider

    async def test_embeds_chunks_and_stores_in_vec_chunks(
        self,
        embedding_service: EmbeddingService,
        db_with_vec: aiosqlite.Connection,
        sample_chunks: list[Chunk],
        mock_provider: MockAIProvider,
    ) -> None:
        """Chunks should be embedded and stored in vec_chunks table."""
        await embedding_service.embed_chunks(db_with_vec, sample_chunks)
        await db_with_vec.commit()  # Caller commits

        # Verify embeddings were stored
        cursor = await db_with_vec.execute("SELECT COUNT(*) FROM vec_chunks")
        count = (await cursor.fetchone())[0]
        assert count == len(sample_chunks)

        # Verify each chunk has an embedding
        for chunk in sample_chunks:
            cursor = await db_with_vec.execute(
                "SELECT chunk_id FROM vec_chunks WHERE chunk_id = ?", [chunk.id]
            )
            row = await cursor.fetchone()
            assert row is not None

    async def test_processes_in_batches(
        self,
        db_with_vec: aiosqlite.Connection,
        mock_provider: MockAIProvider,
    ) -> None:
        """Large chunk lists should be processed in batches."""
        # Create more chunks than batch size
        batch_size = 3
        service = EmbeddingService(
            provider=mock_provider, model_name="test-model", batch_size=batch_size
        )

        now = datetime.now()
        chunks = [
            Chunk(
                id=f"chunk-{i}",
                item_id="item-1",
                chunk_index=i,
                content=f"Content {i}",
                token_count=5,
                created_at=now,
            )
            for i in range(10)
        ]

        await service.embed_chunks(db_with_vec, chunks)
        await db_with_vec.commit()

        # Should have made 4 batch calls (10 / 3 = 3.33, rounded up to 4)
        assert len(mock_provider.embed_batch_calls) == 4
        assert len(mock_provider.embed_batch_calls[0]) == 3
        assert len(mock_provider.embed_batch_calls[1]) == 3
        assert len(mock_provider.embed_batch_calls[2]) == 3
        assert len(mock_provider.embed_batch_calls[3]) == 1

    async def test_records_model_on_first_use(
        self,
        embedding_service: EmbeddingService,
        db_with_vec: aiosqlite.Connection,
        sample_chunks: list[Chunk],
    ) -> None:
        """First embedding should record the model name."""
        await embedding_service.embed_chunks(db_with_vec, sample_chunks)
        await db_with_vec.commit()

        cursor = await db_with_vec.execute(
            "SELECT value FROM app_metadata WHERE key = ?", [EMBEDDING_MODEL_KEY]
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["value"] == "test-model"

    async def test_raises_on_model_mismatch(
        self,
        db_with_vec: aiosqlite.Connection,
        sample_chunks: list[Chunk],
        mock_provider: MockAIProvider,
    ) -> None:
        """Should raise if configured model differs from stored model."""
        # First, store a different model
        await db_with_vec.execute(
            "INSERT INTO app_metadata (key, value) VALUES (?, ?)",
            [EMBEDDING_MODEL_KEY, "different-model"],
        )
        await db_with_vec.commit()

        service = EmbeddingService(provider=mock_provider, model_name="test-model")

        with pytest.raises(EmbeddingModelMismatchError) as exc_info:
            await service.embed_chunks(db_with_vec, sample_chunks)

        assert "different-model" in str(exc_info.value)
        assert "test-model" in str(exc_info.value)

    async def test_wraps_provider_errors(
        self,
        db_with_vec: aiosqlite.Connection,
        sample_chunks: list[Chunk],
    ) -> None:
        """AIProviderError should be wrapped in EmbeddingError."""
        failing_provider = MockAIProvider(should_fail=True)
        service = EmbeddingService(provider=failing_provider, model_name="test-model")

        with pytest.raises(EmbeddingError) as exc_info:
            await service.embed_chunks(db_with_vec, sample_chunks)

        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, AIProviderError)

    async def test_does_not_record_model_on_failure(
        self,
        db_with_vec: aiosqlite.Connection,
        sample_chunks: list[Chunk],
    ) -> None:
        """Model should NOT be recorded if embedding fails (atomicity)."""
        failing_provider = MockAIProvider(should_fail=True)
        service = EmbeddingService(provider=failing_provider, model_name="test-model")

        with pytest.raises(EmbeddingError):
            await service.embed_chunks(db_with_vec, sample_chunks)

        # Model should NOT have been recorded since embedding failed
        cursor = await db_with_vec.execute(
            "SELECT value FROM app_metadata WHERE key = ?", [EMBEDDING_MODEL_KEY]
        )
        row = await cursor.fetchone()
        assert row is None, "Model should not be recorded when embedding fails"

    async def test_validates_embedding_dimensions(
        self,
        db_with_vec: aiosqlite.Connection,
        sample_chunks: list[Chunk],
    ) -> None:
        """Should raise if embedding dimensions don't match expected."""
        wrong_dim_provider = MockAIProvider(embedding_dim=512)  # Wrong dimension
        service = EmbeddingService(provider=wrong_dim_provider, model_name="test-model")

        with pytest.raises(EmbeddingModelMismatchError) as exc_info:
            await service.embed_chunks(db_with_vec, sample_chunks)

        assert "512" in str(exc_info.value)
        assert str(EMBEDDING_DIMENSION) in str(exc_info.value)


class TestEmbedQuery:
    """Tests for embed_query method."""

    async def test_embeds_query_text(
        self, embedding_service: EmbeddingService, mock_provider: MockAIProvider
    ) -> None:
        """Should generate embedding for query text."""
        embedding = await embedding_service.embed_query("test query")

        assert len(embedding) == EMBEDDING_DIMENSION
        assert mock_provider.embed_calls == ["test query"]

    async def test_raises_on_empty_query(
        self, embedding_service: EmbeddingService
    ) -> None:
        """Should raise for empty or whitespace queries."""
        with pytest.raises(EmbeddingError):
            await embedding_service.embed_query("")

        with pytest.raises(EmbeddingError):
            await embedding_service.embed_query("   ")

    async def test_wraps_provider_errors(self) -> None:
        """AIProviderError should be wrapped in EmbeddingError."""
        failing_provider = MockAIProvider(should_fail=True)
        service = EmbeddingService(provider=failing_provider, model_name="test-model")

        with pytest.raises(EmbeddingError) as exc_info:
            await service.embed_query("test query")

        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, AIProviderError)

    async def test_validates_embedding_dimensions(self) -> None:
        """Should raise if embedding dimensions don't match expected."""
        wrong_dim_provider = MockAIProvider(embedding_dim=1536)
        service = EmbeddingService(provider=wrong_dim_provider, model_name="test-model")

        with pytest.raises(EmbeddingModelMismatchError) as exc_info:
            await service.embed_query("test query")

        assert "1536" in str(exc_info.value)

    async def test_checks_model_consistency_when_db_provided(
        self,
        db_with_vec: aiosqlite.Connection,
        mock_provider: MockAIProvider,
    ) -> None:
        """Should raise if model doesn't match stored model when db provided."""
        # Store a different model
        await db_with_vec.execute(
            "INSERT INTO app_metadata (key, value) VALUES (?, ?)",
            [EMBEDDING_MODEL_KEY, "different-model"],
        )
        await db_with_vec.commit()

        service = EmbeddingService(provider=mock_provider, model_name="test-model")

        with pytest.raises(EmbeddingModelMismatchError) as exc_info:
            await service.embed_query("test query", db=db_with_vec)

        assert "different-model" in str(exc_info.value)
        assert "test-model" in str(exc_info.value)

    async def test_skips_model_check_when_db_not_provided(
        self,
        db_with_vec: aiosqlite.Connection,
        mock_provider: MockAIProvider,
    ) -> None:
        """Should not check model consistency when db not provided."""
        # Store a different model
        await db_with_vec.execute(
            "INSERT INTO app_metadata (key, value) VALUES (?, ?)",
            [EMBEDDING_MODEL_KEY, "different-model"],
        )
        await db_with_vec.commit()

        service = EmbeddingService(provider=mock_provider, model_name="test-model")

        # Should succeed without db parameter (no consistency check)
        embedding = await service.embed_query("test query")
        assert len(embedding) == EMBEDDING_DIMENSION

    async def test_allows_query_when_model_matches(
        self,
        db_with_vec: aiosqlite.Connection,
        mock_provider: MockAIProvider,
    ) -> None:
        """Should allow query when configured model matches stored model."""
        # Store the same model
        await db_with_vec.execute(
            "INSERT INTO app_metadata (key, value) VALUES (?, ?)",
            [EMBEDDING_MODEL_KEY, "test-model"],
        )
        await db_with_vec.commit()

        service = EmbeddingService(provider=mock_provider, model_name="test-model")

        # Should succeed
        embedding = await service.embed_query("test query", db=db_with_vec)
        assert len(embedding) == EMBEDDING_DIMENSION


class TestModelConsistency:
    """Tests for model consistency checking."""

    async def test_allows_same_model(
        self,
        db_with_vec: aiosqlite.Connection,
        sample_chunks: list[Chunk],
        mock_provider: MockAIProvider,
    ) -> None:
        """Should allow embedding with same model as stored."""
        # Store the model
        await db_with_vec.execute(
            "INSERT INTO app_metadata (key, value) VALUES (?, ?)",
            [EMBEDDING_MODEL_KEY, "test-model"],
        )
        await db_with_vec.commit()

        service = EmbeddingService(provider=mock_provider, model_name="test-model")

        # Should not raise
        await service.embed_chunks(db_with_vec, sample_chunks)
        await db_with_vec.commit()

    async def test_uses_configured_model_name(
        self, mock_provider: MockAIProvider
    ) -> None:
        """Service should use the provided model name."""
        service = EmbeddingService(provider=mock_provider, model_name="custom-model")
        assert service._model_name == "custom-model"

    async def test_defaults_to_settings_model(
        self, mock_provider: MockAIProvider
    ) -> None:
        """Service should default to settings.embedding_model."""
        with patch("src.services.embeddings.settings") as mock_settings:
            mock_settings.embedding_model = "settings-model"
            service = EmbeddingService(provider=mock_provider)
            assert service._model_name == "settings-model"


class TestBatchSize:
    """Tests for batch size configuration."""

    def test_default_batch_size(self, mock_provider: MockAIProvider) -> None:
        """Default batch size should be 32."""
        service = EmbeddingService(provider=mock_provider)
        assert service._batch_size == DEFAULT_BATCH_SIZE
        assert service._batch_size == 32

    def test_custom_batch_size(self, mock_provider: MockAIProvider) -> None:
        """Should accept custom batch size."""
        service = EmbeddingService(provider=mock_provider, batch_size=64)
        assert service._batch_size == 64
