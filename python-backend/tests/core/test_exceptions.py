"""Tests for custom exception hierarchy."""

import pytest
from src.exceptions import (
    AIProviderError,
    ChunkingError,
    ChunkNotFoundError,
    ContentParsingError,
    CortexError,
    DatabaseError,
    EmbeddingError,
    EmbeddingModelMismatchError,
    ItemNotFoundError,
    MetadataExtractionError,
    OllamaAPIResponseError,
    OllamaModelNotFoundError,
    OllamaNotRunningError,
    OllamaTimeoutError,
    ProcessingError,
    SearchError,
)


class TestErrorCodes:
    """Every exception class has a static error_code for stable API contract."""

    @pytest.mark.parametrize(
        ("cls", "expected_code"),
        [
            (CortexError, "cortex_error"),
            (ItemNotFoundError, "item_not_found"),
            (ChunkNotFoundError, "chunk_not_found"),
            (DatabaseError, "database_error"),
            (AIProviderError, "ai_provider_error"),
            (OllamaNotRunningError, "ollama_not_running"),
            (OllamaModelNotFoundError, "ollama_model_not_found"),
            (OllamaTimeoutError, "ollama_timeout"),
            (OllamaAPIResponseError, "ollama_api_response_error"),
            (ProcessingError, "processing_error"),
            (SearchError, "search_error"),
            (ContentParsingError, "content_parsing_error"),
            (ChunkingError, "chunking_error"),
            (EmbeddingError, "embedding_error"),
            (EmbeddingModelMismatchError, "embedding_model_mismatch"),
            (MetadataExtractionError, "metadata_extraction_error"),
        ],
    )
    def test_error_code(self, cls: type, expected_code: str):
        """Each exception class defines the expected error_code."""
        assert cls.error_code == expected_code


class TestProcessingError:
    """Tests for ProcessingError base class."""

    def test_basic_instantiation(self):
        exc = ProcessingError("something failed")
        assert str(exc) == "something failed"
        assert exc.item_id is None
        assert exc.step is None

    def test_with_all_context(self):
        exc = ProcessingError(
            "processing failed",
            item_id="item-123",
            step="content_parsing",
        )
        assert str(exc) == "processing failed"
        assert exc.item_id == "item-123"
        assert exc.step == "content_parsing"

    def test_inherits_from_cortex_error(self):
        exc = ProcessingError("test")
        assert isinstance(exc, CortexError)
        assert isinstance(exc, Exception)


class TestContentParsingError:
    """Tests for ContentParsingError."""

    def test_instantiation(self):
        exc = ContentParsingError("bad HTML", item_id="item-1", step="content_parsing")
        assert str(exc) == "bad HTML"
        assert exc.item_id == "item-1"
        assert exc.step == "content_parsing"

    def test_inherits_from_processing_error(self):
        exc = ContentParsingError("test")
        assert isinstance(exc, ProcessingError)
        assert isinstance(exc, CortexError)

    def test_defaults(self):
        exc = ContentParsingError("test")
        assert exc.item_id is None
        assert exc.step is None


class TestSearchError:
    """Tests for SearchError."""

    def test_basic_instantiation(self):
        exc = SearchError("search failed")
        assert str(exc) == "search failed"
        assert exc.query is None
        assert exc.step is None

    def test_with_all_context(self):
        exc = SearchError(
            "search failed at rerank",
            query="hybrid ranking",
            step="rerank",
        )
        assert str(exc) == "search failed at rerank"
        assert exc.query == "hybrid ranking"
        assert exc.step == "rerank"

    def test_inherits_from_cortex_error(self):
        exc = SearchError("test")
        assert isinstance(exc, CortexError)
        assert isinstance(exc, Exception)


class TestChunkingError:
    """Tests for ChunkingError."""

    def test_instantiation(self):
        exc = ChunkingError("split failed", item_id="item-2", step="chunking")
        assert str(exc) == "split failed"
        assert exc.item_id == "item-2"
        assert exc.step == "chunking"

    def test_inherits_from_processing_error(self):
        exc = ChunkingError("test")
        assert isinstance(exc, ProcessingError)
        assert isinstance(exc, CortexError)


class TestEmbeddingError:
    """Tests for EmbeddingError."""

    def test_instantiation(self):
        exc = EmbeddingError(
            "embedding failed",
            item_id="item-3",
            step="embedding",
        )
        assert str(exc) == "embedding failed"
        assert exc.item_id == "item-3"
        assert exc.step == "embedding"

    def test_inherits_from_processing_error(self):
        exc = EmbeddingError("test")
        assert isinstance(exc, ProcessingError)
        assert isinstance(exc, CortexError)

    def test_distinct_from_ai_provider_error(self):
        exc = EmbeddingError("test")
        assert not isinstance(exc, AIProviderError)


