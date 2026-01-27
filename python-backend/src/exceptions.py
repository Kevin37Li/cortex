"""Custom exception hierarchy for Cortex backend."""


class CortexError(Exception):
    """Base exception for all Cortex-related errors."""

    error_code: str = "cortex_error"


class ItemNotFoundError(CortexError):
    """Raised when an item is not found in the database.

    Used by repository update() methods when the item doesn't exist.
    """

    error_code: str = "item_not_found"

    def __init__(self, *, item_id: str) -> None:
        self.item_id = item_id
        super().__init__(f"Item not found: {item_id}")


class ChunkNotFoundError(CortexError):
    """Raised when a chunk is not found in the database."""

    error_code: str = "chunk_not_found"

    def __init__(self, *, chunk_id: str) -> None:
        self.chunk_id = chunk_id
        super().__init__(f"Chunk not found: {chunk_id}")


class DatabaseError(CortexError):
    """Raised for database-related errors."""

    error_code: str = "database_error"


class AIProviderError(CortexError):
    """Base exception for AI provider errors."""

    error_code: str = "ai_provider_error"


class OllamaNotRunningError(AIProviderError):
    """Raised when Ollama server is not accessible."""

    error_code: str = "ollama_not_running"

    def __init__(self, *, base_url: str) -> None:
        self.base_url = base_url
        super().__init__(f"Ollama not running at {base_url}")


class OllamaModelNotFoundError(AIProviderError):
    """Raised when the requested model is not available in Ollama."""

    error_code: str = "ollama_model_not_found"

    def __init__(self, *, model: str) -> None:
        self.model = model
        super().__init__(f"Model not found: {model}. Run: ollama pull {model}")


class OllamaTimeoutError(AIProviderError):
    """Raised when an Ollama operation times out."""

    error_code: str = "ollama_timeout"

    def __init__(self, *, operation: str, timeout: float) -> None:
        self.operation = operation
        self.timeout = timeout
        super().__init__(f"Ollama {operation} timed out after {timeout}s")


class OllamaAPIResponseError(AIProviderError):
    """Raised when Ollama API returns an unexpected/malformed response."""

    error_code: str = "ollama_api_response_error"

    def __init__(
        self, *, operation: str, model: str, response_data: dict | None
    ) -> None:
        self.operation = operation
        self.model = model
        self.response_data = response_data
        super().__init__(
            f"Ollama {operation} returned malformed response for model '{model}': {response_data}"
        )


class ProcessingError(CortexError):
    """Base exception for content processing pipeline errors."""

    error_code: str = "processing_error"

    def __init__(
        self,
        message: str,
        *,
        item_id: str | None = None,
        step: str | None = None,
    ) -> None:
        self.item_id = item_id
        self.step = step
        super().__init__(message)


class ContentParsingError(ProcessingError):
    """Raised when HTML/text content cannot be parsed."""

    error_code: str = "content_parsing_error"


class ChunkingError(ProcessingError):
    """Raised when text splitting/chunking fails."""

    error_code: str = "chunking_error"


class EmbeddingError(ProcessingError):
    """Raised when embedding generation fails during processing.

    Distinct from AIProviderError — this indicates a processing-level failure,
    not a provider connectivity issue.
    """

    error_code: str = "embedding_error"


class EmbeddingModelMismatchError(ProcessingError):
    """Raised when embedding dimensions or model are inconsistent."""

    error_code: str = "embedding_model_mismatch"


class MetadataExtractionError(ProcessingError):
    """Raised when LLM-based metadata extraction fails."""

    error_code: str = "metadata_extraction_error"
