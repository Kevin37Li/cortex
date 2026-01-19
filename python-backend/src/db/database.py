"""Database connection and initialization for Cortex backend."""

import logging
from collections.abc import AsyncIterator
from pathlib import Path

import aiosqlite
import sqlite_vec

from ..config import settings

logger = logging.getLogger(__name__)

# Embedding dimension based on model (nomic-embed-text uses 768)
EMBEDDING_DIMENSION = 768

# Path to schema file
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def _load_sqlite_vec(db: aiosqlite.Connection) -> None:
    """Load the sqlite-vec extension."""
    await db.enable_load_extension(True)
    await db.execute("SELECT load_extension(?)", [sqlite_vec.loadable_path()])
    await db.enable_load_extension(False)


async def _create_vec_table(db: aiosqlite.Connection) -> None:
    """Create the vector embeddings table using sqlite-vec.

    This must be done after loading the extension and cannot be in schema.sql
    because the vec0 virtual table type is only available after loading sqlite-vec.
    """
    await db.execute(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
            chunk_id TEXT PRIMARY KEY,
            embedding FLOAT[{EMBEDDING_DIMENSION}]
        )
        """
    )


async def _apply_schema(db: aiosqlite.Connection) -> None:
    """Apply the database schema from schema.sql."""
    schema_sql = SCHEMA_PATH.read_text()
    await db.executescript(schema_sql)


async def init_database() -> None:
    """Initialize the database with schema and extensions.

    Creates the database directory if it doesn't exist,
    loads sqlite-vec extension, and applies the schema.
    """
    db_path = settings.db_path

    # Ensure the database directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Initializing database at {db_path}")

    async with aiosqlite.connect(db_path) as db:
        # Enable foreign keys
        await db.execute("PRAGMA foreign_keys = ON")

        # Load sqlite-vec extension
        await _load_sqlite_vec(db)

        # Verify sqlite-vec is working
        cursor = await db.execute("SELECT vec_version()")
        version = await cursor.fetchone()
        logger.info(f"sqlite-vec version: {version[0] if version else 'unknown'}")

        # Apply schema (tables, FTS, triggers, indexes)
        await _apply_schema(db)

        # Create vector table (must be after loading extension)
        await _create_vec_table(db)

        await db.commit()

    logger.info("Database initialization complete")


async def get_connection() -> AsyncIterator[aiosqlite.Connection]:
    """Get a database connection with sqlite-vec loaded.

    Yields an async database connection configured with:
    - Foreign keys enabled
    - sqlite-vec extension loaded
    - Row factory for dict-like access

    Usage:
        async for db in get_connection():
            await db.execute(...)
    """
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await _load_sqlite_vec(db)
        db.row_factory = aiosqlite.Row
        yield db


async def verify_database() -> dict:
    """Verify database is properly initialized and return status info.

    Returns a dict with:
    - sqlite_version: SQLite version string
    - vec_version: sqlite-vec version string
    - tables: list of table names
    - item_count: number of items
    - chunk_count: number of chunks

    Raises:
        FileNotFoundError: If the database file doesn't exist. Run init_database() first.
    """
    db_path = settings.db_path
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found at {db_path}. Run init_database() to initialize."
        )

    async with aiosqlite.connect(db_path) as db:
        await _load_sqlite_vec(db)

        # Get SQLite version
        cursor = await db.execute("SELECT sqlite_version()")
        sqlite_version = (await cursor.fetchone())[0]

        # Get sqlite-vec version
        cursor = await db.execute("SELECT vec_version()")
        vec_version = (await cursor.fetchone())[0]

        # Get table names
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in await cursor.fetchall()]

        # Get counts (may be 0 if tables don't exist yet)
        try:
            cursor = await db.execute("SELECT COUNT(*) FROM items")
            item_count = (await cursor.fetchone())[0]
        except aiosqlite.OperationalError:
            item_count = 0

        try:
            cursor = await db.execute("SELECT COUNT(*) FROM chunks")
            chunk_count = (await cursor.fetchone())[0]
        except aiosqlite.OperationalError:
            chunk_count = 0

        return {
            "sqlite_version": sqlite_version,
            "vec_version": vec_version,
            "tables": tables,
            "item_count": item_count,
            "chunk_count": chunk_count,
        }
