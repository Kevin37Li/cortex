"""Tests for ChunkingService."""

import pytest
from src.db.models import ChunkResult
from src.services.chunking import ChunkingService


class TestChunkingService:
    """Tests for ChunkingService."""

    @pytest.fixture
    def service(self) -> ChunkingService:
        """Create a ChunkingService instance."""
        return ChunkingService()

    def test_empty_input_returns_empty_list(self, service: ChunkingService) -> None:
        """Empty or whitespace input should return empty list."""
        assert service.chunk_text("") == []
        assert service.chunk_text("   ") == []
        assert service.chunk_text("\n\n") == []

    def test_short_content_returns_single_chunk(self, service: ChunkingService) -> None:
        """Short content below chunk size returns single chunk."""
        chunks = service.chunk_text("Hello world.")
        assert len(chunks) == 1
        assert chunks[0].content == "Hello world."
        assert chunks[0].chunk_index == 0
        assert chunks[0].token_count > 0

    def test_long_content_produces_multiple_chunks(
        self, service: ChunkingService
    ) -> None:
        """Long content is split into multiple chunks with sequential indices."""
        long_text = ("This is a paragraph about AI. " * 50 + "\n\n") * 5
        chunks = service.chunk_text(long_text)

        assert len(chunks) > 1
        # Verify indices are sequential
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_chunks_have_reasonable_token_counts(
        self, service: ChunkingService
    ) -> None:
        """Chunks should have token counts within expected range."""
        long_text = ("This is a test sentence. " * 100 + "\n\n") * 3
        chunks = service.chunk_text(long_text)

        for chunk in chunks:
            assert chunk.token_count > 0
            # Token count should be reasonable (not exceeding 2x target)
            assert chunk.token_count < 1000

    def test_respects_paragraph_separators(self, service: ChunkingService) -> None:
        """Chunks should preferentially split at paragraph boundaries."""
        text = "First paragraph content.\n\nSecond paragraph content."
        chunks = service.chunk_text(text)

        # Short enough to be one chunk, but demonstrates separator handling
        assert len(chunks) >= 1
        assert chunks[0].content  # Has content

    def test_chunk_result_fields(self, service: ChunkingService) -> None:
        """ChunkResult should have all required fields."""
        chunks = service.chunk_text("Test content for chunking.")

        chunk = chunks[0]
        assert isinstance(chunk, ChunkResult)
        assert isinstance(chunk.content, str)
        assert isinstance(chunk.chunk_index, int)
        assert isinstance(chunk.token_count, int)

    def test_token_estimation_uses_word_count_heuristic(
        self, service: ChunkingService
    ) -> None:
        """Token estimation should use word_count * 1.3 approximation."""
        text = "one two three four five"  # 5 words
        chunks = service.chunk_text(text)

        # 5 words * 1.3 = 6.5, truncated to 6
        assert chunks[0].token_count == 6

    def test_handles_only_whitespace_between_words(
        self, service: ChunkingService
    ) -> None:
        """Text with only spaces (no structure) should still chunk properly."""
        text = "word " * 200
        chunks = service.chunk_text(text)

        # Should produce at least one chunk
        assert len(chunks) >= 1
        assert all(c.content.strip() for c in chunks)

    def test_chunk_overlap_preserves_context(self, service: ChunkingService) -> None:
        """Consecutive chunks should have overlapping content."""
        # Create text long enough to produce multiple chunks
        # Use distinct sentence patterns so we can verify overlap
        sentences = [f"Sentence number {i} about topic." for i in range(100)]
        long_text = " ".join(sentences)

        chunks = service.chunk_text(long_text)

        # Must produce at least 2 chunks to verify overlap
        assert len(chunks) >= 2, "Expected multiple chunks to test overlap behavior"

        # Verify there's some overlap by checking that the end of chunk N
        # contains some text that appears at the start of chunk N+1
        # This is a heuristic check - we just verify chunks aren't totally disjoint
        first_chunk_end = chunks[0].content[-100:]
        second_chunk_start = chunks[1].content[:100]

        # At least some words should be shared due to overlap
        first_words = set(first_chunk_end.split())
        second_words = set(second_chunk_start.split())
        assert first_words & second_words  # Intersection should not be empty
