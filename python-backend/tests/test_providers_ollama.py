"""Tests for Ollama AI provider."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from src.exceptions import (
    OllamaAPIResponseError,
    OllamaModelNotFoundError,
    OllamaNotRunningError,
    OllamaTimeoutError,
)
from src.providers import OllamaProvider
from src.providers.models import ModelInfo


@pytest.fixture
def provider():
    """Create an OllamaProvider instance for testing."""
    return OllamaProvider(
        base_url="http://localhost:11434",
        embedding_model="nomic-embed-text",
        chat_model="llama3.2:3b",
        timeout=30.0,
        embed_timeout=60.0,
        availability_timeout=5.0,
    )


class TestOllamaProviderInit:
    """Tests for OllamaProvider initialization."""

    def test_init_default_values(self):
        """Test provider initializes with default values from settings."""
        provider = OllamaProvider()
        assert provider.base_url == "http://localhost:11434"
        assert provider.embedding_model == "nomic-embed-text"
        assert provider.chat_model == "llama3.2:3b"
        assert provider.timeout == 30.0
        assert provider.embed_timeout == 60.0
        assert provider.availability_timeout == 5.0

    def test_init_custom_values(self):
        """Test provider initializes with custom values."""
        provider = OllamaProvider(
            base_url="http://custom:1234",
            embedding_model="custom-embed",
            chat_model="custom-chat",
            timeout=10.0,
            embed_timeout=20.0,
            availability_timeout=2.0,
        )
        assert provider.base_url == "http://custom:1234"
        assert provider.embedding_model == "custom-embed"
        assert provider.chat_model == "custom-chat"
        assert provider.timeout == 10.0
        assert provider.embed_timeout == 20.0
        assert provider.availability_timeout == 2.0

    def test_init_strips_trailing_slash(self):
        """Test provider strips trailing slash from base_url."""
        provider = OllamaProvider(base_url="http://localhost:11434/")
        assert provider.base_url == "http://localhost:11434"


class TestOllamaProviderIsAvailable:
    """Tests for OllamaProvider.is_available method."""

    async def test_is_available_returns_true_when_server_responds(self, provider):
        """Test is_available returns True when server responds with 200."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await provider.is_available()
            assert result is True

    async def test_is_available_returns_false_on_connect_error(self, provider):
        """Test is_available returns False when connection fails."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await provider.is_available()
            assert result is False

    async def test_is_available_returns_false_on_timeout(self, provider):
        """Test is_available returns False when request times out."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await provider.is_available()
            assert result is False


