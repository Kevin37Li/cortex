"""Tests for MetadataExtractor service."""

from collections.abc import AsyncIterator

import pytest
from src.db.models import ExtractedMetadata
from src.exceptions import AIProviderError, MetadataExtractionError
from src.providers import AIProvider
from src.services.extraction import MAX_EXTRACTION_CHARS, MetadataExtractor


class MockAIProvider(AIProvider):
    """Mock provider for testing extraction service."""

    def __init__(self, response: str = "", should_fail: bool = False) -> None:
        self.response = response
        self.should_fail = should_fail
        self.chat_calls: list[dict] = []

    async def embed(self, text: str) -> list[float]:
        return [0.1] * 768

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 768 for _ in texts]

    async def chat(
        self, messages: list[dict[str, str]], system: str | None = None
    ) -> str:
        self.chat_calls.append({"messages": messages, "system": system})
        if self.should_fail:
            raise AIProviderError("Mock provider error")
        return self.response

    async def stream_chat(
        self, messages: list[dict[str, str]], system: str | None = None
    ) -> AsyncIterator[str]:
        yield "Mock response"


class TestExtractValidJson:
    """Tests for extraction with valid JSON responses."""

    @pytest.mark.asyncio
    async def test_extract_valid_json(self) -> None:
        """Test extraction with valid JSON response."""
        mock_response = '{"summary": "Test summary.", "concepts": ["AI", "ML"], "entities": ["OpenAI"]}'
        provider = MockAIProvider(mock_response)
        extractor = MetadataExtractor(provider)

        result = await extractor.extract("Test content")

        assert result.summary == "Test summary."
        assert result.concepts == ["AI", "ML"]
        assert result.entities == ["OpenAI"]

    @pytest.mark.asyncio
    async def test_extract_with_title(self) -> None:
        """Test extraction includes title in prompt when provided."""
        mock_response = '{"summary": "About ML", "concepts": ["ML"], "entities": []}'
        provider = MockAIProvider(mock_response)
        extractor = MetadataExtractor(provider)

        await extractor.extract("Test content", title="Machine Learning Guide")

        # Verify title was included in the prompt
        assert len(provider.chat_calls) == 1
        user_message = provider.chat_calls[0]["messages"][0]["content"]
        assert "Title: Machine Learning Guide" in user_message

    @pytest.mark.asyncio
    async def test_extract_without_title(self) -> None:
        """Test extraction works without title."""
        mock_response = '{"summary": "Summary", "concepts": [], "entities": []}'
        provider = MockAIProvider(mock_response)
        extractor = MetadataExtractor(provider)

        await extractor.extract("Test content")

        user_message = provider.chat_calls[0]["messages"][0]["content"]
        assert "Title:" not in user_message

    @pytest.mark.asyncio
    async def test_extract_json_in_code_block(self) -> None:
        """Test extraction handles JSON wrapped in markdown code blocks."""
        mock_response = """Here is the extracted metadata:
```json
{"summary": "Wrapped JSON", "concepts": ["coding"], "entities": []}
```"""
        provider = MockAIProvider(mock_response)
        extractor = MetadataExtractor(provider)

        result = await extractor.extract("Test content")

        assert result.summary == "Wrapped JSON"
        assert result.concepts == ["coding"]

    @pytest.mark.asyncio
    async def test_extract_json_with_extra_text(self) -> None:
        """Test extraction finds JSON even with surrounding text."""
        mock_response = 'Sure, here is the metadata: {"summary": "Found", "concepts": ["test"], "entities": []}'
        provider = MockAIProvider(mock_response)
        extractor = MetadataExtractor(provider)

        result = await extractor.extract("Test content")

        assert result.summary == "Found"

    @pytest.mark.asyncio
    async def test_extract_json_with_braces_in_strings(self) -> None:
        """Test extraction handles braces inside JSON string values."""
        # JSON with braces in the summary text
        mock_response = '{"summary": "The function uses {config} syntax.", "concepts": ["code"], "entities": []}'
        provider = MockAIProvider(mock_response)
        extractor = MetadataExtractor(provider)

        result = await extractor.extract("Test content")

        assert result.summary == "The function uses {config} syntax."
        assert result.concepts == ["code"]


