"""Dependency injection helpers for API routes."""

from collections.abc import AsyncIterator

import aiosqlite
from fastapi import Depends

from ..db.database import db_connection
from ..db.repositories import (
    ChunkRepository,
    ItemRepository,
    chunk_repo,
    item_repo,
)
from ..providers import AIProvider, OllamaProvider
from ..services.embeddings import EmbeddingService


async def get_db_connection() -> AsyncIterator[aiosqlite.Connection]:
    """Async generator for FastAPI Depends().

    Yields:
        Database connection with foreign keys enabled and sqlite-vec loaded
    """
    async with db_connection() as db:
        yield db


def get_item_repo() -> ItemRepository:
    """Get the ItemRepository singleton for FastAPI dependency injection.

    Returns:
        ItemRepository instance for item data access
    """
    return item_repo


def get_chunk_repo() -> ChunkRepository:
    """Get the ChunkRepository singleton for FastAPI dependency injection.

    Returns:
        ChunkRepository instance for chunk data access
    """
    return chunk_repo


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
