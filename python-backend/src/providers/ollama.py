"""Ollama AI provider implementation."""

import json
from collections.abc import AsyncIterator
from datetime import datetime

import httpx

from src.config import settings
from src.exceptions import (
    OllamaAPIResponseError,
    OllamaModelNotFoundError,
    OllamaNotRunningError,
    OllamaTimeoutError,
)
from src.providers import AIProvider, ModelInfo


class OllamaProvider(AIProvider):
    """AI provider implementation for Ollama local inference.

    Provides embeddings and chat completions using local Ollama server.
    """

    def __init__(
        self,
        base_url: str = settings.ollama_host,
        embedding_model: str = settings.embedding_model,
        chat_model: str = settings.chat_model,
        timeout: float = settings.ollama_timeout,
        embed_timeout: float = settings.ollama_embed_timeout,
        availability_timeout: float = settings.ollama_availability_timeout,
    ) -> None:
        """Initialize the Ollama provider.

        Args:
            base_url: Ollama server URL.
            embedding_model: Model to use for embeddings.
            chat_model: Model to use for chat completions.
            timeout: General request timeout in seconds.
            embed_timeout: Embedding request timeout in seconds (longer for model loading).
            availability_timeout: Timeout for availability checks in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.embedding_model = embedding_model
        self.chat_model = chat_model
        self.timeout = timeout
        self.embed_timeout = embed_timeout
        self.availability_timeout = availability_timeout

    async def is_available(self) -> bool:
        """Check if Ollama server is accessible.

        Returns:
            True if server responds, False otherwise.
        """
        try:
            async with httpx.AsyncClient(timeout=self.availability_timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def list_models(self) -> list[ModelInfo]:
        """List available models on the Ollama server.

        Returns:
            List of ModelInfo objects for available models.

        Raises:
            OllamaNotRunningError: If Ollama server is not accessible.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()

                models = []
                for model_data in data.get("models", []):
                    modified_at = None
                    if model_data.get("modified_at"):
                        try:
                            modified_at = datetime.fromisoformat(
                                model_data["modified_at"].replace("Z", "+00:00")
                            )
                        except (ValueError, TypeError):
                            pass

                    models.append(
                        ModelInfo(
                            name=model_data.get("name", ""),
                            size=model_data.get("size"),
                            modified_at=modified_at,
                            digest=model_data.get("digest"),
                        )
                    )
                return models
        except httpx.ConnectError as e:
            raise OllamaNotRunningError(base_url=self.base_url) from e
        except httpx.TimeoutException as e:
            raise OllamaTimeoutError(
                operation="list_models", timeout=self.timeout
            ) from e

    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for a single text.

        Args:
            text: The text to embed.

        Returns:
            List of floats representing the embedding vector.

        Raises:
            OllamaNotRunningError: If Ollama server is not accessible.
            OllamaModelNotFoundError: If the embedding model is not available.
            OllamaTimeoutError: If the request times out.
        """
        try:
            async with httpx.AsyncClient(timeout=self.embed_timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.embedding_model, "prompt": text},
                )

                if response.status_code == 404:
                    raise OllamaModelNotFoundError(model=self.embedding_model)

                response.raise_for_status()
                data = response.json()
                embedding = data.get("embedding") if isinstance(data, dict) else None
                if not isinstance(embedding, list) or not all(
                    isinstance(value, int | float) for value in embedding
                ):
                    raise OllamaAPIResponseError(
                        operation="embed",
                        model=self.embedding_model,
                        response_data=data,
                    )
                return [float(value) for value in embedding]
        except httpx.ConnectError as e:
            raise OllamaNotRunningError(base_url=self.base_url) from e
        except httpx.TimeoutException as e:
            raise OllamaTimeoutError(
                operation="embed", timeout=self.embed_timeout
            ) from e

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors, one per input text.

        Raises:
            OllamaNotRunningError: If Ollama server is not accessible.
            OllamaModelNotFoundError: If the embedding model is not available.
            OllamaTimeoutError: If the request times out.
        """
        embeddings = []
        for text in texts:
            embedding = await self.embed(text)
            embeddings.append(embedding)
        return embeddings

    async def chat(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        json_mode: bool = False,
        json_schema: dict[str, object] | None = None,
    ) -> str:
        """Generate a chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            system: Optional system prompt.
            json_mode: If True, request JSON-only response from Ollama.
            json_schema: Optional JSON schema for structured output.

        Returns:
            The assistant's response text.

        Raises:
            OllamaNotRunningError: If Ollama server is not accessible.
            OllamaModelNotFoundError: If the chat model is not available.
            OllamaTimeoutError: If the request times out.
        """
        try:
            payload: dict = {
                "model": self.chat_model,
                "messages": messages,
                "stream": False,
            }

            if system:
                payload["system"] = system
            if json_schema is not None:
                payload["format"] = json_schema
            elif json_mode:
                payload["format"] = "json"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )

                if response.status_code == 404:
                    raise OllamaModelNotFoundError(model=self.chat_model)

                response.raise_for_status()
                data = response.json()
                message = data.get("message") if isinstance(data, dict) else None
                content = message.get("content") if isinstance(message, dict) else None
                if not isinstance(content, str):
                    raise OllamaAPIResponseError(
                        operation="chat", model=self.chat_model, response_data=data
                    )
                return content
        except httpx.ConnectError as e:
            raise OllamaNotRunningError(base_url=self.base_url) from e
        except httpx.TimeoutException as e:
            raise OllamaTimeoutError(operation="chat", timeout=self.timeout) from e

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
            OllamaNotRunningError: If Ollama server is not accessible.
            OllamaModelNotFoundError: If the chat model is not available.
            OllamaTimeoutError: If the request times out.
        """
        payload: dict = {
            "model": self.chat_model,
            "messages": messages,
            "stream": True,
        }

        if system:
            payload["system"] = system

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                ) as response:
                    if response.status_code == 404:
                        raise OllamaModelNotFoundError(model=self.chat_model)

                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                message = (
                                    data.get("message")
                                    if isinstance(data, dict)
                                    else None
                                )
                                content = (
                                    message.get("content")
                                    if isinstance(message, dict)
                                    else None
                                )
                                if isinstance(content, str) and content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
        except httpx.ConnectError as e:
            raise OllamaNotRunningError(base_url=self.base_url) from e
        except httpx.TimeoutException as e:
            raise OllamaTimeoutError(
                operation="stream_chat", timeout=self.timeout
            ) from e
