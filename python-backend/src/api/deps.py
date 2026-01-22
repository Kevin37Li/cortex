"""Dependency injection helpers for API routes."""

from collections.abc import AsyncIterator

import aiosqlite

from ..db.database import get_connection
from ..db.repositories import ItemRepository
from ..providers import OllamaProvider


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