class TestEmbeddingModelMismatchError:
    """Tests for EmbeddingModelMismatchError."""

    def test_instantiation(self):
        exc = EmbeddingModelMismatchError(
            "dimension mismatch: expected 384, got 768",
            item_id="item-4",
            step="embedding",
        )
        assert str(exc) == "dimension mismatch: expected 384, got 768"
        assert exc.item_id == "item-4"

    def test_inherits_from_processing_error(self):
        exc = EmbeddingModelMismatchError("test")
        assert isinstance(exc, ProcessingError)
        assert isinstance(exc, CortexError)


class TestMetadataExtractionError:
    """Tests for MetadataExtractionError."""

    def test_instantiation(self):
        exc = MetadataExtractionError(
            "LLM extraction failed",
            item_id="item-5",
            step="metadata_extraction",
        )
        assert str(exc) == "LLM extraction failed"
        assert exc.item_id == "item-5"
        assert exc.step == "metadata_extraction"

    def test_inherits_from_processing_error(self):
        exc = MetadataExtractionError("test")
        assert isinstance(exc, ProcessingError)
        assert isinstance(exc, CortexError)


class TestItemNotFoundError:
    """Tests for ItemNotFoundError."""

    def test_instantiation(self):
        exc = ItemNotFoundError(item_id="abc-123")
        assert str(exc) == "Item not found: abc-123"
        assert exc.item_id == "abc-123"

    def test_inherits_from_cortex_error(self):
        exc = ItemNotFoundError(item_id="x")
        assert isinstance(exc, CortexError)


class TestChunkNotFoundError:
    """Tests for ChunkNotFoundError."""

    def test_instantiation(self):
        exc = ChunkNotFoundError(chunk_id="chunk-456")
        assert str(exc) == "Chunk not found: chunk-456"
        assert exc.chunk_id == "chunk-456"

    def test_inherits_from_cortex_error(self):
        exc = ChunkNotFoundError(chunk_id="x")
        assert isinstance(exc, CortexError)


class TestDatabaseError:
    """Tests for DatabaseError."""

    def test_instantiation(self):
        exc = DatabaseError("connection lost")
        assert str(exc) == "connection lost"

    def test_inherits_from_cortex_error(self):
        exc = DatabaseError("test")
        assert isinstance(exc, CortexError)


class TestOllamaNotRunningError:
    """Tests for OllamaNotRunningError."""

    def test_instantiation(self):
        exc = OllamaNotRunningError(base_url="http://localhost:11434")
        assert str(exc) == "Ollama not running at http://localhost:11434"
        assert exc.base_url == "http://localhost:11434"

    def test_inherits_from_ai_provider_error(self):
        exc = OllamaNotRunningError(base_url="http://localhost:11434")
        assert isinstance(exc, AIProviderError)
        assert isinstance(exc, CortexError)


class TestOllamaModelNotFoundError:
    """Tests for OllamaModelNotFoundError."""

    def test_instantiation(self):
        exc = OllamaModelNotFoundError(model="llama3")
        assert str(exc) == "Model not found: llama3. Run: ollama pull llama3"
        assert exc.model == "llama3"

    def test_inherits_from_ai_provider_error(self):
        exc = OllamaModelNotFoundError(model="x")
        assert isinstance(exc, AIProviderError)


class TestOllamaTimeoutError:
    """Tests for OllamaTimeoutError."""

    def test_instantiation(self):
        exc = OllamaTimeoutError(operation="embed", timeout=30.0)
        assert str(exc) == "Ollama embed timed out after 30.0s"
        assert exc.operation == "embed"
        assert exc.timeout == 30.0

    def test_inherits_from_ai_provider_error(self):
        exc = OllamaTimeoutError(operation="embed", timeout=10.0)
        assert isinstance(exc, AIProviderError)


class TestOllamaAPIResponseError:
    """Tests for OllamaAPIResponseError."""

    def test_instantiation(self):
        exc = OllamaAPIResponseError(
            operation="embed", model="llama3", response_data={"bad": "data"}
        )
        assert "malformed response" in str(exc)
        assert exc.operation == "embed"
        assert exc.model == "llama3"
        assert exc.response_data == {"bad": "data"}

    def test_with_none_response(self):
        exc = OllamaAPIResponseError(
            operation="generate", model="llama3", response_data=None
        )
        assert exc.response_data is None

    def test_inherits_from_ai_provider_error(self):
        exc = OllamaAPIResponseError(operation="embed", model="x", response_data=None)
        assert isinstance(exc, AIProviderError)


class TestExceptionChaining:
    """Test that processing errors work with Python's raise ... from syntax."""

    def test_exception_chaining(self):
        cause = ValueError("underlying cause")
        with pytest.raises(ContentParsingError) as exc_info:
            try:
                raise cause
            except ValueError as e:
                raise ContentParsingError(
                    "parse failed",
                    item_id="item-1",
                ) from e

        exc = exc_info.value
        assert exc.__cause__ is cause
