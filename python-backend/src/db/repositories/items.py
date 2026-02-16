"""Repository for item database operations."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TypeAlias
from uuid import uuid4

import aiosqlite

from src.db import Item, ItemCreate, ItemMetadata, ItemUpdate, normalize_item_metadata
from src.db.repositories import BaseRepository
from src.exceptions import DatabaseError, ItemNotFoundError

ItemList: TypeAlias = list[Item]


class ItemRepository(BaseRepository[Item, ItemCreate, ItemUpdate]):
    """Repository for managing items in the database.

    Items are the main content units in Cortex - web pages, notes, files, etc.
    This repository handles all CRUD operations for items, with UUID generation
    happening internally on create.

    Stateless - db connection passed via method parameters.
    Methods do NOT commit - caller is responsible for transaction management.
    """

    @property
    def table_name(self) -> str:
        return "items"

    @staticmethod
    def _serialize_metadata(metadata: ItemMetadata | None) -> str | None:
        if metadata is None:
            return None

        return json.dumps(metadata.model_dump(exclude_none=True))

    def _row_to_item(self, row: aiosqlite.Row) -> Item:
        """Convert a database row to an Item model."""
        metadata = row["metadata"]
        if metadata is not None and isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = None

        metadata = normalize_item_metadata(metadata)

        return Item(
            id=row["id"],
            title=row["title"],
            content=row["content"],
            content_type=row["content_type"],
            source_url=row["source_url"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            processing_status=row["processing_status"],
            metadata=metadata,
        )

    async def create(self, db: aiosqlite.Connection, data: ItemCreate) -> Item:
        """Create a new item.

        UUID is generated using uuid4(). Initial processing_status is 'pending'.
        Does NOT commit - caller is responsible for committing.

        Args:
            db: Database connection
            data: The item data to create

        Returns:
            The created item with all fields populated
        """
        item_id = str(uuid4())
        now = datetime.now(UTC).isoformat()
        metadata_json = self._serialize_metadata(data.metadata)

        await db.execute(
            """
            INSERT INTO items (id, title, content, content_type, source_url,
                               created_at, updated_at, processing_status, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                item_id,
                data.title,
                data.content,
                data.content_type,
                data.source_url,
                now,
                now,
                "pending",
                metadata_json,
            ],
        )

        # Return the created item
        result = await self.get(db, item_id)
        if result is None:
            raise DatabaseError(f"Failed to retrieve newly created item: {item_id}")
        return result

    async def get(self, db: aiosqlite.Connection, id: str) -> Item | None:
        """Get an item by ID.

        Args:
            db: Database connection
            id: The item's unique identifier

        Returns:
            The item if found, None otherwise
        """
        cursor = await db.execute(
            "SELECT * FROM items WHERE id = ?",
            [id],
        )
        row = await cursor.fetchone()

        if row is None:
            return None

        return self._row_to_item(row)

    async def list(
        self, db: aiosqlite.Connection, offset: int = 0, limit: int = 20
    ) -> ItemList:
        """List items with pagination, ordered by created_at descending.

        Args:
            db: Database connection
            offset: Number of items to skip
            limit: Maximum number of items to return

        Returns:
            List of items
        """
        cursor = await db.execute(
            "SELECT * FROM items ORDER BY created_at DESC LIMIT ? OFFSET ?",
            [limit, offset],
        )
        rows = await cursor.fetchall()
        return [self._row_to_item(row) for row in rows]

    async def update(self, db: aiosqlite.Connection, id: str, data: ItemUpdate) -> Item:
        """Update an item.

        Only non-None fields in the update data are applied.
        The updated_at timestamp is automatically updated.
        Does NOT commit - caller is responsible for committing.

        Args:
            db: Database connection
            id: The item's unique identifier
            data: The fields to update

        Returns:
            The updated item

        Raises:
            ItemNotFoundError: If the item doesn't exist
        """
        # Check if item exists
        existing = await self.get(db, id)
        if existing is None:
            raise ItemNotFoundError(item_id=id)

        # Build update query with only non-None fields
        updates: list[str] = []
        values: list[str | None] = []

        if data.title is not None:
            updates.append("title = ?")
            values.append(data.title)

        if data.content is not None:
            updates.append("content = ?")
            values.append(data.content)

        if data.source_url is not None:
            updates.append("source_url = ?")
            values.append(data.source_url)

        if data.metadata is not None:
            updates.append("metadata = ?")
            values.append(self._serialize_metadata(data.metadata))

        # Always update updated_at
        now = datetime.now(UTC).isoformat()
        updates.append("updated_at = ?")
        values.append(now)

        if updates:
            values.append(id)
            await db.execute(
                f"UPDATE items SET {', '.join(updates)} WHERE id = ?",
                values,
            )

        result = await self.get(db, id)
        if result is None:
            raise DatabaseError(f"Failed to retrieve updated item: {id}")
        return result

    async def delete(self, db: aiosqlite.Connection, id: str) -> bool:
        """Delete an item.

        Does NOT commit - caller is responsible for committing.

        Args:
            db: Database connection
            id: The item's unique identifier

        Returns:
            True if deleted, False if item didn't exist
        """
        cursor = await db.execute(
            "DELETE FROM items WHERE id = ?",
            [id],
        )
        return cursor.rowcount > 0

    async def count(self, db: aiosqlite.Connection) -> int:
        """Count total items.

        Args:
            db: Database connection

        Returns:
            Total number of items
        """
        cursor = await db.execute("SELECT COUNT(*) FROM items")
        result = await cursor.fetchone()
        return result[0] if result else 0

    async def get_by_status(self, db: aiosqlite.Connection, status: str) -> ItemList:
        """Get items filtered by processing status.

        Args:
            db: Database connection
            status: The processing status to filter by
                   ('pending', 'processing', 'completed', 'failed')

        Returns:
            List of items with the given status
        """
        cursor = await db.execute(
            "SELECT * FROM items WHERE processing_status = ? ORDER BY created_at DESC",
            [status],
        )
        rows = await cursor.fetchall()
        return [self._row_to_item(row) for row in rows]

    async def update_status(
        self, db: aiosqlite.Connection, id: str, status: str
    ) -> None:
        """Update an item's processing status.

        Does NOT commit - caller is responsible for committing.

        Args:
            db: Database connection
            id: The item's unique identifier
            status: The new processing status

        Raises:
            ItemNotFoundError: If the item doesn't exist
        """
        existing = await self.get(db, id)
        if existing is None:
            raise ItemNotFoundError(item_id=id)

        now = datetime.now(UTC).isoformat()
        await db.execute(
            "UPDATE items SET processing_status = ?, updated_at = ? WHERE id = ?",
            [status, now, id],
        )
