"""Tests for database initialization and schema."""

from pathlib import Path
from unittest.mock import patch

import aiosqlite
import pytest
import sqlite_vec
from src.db.database import (
    EMBEDDING_DIMENSION,
    _apply_schema,
    _create_vec_table,
    _load_sqlite_vec,
    init_database,
    verify_database,
)


@pytest.fixture
def mock_settings(temp_db_path: Path):
    """Mock settings with temporary database path."""
    with patch("src.db.database.settings") as mock:
        mock.db_path = temp_db_path
        yield mock


class TestSqliteVecLoading:
    """Test sqlite-vec extension loading."""

    async def test_load_sqlite_vec(self, temp_db_path: Path):
        """Test that sqlite-vec extension loads correctly."""
        async with aiosqlite.connect(temp_db_path) as db:
            await _load_sqlite_vec(db)

            # Verify extension is loaded by calling vec_version
            cursor = await db.execute("SELECT vec_version()")
            result = await cursor.fetchone()
            assert result is not None
            assert result[0] is not None

    async def test_vec_operations_work(self, temp_db_path: Path):
        """Test that vector operations work after loading extension."""
        async with aiosqlite.connect(temp_db_path) as db:
            await _load_sqlite_vec(db)

            # Create a simple vector table
            await db.execute(
                "CREATE VIRTUAL TABLE test_vec USING vec0(id TEXT PRIMARY KEY, vec FLOAT[3])"
            )

            # Insert a vector
            await db.execute(
                "INSERT INTO test_vec(id, vec) VALUES (?, ?)",
                ["test1", sqlite_vec.serialize_float32([1.0, 2.0, 3.0])],
            )

            # Query the vector
            cursor = await db.execute("SELECT * FROM test_vec WHERE id = ?", ["test1"])
            result = await cursor.fetchone()
            assert result is not None
            assert result[0] == "test1"


class TestSchemaCreation:
    """Test schema creation."""

    async def test_apply_schema_creates_tables(self, temp_db_path: Path):
        """Test that schema creates all expected tables."""
        async with aiosqlite.connect(temp_db_path) as db:
            await _apply_schema(db)
            await db.commit()

            # Check tables exist
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in await cursor.fetchall()]

            assert "items" in tables
            assert "chunks" in tables
            assert "chunks_fts" in tables

    async def test_items_table_structure(self, temp_db_path: Path):
        """Test items table has correct columns."""
        async with aiosqlite.connect(temp_db_path) as db:
            await _apply_schema(db)
            await db.commit()

            cursor = await db.execute("PRAGMA table_info(items)")
            columns = {row[1]: row[2] for row in await cursor.fetchall()}

            assert "id" in columns
            assert "title" in columns
            assert "content" in columns
            assert "content_type" in columns
            assert "source_url" in columns
            assert "created_at" in columns
            assert "updated_at" in columns
            assert "processing_status" in columns
            assert "metadata" in columns

    async def test_chunks_table_structure(self, temp_db_path: Path):
        """Test chunks table has correct columns."""
        async with aiosqlite.connect(temp_db_path) as db:
            await _apply_schema(db)
            await db.commit()

            cursor = await db.execute("PRAGMA table_info(chunks)")
            columns = {row[1]: row[2] for row in await cursor.fetchall()}

            assert "id" in columns
            assert "item_id" in columns
            assert "content" in columns
            assert "chunk_index" in columns
            assert "token_count" in columns
            assert "created_at" in columns

    async def test_indexes_created(self, temp_db_path: Path):
        """Test that indexes are created."""
        async with aiosqlite.connect(temp_db_path) as db:
            await _apply_schema(db)
            await db.commit()

            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
            )
            indexes = [row[0] for row in await cursor.fetchall()]

            assert "idx_items_status" in indexes
            assert "idx_items_created" in indexes
            assert "idx_items_content_type" in indexes
            assert "idx_chunks_item" in indexes
            assert "idx_chunks_item_index" in indexes