class TestOllamaProviderListModels:
    """Tests for OllamaProvider.list_models method."""

    async def test_list_models_returns_model_info(self, provider):
        """Test list_models returns list of ModelInfo objects."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {
                    "name": "llama3.2:3b",
                    "size": 1234567890,
                    "modified_at": "2024-01-15T10:30:00Z",
                    "digest": "abc123",
                },
                {
                    "name": "nomic-embed-text",
                    "size": 987654321,
                },
            ]
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            models = await provider.list_models()
            assert len(models) == 2
            assert all(isinstance(m, ModelInfo) for m in models)
            assert models[0].name == "llama3.2:3b"
            assert models[0].size == 1234567890
            assert models[1].name == "nomic-embed-text"

    async def test_list_models_raises_not_running_on_connect_error(self, provider):
        """Test list_models raises OllamaNotRunningError on connection failure."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(OllamaNotRunningError) as exc_info:
                await provider.list_models()
            assert provider.base_url in str(exc_info.value)

    async def test_list_models_raises_timeout_error(self, provider):
        """Test list_models raises OllamaTimeoutError on timeout."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(OllamaTimeoutError) as exc_info:
                await provider.list_models()
            assert "list_models" in str(exc_info.value)


class TestOllamaProviderEmbed:
    """Tests for OllamaProvider.embed method."""

    async def test_embed_returns_embedding_vector(self, provider):
        """Test embed returns list of floats."""
        mock_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"embedding": mock_embedding}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await provider.embed("test text")
            assert result == mock_embedding

    async def test_embed_raises_model_not_found_on_404(self, provider):
        """Test embed raises OllamaModelNotFoundError on 404 response."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(OllamaModelNotFoundError) as exc_info:
                await provider.embed("test text")
            assert provider.embedding_model in str(exc_info.value)

    async def test_embed_raises_not_running_on_connect_error(self, provider):
        """Test embed raises OllamaNotRunningError on connection failure."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(OllamaNotRunningError):
                await provider.embed("test text")

    async def test_embed_raises_timeout_error(self, provider):
        """Test embed raises OllamaTimeoutError on timeout."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(OllamaTimeoutError) as exc_info:
                await provider.embed("test text")
            assert "embed" in str(exc_info.value)

    async def test_embed_raises_api_response_error_on_missing_embedding(self, provider):
        """Test embed raises OllamaAPIResponseError when embedding key is missing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"some_other_key": "value"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(OllamaAPIResponseError) as exc_info:
                await provider.embed("test text")
            assert "embed" in str(exc_info.value)
            assert provider.embedding_model in str(exc_info.value)


class TestOllamaProviderEmbedBatch:
    """Tests for OllamaProvider.embed_batch method."""

    async def test_embed_batch_returns_multiple_embeddings(self, provider):
        """Test embed_batch returns embedding for each input text."""
        mock_embeddings = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9],
        ]
        call_count = 0

        def mock_json():
            nonlocal call_count
            result = {"embedding": mock_embeddings[call_count]}
            call_count += 1
            return result

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = mock_json

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await provider.embed_batch(["text1", "text2", "text3"])
            assert len(result) == 3
            assert result == mock_embeddings


class TestOllamaProviderChat:
    """Tests for OllamaProvider.chat method."""

    async def test_chat_returns_response_content(self, provider):
        """Test chat returns the assistant's response text."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "message": {"role": "assistant", "content": "Hello! How can I help?"}
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            messages = [{"role": "user", "content": "Hello!"}]
            result = await provider.chat(messages)
            assert result == "Hello! How can I help?"

    async def test_chat_with_system_prompt(self, provider):
        """Test chat includes system prompt in payload."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "message": {"role": "assistant", "content": "I am helpful."}
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            messages = [{"role": "user", "content": "Who are you?"}]
            await provider.chat(messages, system="You are a helpful assistant.")

            # Verify system was passed in the payload
            call_args = mock_client.post.call_args
            payload = call_args.kwargs["json"]
            assert payload["system"] == "You are a helpful assistant."

    async def test_chat_raises_model_not_found_on_404(self, provider):
        """Test chat raises OllamaModelNotFoundError on 404 response."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(OllamaModelNotFoundError) as exc_info:
                await provider.chat([{"role": "user", "content": "Hello"}])
            assert provider.chat_model in str(exc_info.value)

    async def test_chat_raises_not_running_on_connect_error(self, provider):
        """Test chat raises OllamaNotRunningError on connection failure."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(OllamaNotRunningError):
                await provider.chat([{"role": "user", "content": "Hello"}])

    async def test_chat_raises_api_response_error_on_missing_message(self, provider):
        """Test chat raises OllamaAPIResponseError when message key is missing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"some_other_key": "value"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(OllamaAPIResponseError) as exc_info:
                await provider.chat([{"role": "user", "content": "Hello"}])
            assert "chat" in str(exc_info.value)
            assert provider.chat_model in str(exc_info.value)

    async def test_chat_raises_api_response_error_on_missing_content(self, provider):
        """Test chat raises OllamaAPIResponseError when content key is missing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"message": {"role": "assistant"}}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(OllamaAPIResponseError) as exc_info:
                await provider.chat([{"role": "user", "content": "Hello"}])
            assert "chat" in str(exc_info.value)
            assert provider.chat_model in str(exc_info.value)


class TestOllamaProviderStreamChat:
    """Tests for OllamaProvider.stream_chat method."""

    async def test_stream_chat_yields_content_chunks(self, provider):
        """Test stream_chat yields content from each chunk."""
        chunks = [
            json.dumps({"message": {"content": "Hello"}}),
            json.dumps({"message": {"content": " world"}}),
            json.dumps({"message": {"content": "!"}}),
        ]

        async def mock_aiter_lines():
            for chunk in chunks:
                yield chunk

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines

        # Create a context manager for the stream response
        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.stream = MagicMock(return_value=mock_stream_cm)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            messages = [{"role": "user", "content": "Hello"}]
            result_chunks = []
            async for chunk in provider.stream_chat(messages):
                result_chunks.append(chunk)

            assert result_chunks == ["Hello", " world", "!"]

    async def test_stream_chat_raises_model_not_found_on_404(self, provider):
        """Test stream_chat raises OllamaModelNotFoundError on 404."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.stream = MagicMock(return_value=mock_stream_cm)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(OllamaModelNotFoundError):
                async for _ in provider.stream_chat(
                    [{"role": "user", "content": "Hello"}]
                ):
                    pass

    async def test_stream_chat_raises_not_running_on_connect_error(self, provider):
        """Test stream_chat raises OllamaNotRunningError on connection failure."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.stream = MagicMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(OllamaNotRunningError):
                async for _ in provider.stream_chat(
                    [{"role": "user", "content": "Hello"}]
                ):
                    pass
