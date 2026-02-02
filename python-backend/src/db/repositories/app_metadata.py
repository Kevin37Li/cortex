"""Repository for application metadata key-value storage."""

from __future__ import annotations

import aiosqlite


class AppMetadataRepository:
    """Repository for app-wide metadata key-value storage.

    Used for storing application settings that need to persist across sessions,
    such as the embedding model name to enforce consistency.

    Stateless - db connection passed via method parameters.
    Methods do NOT commit - caller is responsible for transaction management.
    """

    async def get(self, db: aiosqlite.Connection, key: str) -> str | None:
        """Get a metadata value by key.

        Args:
            db: Database connection
            key: The metadata key to retrieve

        Returns:
            The value if found, None otherwise
        """
        cursor = await db.execute("SELECT value FROM app_metadata WHERE key = ?", [key])
        row = await cursor.fetchone()
        return row["value"] if row else None

    async def set(self, db: aiosqlite.Connection, key: str, value: str) -> None:
        """Set a metadata key-value pair.

        Uses INSERT OR REPLACE to upsert the value.
        Does NOT commit - caller is responsible for committing.

        Args:
            db: Database connection
            key: The metadata key
            value: The value to store
        """
        await db.execute(
            "INSERT OR REPLACE INTO app_metadata (key, value) VALUES (?, ?)",
            [key, value],
        )
