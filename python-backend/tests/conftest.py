"""Shared fixtures for pytest tests."""

from pathlib import Path
from unittest.mock import patch

import aiosqlite
import pytest
from httpx import ASGITransport, AsyncClient
from src.db.database import _apply_schema, init_database
from src.main import app


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    return tmp_path / "test.db"


@pytest.fixture
async def db_connection(temp_db_path: Path):
    """Create a database connection with schema applied.

    Use this fixture for repository and database-level tests that need
    direct access to the database connection.
    """
    async with aiosqlite.connect(temp_db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        db.row_factory = aiosqlite.Row
        await _apply_schema(db)
        await db.commit()
        yield db


@pytest.fixture
async def client(temp_db_path: Path):
    """Create an async test client with temporary database.

    Use this fixture for API endpoint tests that need to make HTTP requests.
    The database is initialized and the app is configured to use the temporary
    database path.
    """
    with patch("src.config.settings.db_path", temp_db_path):
        await init_database()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
