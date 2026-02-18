"""Shared fixtures for pytest tests."""

from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
import pytest
import sqlite_vec
from httpx import ASGITransport, AsyncClient
from src.db.database import EMBEDDING_DIMENSION, _apply_schema, init_database
from src.db.models import Chunk
from src.main import app
from src.providers import OllamaProvider
from src.services.embeddings import EmbeddingService
from src.services.processing import ProcessingQueue
from src.services.search import SearchService

from tests.fakes.providers import MockAIProvider


# Database fixtures
@pytest.fixture(scope="function")
def temp_db_path(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    return tmp_path / "test.db"


@pytest.fixture(scope="function")
async def db_connection(temp_db_path: Path) -> AsyncIterator[aiosqlite.Connection]:
    """Create a database connection with schema applied."""
    async with aiosqlite.connect(temp_db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        db.row_factory = aiosqlite.Row
        await _apply_schema(db)
        await db.commit()
        yield db


@pytest.fixture(scope="function")
async def db_with_vec(temp_db_path: Path) -> AsyncIterator[aiosqlite.Connection]:
    """Create a database connection with sqlite-vec and schema applied."""
    async with aiosqlite.connect(temp_db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        db.row_factory = aiosqlite.Row

        await db.enable_load_extension(True)
        await db.execute("SELECT load_extension(?)", [sqlite_vec.loadable_path()])
        await db.enable_load_extension(False)
        await _apply_schema(db)

        await db.execute(
            f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
                chunk_id TEXT PRIMARY KEY,
                embedding FLOAT[{EMBEDDING_DIMENSION}]
            )
            """
        )

        await db.commit()
        yield db


@pytest.fixture(scope="function")
def mock_settings(temp_db_path: Path):
    """Mock DB settings with a temporary database path."""
    with patch("src.db.database.settings") as mock:
        mock.db_path = temp_db_path
        yield mock


# HTTP/client fixtures
@pytest.fixture(scope="function")
async def client(temp_db_path: Path) -> AsyncIterator[AsyncClient]:
    """Create an async test client with temporary database and queue mock."""
    with patch("src.config.settings.db_path", temp_db_path):
        await init_database()
        mock_queue = AsyncMock(spec=ProcessingQueue)
        app.state.processing_queue = mock_queue
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


# Provider fixtures
@pytest.fixture(scope="function")
def ollama_provider() -> OllamaProvider:
    """Create an OllamaProvider instance for provider tests."""
    return OllamaProvider(
        base_url="http://localhost:11434",
        embedding_model="nomic-embed-text",
        chat_model="llama3.2:3b",
        timeout=30.0,
        embed_timeout=60.0,
        availability_timeout=5.0,
    )


@pytest.fixture(scope="function")
def mock_ollama_provider() -> MagicMock:
    """Create a mock OllamaProvider for health endpoint tests."""
    provider_mock = MagicMock(spec=OllamaProvider)
    provider_mock.base_url = "http://localhost:11434"
    provider_mock.embedding_model = "nomic-embed-text"
    provider_mock.chat_model = "llama3.2:3b"
    return provider_mock


@pytest.fixture(scope="function")
def mock_provider() -> MockAIProvider:
    """Create a mock AI provider for embedding service tests."""
    return MockAIProvider()


@pytest.fixture(scope="function")
def embedding_service(mock_provider: MockAIProvider) -> EmbeddingService:
    """Create an EmbeddingService with mock provider."""
    return EmbeddingService(provider=mock_provider, model_name="test-model")


@pytest.fixture(scope="function")
def search_service(embedding_service: EmbeddingService) -> SearchService:
    """Create a SearchService with mock embedding service."""
    return SearchService(embedding_service=embedding_service)


# Test data fixtures
@pytest.fixture(scope="function")
def sample_chunks() -> list[Chunk]:
    """Create sample chunks for tests."""
    now = datetime.now()
    return [
        Chunk(
            id=f"chunk-{i}",
            item_id="item-1",
            chunk_index=i,
            content=f"This is chunk number {i} with some content.",
            token_count=10,
            created_at=now,
        )
        for i in range(5)
    ]