class TestExtractPartialJson:
    """Tests for graceful handling of malformed/partial JSON."""

    @pytest.mark.asyncio
    async def test_extract_invalid_json(self) -> None:
        """Test graceful handling of completely invalid response."""
        provider = MockAIProvider("Invalid JSON response without any braces")
        extractor = MetadataExtractor(provider)

        result = await extractor.extract("Test content")

        # Should return empty defaults, not raise
        assert isinstance(result, ExtractedMetadata)
        assert result.summary == ""
        assert result.concepts == []
        assert result.entities == []

    @pytest.mark.asyncio
    async def test_extract_malformed_json(self) -> None:
        """Test handling of syntactically invalid JSON."""
        provider = MockAIProvider('{"summary": "Missing quotes, concepts: []}')
        extractor = MetadataExtractor(provider)

        result = await extractor.extract("Test content")

        assert isinstance(result, ExtractedMetadata)
        assert result.summary == ""

    @pytest.mark.asyncio
    async def test_extract_partial_fields(self) -> None:
        """Test handling of JSON with missing fields."""
        mock_response = '{"summary": "Only summary here"}'
        provider = MockAIProvider(mock_response)
        extractor = MetadataExtractor(provider)

        result = await extractor.extract("Test content")

        assert result.summary == "Only summary here"
        assert result.concepts == []
        assert result.entities == []

    @pytest.mark.asyncio
    async def test_extract_wrong_types(self) -> None:
        """Test handling of JSON with wrong field types."""
        mock_response = '{"summary": 123, "concepts": "not a list", "entities": null}'
        provider = MockAIProvider(mock_response)
        extractor = MetadataExtractor(provider)

        result = await extractor.extract("Test content")

        assert result.summary == ""  # Number filtered out
        assert result.concepts == []  # String instead of list filtered out
        assert result.entities == []  # null filtered out

    @pytest.mark.asyncio
    async def test_extract_mixed_list_items(self) -> None:
        """Test filtering non-string items from lists."""
        mock_response = '{"summary": "Test", "concepts": ["valid", 123, null, "also valid"], "entities": []}'
        provider = MockAIProvider(mock_response)
        extractor = MetadataExtractor(provider)

        result = await extractor.extract("Test content")

        assert result.concepts == ["valid", "also valid"]

    @pytest.mark.asyncio
    async def test_extract_non_object_json(self) -> None:
        """Test handling of valid JSON that isn't an object (e.g., array)."""
        # LLM might return an array instead of an object
        mock_response = '["item1", "item2"]'
        provider = MockAIProvider(mock_response)
        extractor = MetadataExtractor(provider)

        result = await extractor.extract("Test content")

        # Should return empty defaults, not raise AttributeError
        assert isinstance(result, ExtractedMetadata)
        assert result.summary == ""
        assert result.concepts == []
        assert result.entities == []


class TestTextTruncation:
    """Tests for text truncation behavior."""

    @pytest.mark.asyncio
    async def test_truncate_long_text(self) -> None:
        """Test text truncation for long inputs."""
        provider = MockAIProvider('{"summary": "", "concepts": [], "entities": []}')
        extractor = MetadataExtractor(provider)
        long_text = "x" * 20000

        result = await extractor.extract(long_text)

        # Should complete without error (text was truncated)
        assert isinstance(result, ExtractedMetadata)

        # Verify truncation happened
        user_message = provider.chat_calls[0]["messages"][0]["content"]
        # Text should be truncated + "..." added
        assert len(user_message) < len(long_text)
        assert "..." in user_message

    @pytest.mark.asyncio
    async def test_short_text_not_truncated(self) -> None:
        """Test that short text is not modified."""
        provider = MockAIProvider('{"summary": "", "concepts": [], "entities": []}')
        extractor = MetadataExtractor(provider)
        short_text = "Short content"

        await extractor.extract(short_text)

        user_message = provider.chat_calls[0]["messages"][0]["content"]
        assert short_text in user_message
        # Should not have truncation indicator unless text was truncated
        assert "..." not in user_message or len(short_text) <= MAX_EXTRACTION_CHARS

    @pytest.mark.asyncio
    async def test_truncation_preserves_start(self) -> None:
        """Test that truncation keeps the beginning of the text."""
        provider = MockAIProvider('{"summary": "", "concepts": [], "entities": []}')
        extractor = MetadataExtractor(provider)

        # Create text where we can verify the start is preserved
        long_text = "START_MARKER" + "x" * 20000 + "END_MARKER"

        await extractor.extract(long_text)

        user_message = provider.chat_calls[0]["messages"][0]["content"]
        assert "START_MARKER" in user_message
        assert "END_MARKER" not in user_message


class TestEmptyContent:
    """Tests for empty content handling."""

    @pytest.mark.asyncio
    async def test_empty_text(self) -> None:
        """Test handling of empty text."""
        provider = MockAIProvider('{"summary": "test", "concepts": [], "entities": []}')
        extractor = MetadataExtractor(provider)

        result = await extractor.extract("")

        assert result.summary == ""
        assert result.concepts == []
        assert result.entities == []
        # Should not have called the provider
        assert len(provider.chat_calls) == 0

    @pytest.mark.asyncio
    async def test_whitespace_only_text(self) -> None:
        """Test handling of whitespace-only text."""
        provider = MockAIProvider('{"summary": "test", "concepts": [], "entities": []}')
        extractor = MetadataExtractor(provider)

        result = await extractor.extract("   \n\t  ")

        assert result.summary == ""
        assert len(provider.chat_calls) == 0


class TestProviderErrors:
    """Tests for AI provider error handling."""

    @pytest.mark.asyncio
    async def test_wraps_provider_error(self) -> None:
        """Test that AIProviderError is wrapped in MetadataExtractionError."""
        provider = MockAIProvider(should_fail=True)
        extractor = MetadataExtractor(provider)

        with pytest.raises(MetadataExtractionError) as exc_info:
            await extractor.extract("Test content")

        # Verify error chaining
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, AIProviderError)

    @pytest.mark.asyncio
    async def test_error_includes_step(self) -> None:
        """Test that error includes the processing step."""
        provider = MockAIProvider(should_fail=True)
        extractor = MetadataExtractor(provider)

        with pytest.raises(MetadataExtractionError) as exc_info:
            await extractor.extract("Test content")

        assert exc_info.value.step == "metadata_extraction"


class TestSystemPrompt:
    """Tests for system prompt configuration."""

    @pytest.mark.asyncio
    async def test_uses_system_prompt(self) -> None:
        """Test that extraction uses the system prompt."""
        provider = MockAIProvider('{"summary": "", "concepts": [], "entities": []}')
        extractor = MetadataExtractor(provider)

        await extractor.extract("Test content")

        assert len(provider.chat_calls) == 1
        system = provider.chat_calls[0]["system"]
        assert system is not None
        assert "knowledge extraction" in system.lower()
        assert "JSON" in system