class TestVecChunksTable:
    """Test vector embeddings table."""

    async def test_create_vec_chunks_table(self, temp_db_path: Path):
        """Test that vec_chunks table is created correctly."""
        async with aiosqlite.connect(temp_db_path) as db:
            await _load_sqlite_vec(db)
            await _create_vec_table(db)
            await db.commit()

            # Verify table exists
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='vec_chunks'"
            )
            result = await cursor.fetchone()
            assert result is not None

    async def test_vec_chunks_insert_and_query(self, temp_db_path: Path):
        """Test inserting and querying vectors in vec_chunks."""
        async with aiosqlite.connect(temp_db_path) as db:
            await _load_sqlite_vec(db)
            await _create_vec_table(db)

            # Create a test embedding (768 dimensions)
            test_embedding = [0.1] * EMBEDDING_DIMENSION

            # Insert
            await db.execute(
                "INSERT INTO vec_chunks(chunk_id, embedding) VALUES (?, ?)",
                ["chunk1", sqlite_vec.serialize_float32(test_embedding)],
            )
            await db.commit()

            # Query by ID
            cursor = await db.execute(
                "SELECT chunk_id FROM vec_chunks WHERE chunk_id = ?", ["chunk1"]
            )
            result = await cursor.fetchone()
            assert result is not None
            assert result[0] == "chunk1"


class TestFTSSync:
    """Test FTS sync triggers."""

    async def test_fts_sync_on_insert(self, temp_db_path: Path):
        """Test that FTS table syncs on chunk insert."""
        async with aiosqlite.connect(temp_db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await _apply_schema(db)

            # Insert an item first (for foreign key)
            await db.execute(
                "INSERT INTO items(id, title, content, content_type) VALUES (?, ?, ?, ?)",
                ["item1", "Test Item", "Test content", "note"],
            )

            # Insert a chunk
            await db.execute(
                "INSERT INTO chunks(id, item_id, content, chunk_index) VALUES (?, ?, ?, ?)",
                ["chunk1", "item1", "This is searchable text", 0],
            )
            await db.commit()

            # Search in FTS
            cursor = await db.execute(
                "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH 'searchable'"
            )
            result = await cursor.fetchone()
            assert result is not None

    async def test_fts_sync_on_delete(self, temp_db_path: Path):
        """Test that FTS table syncs on chunk delete."""
        async with aiosqlite.connect(temp_db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await _apply_schema(db)

            # Insert item and chunk
            await db.execute(
                "INSERT INTO items(id, title, content, content_type) VALUES (?, ?, ?, ?)",
                ["item1", "Test Item", "Test content", "note"],
            )
            await db.execute(
                "INSERT INTO chunks(id, item_id, content, chunk_index) VALUES (?, ?, ?, ?)",
                ["chunk1", "item1", "Unique searchable phrase", 0],
            )
            await db.commit()

            # Delete the chunk
            await db.execute("DELETE FROM chunks WHERE id = ?", ["chunk1"])
            await db.commit()

            # FTS should no longer find it
            cursor = await db.execute(
                "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH 'Unique'"
            )
            result = await cursor.fetchone()
            assert result is None


class TestDatabaseInitialization:
    """Test full database initialization."""

    async def test_init_database_creates_directory(
        self, mock_settings, temp_db_path: Path
    ):
        """Test that init_database creates the database directory and file."""
        # Use a nested path that doesn't exist yet
        nested_path = temp_db_path.parent / "nested" / "cortex.db"
        mock_settings.db_path = nested_path

        assert not nested_path.parent.exists()

        await init_database()

        assert nested_path.parent.exists()
        assert nested_path.exists()

    async def test_init_database_creates_all_tables(
        self, mock_settings, temp_db_path: Path
    ):
        """Test that init_database creates all tables."""
        await init_database()

        async with aiosqlite.connect(temp_db_path) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in await cursor.fetchall()]

            assert "items" in tables
            assert "chunks" in tables
            assert "chunks_fts" in tables
            assert "vec_chunks" in tables

    async def test_init_database_idempotent(self, mock_settings, temp_db_path: Path):
        """Test that init_database can be called multiple times safely."""
        await init_database()
        await init_database()  # Should not raise

        # Database should still be valid
        status = await verify_database()
        assert status["sqlite_version"] is not None


class TestVerifyDatabase:
    """Test database verification."""

    async def test_verify_database_raises_if_not_initialized(
        self, mock_settings, temp_db_path: Path
    ):
        """Test that verify_database raises FileNotFoundError if DB doesn't exist."""
        # Database file doesn't exist yet
        assert not temp_db_path.exists()

        with pytest.raises(FileNotFoundError) as exc_info:
            await verify_database()

        assert "init_database()" in str(exc_info.value)

    async def test_verify_database_returns_info(
        self, mock_settings, temp_db_path: Path
    ):
        """Test that verify_database returns expected info."""
        await init_database()
        status = await verify_database()

        assert "sqlite_version" in status
        assert "vec_version" in status
        assert "tables" in status
        assert "item_count" in status
        assert "chunk_count" in status

        assert status["item_count"] == 0
        assert status["chunk_count"] == 0
        assert "items" in status["tables"]
        assert "chunks" in status["tables"]
