"""Abstract base class for AI providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class AIProvider(ABC):
    """Abstract base class defining the interface for AI providers.

    All AI providers (Ollama, OpenAI, etc.) must implement this interface
    to ensure consistent behavior across the application.
    """

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for a single text.

        Args:
            text: The text to embed.

        Returns:
            List of floats representing the embedding vector.

        Raises:
            AIProviderError: If embedding generation fails.
        """
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors, one per input text.

        Raises:
            AIProviderError: If embedding generation fails.
        """
        ...

    @abstractmethod
    async def chat(
        self, messages: list[dict[str, str]], system: str | None = None
    ) -> str:
        """Generate a chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            system: Optional system prompt.

        Returns:
            The assistant's response text.

        Raises:
            AIProviderError: If chat completion fails.
        """
        ...

    @abstractmethod
    async def stream_chat(
        self, messages: list[dict[str, str]], system: str | None = None
    ) -> AsyncIterator[str]:
        """Generate a streaming chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            system: Optional system prompt.

        Yields:
            Chunks of the assistant's response text.

        Raises:
            AIProviderError: If chat completion fails.
        """
        ...
