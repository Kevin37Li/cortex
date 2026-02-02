"""Embedding management service for generating and storing vector embeddings."""

import logging

import aiosqlite
import sqlite_vec

from src.config import settings
from src.db.database import EMBEDDING_DIMENSION
from src.db.models import Chunk
from src.db.repositories import metadata_repo
from src.exceptions import (
    AIProviderError,
    EmbeddingError,
    EmbeddingModelMismatchError,
)
from src.providers import AIProvider

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_KEY = "embedding_model"
DEFAULT_BATCH_SIZE = 32


class EmbeddingService:
    """Service for generating and storing vector embeddings.

    Bridges the AI provider layer and the database layer to:
    - Generate embeddings for text chunks
    - Store embeddings in sqlite-vec
    - Enforce model consistency (prevent mixed embeddings)
    - Track embedding metadata

    Note: Methods do NOT commit - caller is responsible for transaction management.
    """

    def __init__(
        self,
        provider: AIProvider,
        model_name: str | None = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        """Initialize the embedding service.

        Args:
            provider: AI provider for generating embeddings
            model_name: Embedding model name (defaults to settings.embedding_model)
            batch_size: Number of chunks to embed per batch (default 32)
        """
        self._provider = provider
        self._model_name = model_name or settings.embedding_model
        self._batch_size = batch_size

    async def embed_chunks(self, db: aiosqlite.Connection, chunks: list[Chunk]) -> None:
        """Generate embeddings for chunks and store in vec_chunks.

        Chunks must already be persisted in the database with IDs.
        Embeddings are generated in batches and stored in the vec_chunks
        virtual table.

        Does NOT commit - caller is responsible for committing.

        Args:
            db: Database connection with sqlite-vec loaded
            chunks: List of Chunk objects (must have IDs from database)

        Raises:
            EmbeddingModelMismatchError: If configured model differs from stored model
            EmbeddingError: If embedding generation or storage fails
        """
        if not chunks:
            logger.debug("No chunks to embed")
            return

        # Check model consistency before generating any embeddings
        # Returns True if this is first use and model needs to be recorded
        should_record_model = await self._check_model_consistency(db)

        logger.debug(f"Embedding {len(chunks)} chunks in batches of {self._batch_size}")

        try:
            # Process chunks in batches
            for i in range(0, len(chunks), self._batch_size):
                batch = chunks[i : i + self._batch_size]
                texts = [chunk.content for chunk in batch]

                logger.debug(
                    f"Processing batch {i // self._batch_size + 1}: {len(batch)} chunks"
                )

                # Generate embeddings via provider
                embeddings = await self._provider.embed_batch(texts)

                # Validate dimensions
                for embedding in embeddings:
                    self._validate_dimensions(embedding)

                # Store embeddings in vec_chunks
                for chunk, embedding in zip(batch, embeddings, strict=True):
                    serialized = sqlite_vec.serialize_float32(embedding)
                    await db.execute(
                        "INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)",
                        [chunk.id, serialized],
                    )

            # Record model only after embeddings are successfully stored
            # This ensures we don't record a model if embedding fails
            if should_record_model:
                logger.debug(f"Recording embedding model: {self._model_name}")
                await metadata_repo.set(db, EMBEDDING_MODEL_KEY, self._model_name)

            logger.debug(f"Successfully embedded and stored {len(chunks)} chunks")

        except AIProviderError as e:
            logger.error(f"AI provider error during embedding: {e}")
            raise EmbeddingError(
                f"Failed to generate embeddings: {e}",
                step="embed_chunks",
            ) from e
        except Exception as e:
            if isinstance(e, (EmbeddingError, EmbeddingModelMismatchError)):
                raise
            logger.exception("Unexpected error during embedding")
            raise EmbeddingError(
                f"Unexpected error during embedding: {e}",
                step="embed_chunks",
            ) from e

    async def embed_query(
        self, query: str, db: aiosqlite.Connection | None = None
    ) -> list[float]:
        """Generate embedding for a search query.

        Args:
            query: The search query text
            db: Optional database connection for model consistency check.
                If provided, validates the configured model matches the stored model.

        Returns:
            Embedding vector as list of floats

        Raises:
            EmbeddingModelMismatchError: If configured model differs from stored model
            EmbeddingError: If embedding generation fails
        """
        if not query or not query.strip():
            raise EmbeddingError(
                "Cannot embed empty query",
                step="embed_query",
            )

        # Check model consistency if db connection provided
        if db is not None:
            await self._check_model_consistency(db)

        logger.debug(f"Generating query embedding ({len(query)} chars)")

        try:
            embedding = await self._provider.embed(query)
            self._validate_dimensions(embedding)
            return embedding

        except AIProviderError as e:
            logger.error(f"AI provider error during query embedding: {e}")
            raise EmbeddingError(
                f"Failed to generate query embedding: {e}",
                step="embed_query",
            ) from e
        except Exception as e:
            if isinstance(e, (EmbeddingError, EmbeddingModelMismatchError)):
                raise
            logger.exception("Unexpected error during query embedding")
            raise EmbeddingError(
                f"Unexpected error during query embedding: {e}",
                step="embed_query",
            ) from e

    async def _check_model_consistency(self, db: aiosqlite.Connection) -> bool:
        """Check if the configured model matches what's stored in DB.

        On first use, returns True to indicate the model should be recorded.
        On subsequent uses, verifies the configured model matches.

        Args:
            db: Database connection

        Returns:
            True if this is the first use and model should be recorded after
            successful embedding, False if model is already recorded and matches.

        Raises:
            EmbeddingModelMismatchError: If models don't match
        """
        stored_model = await metadata_repo.get(db, EMBEDDING_MODEL_KEY)

        if stored_model is None:
            # First time: caller should record model after successful embedding
            logger.debug(
                f"First use - will record model after success: {self._model_name}"
            )
            return True
        elif stored_model != self._model_name:
            raise EmbeddingModelMismatchError(
                f"Database uses '{stored_model}' but '{self._model_name}' is configured. "
                "Cannot mix embeddings from different models.",
                step="model_consistency_check",
            )
        return False

    def _validate_dimensions(self, embedding: list[float]) -> None:
        """Validate embedding dimensions match expected size.

        Args:
            embedding: Embedding vector to validate

        Raises:
            EmbeddingModelMismatchError: If dimensions don't match
        """
        if len(embedding) != EMBEDDING_DIMENSION:
            raise EmbeddingModelMismatchError(
                f"Embedding has {len(embedding)} dimensions but expected "
                f"{EMBEDDING_DIMENSION}. Model may have changed or be misconfigured.",
                step="dimension_validation",
            )
