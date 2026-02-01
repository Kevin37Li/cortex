"""Repository for application metadata key-value storage."""

from __future__ import annotations

import aiosqlite


class AppMetadataRepository:
    """Repository for app-wide metadata key-value storage.

    Used for storing application settings that need to persist across sessions,
    such as the embedding model name to enforce consistency.
    """

    def __init__(self, db: aiosqlite.Connection) -> None:
        """Initialize the repository with a database connection.

        Args:
            db: An aiosqlite connection with row_factory set
        """
        self.db = db

    async def get(self, key: str) -> str | None:
        """Get a metadata value by key.

        Args:
            key: The metadata key to retrieve

        Returns:
            The value if found, None otherwise
        """
        cursor = await self.db.execute(
            "SELECT value FROM app_metadata WHERE key = ?", [key]
        )
        row = await cursor.fetchone()
        return row["value"] if row else None

    async def set(self, key: str, value: str) -> None:
        """Set a metadata key-value pair.

        Uses INSERT OR REPLACE to upsert the value.
        Note: Does not commit - caller is responsible for committing
        the transaction to allow atomic operations with other changes.

        Args:
            key: The metadata key
            value: The value to store
        """
        await self.db.execute(
            "INSERT OR REPLACE INTO app_metadata (key, value) VALUES (?, ?)",
            [key, value],
        )
