"""Provider fakes for deterministic backend tests."""

from collections.abc import AsyncIterator

from src.db.database import EMBEDDING_DIMENSION
from src.exceptions import AIProviderError
from src.providers import AIProvider


class MockAIProvider(AIProvider):
    """Mock AI provider for tests that require deterministic behavior."""

    def __init__(
        self,
        embedding_dim: int = EMBEDDING_DIMENSION,
        should_fail: bool = False,
        chat_response: str = "Mock response",
    ) -> None:
        self.embedding_dim = embedding_dim
        self.should_fail = should_fail
        self.chat_response = chat_response
        self.embed_calls: list[str] = []
        self.embed_batch_calls: list[list[str]] = []

    async def embed(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        if self.should_fail:
            raise AIProviderError("Mock provider error")
        return [0.1] * self.embedding_dim

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.embed_batch_calls.append(texts)
        if self.should_fail:
            raise AIProviderError("Mock provider error")
        return [[0.1] * self.embedding_dim for _ in texts]

    async def chat(
        self, messages: list[dict[str, str]], system: str | None = None
    ) -> str:
        del messages, system
        return self.chat_response

    async def stream_chat(
        self, messages: list[dict[str, str]], system: str | None = None
    ) -> AsyncIterator[str]:
        del messages, system
        yield "Mock"
        yield " response"
