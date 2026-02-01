"""Dependency injection helpers for API routes."""

from collections.abc import AsyncIterator

import aiosqlite
from fastapi import Depends

from ..db.database import get_connection
from ..db.repositories import ItemRepository
from ..providers import AIProvider, OllamaProvider
from ..services.embeddings import EmbeddingService


async def get_db_connection() -> AsyncIterator[aiosqlite.Connection]:
    """Get a database connection with sqlite-vec loaded.

    Yields:
        Database connection with foreign keys enabled and sqlite-vec loaded
    """
    async for db in get_connection():
        yield db


async def get_item_repository() -> AsyncIterator[ItemRepository]:
    """Get an ItemRepository instance with a database connection.

    Yields:
        ItemRepository connected to the database
    """
    async for db in get_connection():
        yield ItemRepository(db)


async def get_ollama_provider() -> AsyncIterator[OllamaProvider]:
    """Get an OllamaProvider instance configured from settings.

    Yields:
        OllamaProvider configured with settings values (defaults from config)
    """
    yield OllamaProvider()


async def get_ai_provider() -> AsyncIterator[AIProvider]:
    """Get the configured AI provider.

    For MVP, returns OllamaProvider. Later can switch based on settings.

    Yields:
        AIProvider instance configured from settings
    """
    yield OllamaProvider()


async def get_embedding_service(
    provider: AIProvider = Depends(get_ai_provider),
) -> AsyncIterator[EmbeddingService]:
    """Get embedding service with injected provider.

    Yields:
        EmbeddingService with configured AI provider
    """
    yield EmbeddingService(provider=provider)
