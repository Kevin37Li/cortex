"""Custom exception hierarchy for Cortex backend."""


class CortexError(Exception):
    """Base exception for all Cortex-related errors."""

    pass


class ItemNotFoundError(CortexError):
    """Raised when an item is not found in the database.

    Used by repository update() methods when the item doesn't exist.
    """

    def __init__(self, item_id: str) -> None:
        self.item_id = item_id
        super().__init__(f"Item not found: {item_id}")


class ChunkNotFoundError(CortexError):
    """Raised when a chunk is not found in the database."""

    def __init__(self, chunk_id: str) -> None:
        self.chunk_id = chunk_id
        super().__init__(f"Chunk not found: {chunk_id}")


class DatabaseError(CortexError):
    """Raised for database-related errors."""

    pass


class AIProviderError(CortexError):
    """Base exception for AI provider errors."""

    pass


class OllamaNotRunningError(AIProviderError):
    """Raised when Ollama server is not accessible."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        super().__init__(f"Ollama not running at {base_url}")


class OllamaModelNotFoundError(AIProviderError):
    """Raised when the requested model is not available in Ollama."""

    def __init__(self, model: str) -> None:
        self.model = model
        super().__init__(f"Model not found: {model}. Run: ollama pull {model}")


class OllamaTimeoutError(AIProviderError):
    """Raised when an Ollama operation times out."""

    def __init__(self, operation: str, timeout: float) -> None:
        self.operation = operation
        self.timeout = timeout
        super().__init__(f"Ollama {operation} timed out after {timeout}s")


class OllamaAPIResponseError(AIProviderError):
    """Raised when Ollama API returns an unexpected/malformed response."""

    def __init__(self, operation: str, model: str, response_data: dict | None) -> None:
        self.operation = operation
        self.model = model
        self.response_data = response_data
        super().__init__(
            f"Ollama {operation} returned malformed response for model '{model}': {response_data}"
        )
