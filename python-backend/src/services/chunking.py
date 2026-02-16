"""Semantic chunking service for splitting text into embeddable chunks."""

import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import settings
from src.db import ChunkResult
from src.exceptions import ChunkingError

logger = logging.getLogger(__name__)


class ChunkingService:
    """Service for splitting text into semantic chunks suitable for embedding.

    Uses RecursiveCharacterTextSplitter to respect document structure while
    targeting configurable chunk sizes with overlap for context continuity.
    """

    def __init__(self) -> None:
        """Initialize the chunking service with configured splitter."""
        # Approximate: 1 token ≈ 4 characters
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size * 4,  # Convert tokens to chars
            chunk_overlap=settings.chunk_overlap * 4,
            separators=["\n\n", "\n", ". ", " "],
            length_function=len,
        )

    def chunk_text(self, text: str) -> list[ChunkResult]:
        """Split text into semantic chunks.

        Args:
            text: The text content to split into chunks.

        Returns:
            List of ChunkResult objects. Empty list if input is empty/whitespace.

        Raises:
            ChunkingError: If the text splitter fails unexpectedly.
        """
        if not text or not text.strip():
            return []

        try:
            chunks = self._splitter.split_text(text)
            logger.debug(f"Split text into {len(chunks)} chunks")

            return [
                ChunkResult(
                    content=chunk,
                    chunk_index=i,
                    token_count=self._estimate_tokens(chunk),
                )
                for i, chunk in enumerate(chunks)
            ]
        except Exception as e:
            logger.exception("Failed to chunk text")
            raise ChunkingError(
                message=f"Failed to split text into chunks: {e}",
            ) from e

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Approximate token count using word count heuristic.

        Note: This is an MVP approximation (word_count * 1.3). Actual tokenizer
        behavior varies by model and may need refinement based on usage.

        Args:
            text: The text to estimate token count for.

        Returns:
            Estimated token count.
        """
        return int(len(text.split()) * 1.3)
