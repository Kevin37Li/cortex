"""Repository for item database operations."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import aiosqlite

from ...exceptions import DatabaseError, ItemNotFoundError
from ..models import Item, ItemCreate, ItemUpdate
from .base import BaseRepository


class ItemRepository(BaseRepository[Item, ItemCreate, ItemUpdate]):
    """Repository for managing items in the database.

    Items are the main content units in Cortex - web pages, notes, files, etc.
    This repository handles all CRUD operations for items, with UUID generation
    happening internally on create.
    """

    @property
    def table_name(self) -> str:
        return "items"

    def _row_to_item(self, row: aiosqlite.Row) -> Item:
        """Convert a database row to an Item model."""
        metadata = row["metadata"]
        if metadata is not None and isinstance(metadata, str):
            metadata = json.loads(metadata)

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

    async def create(self, data: ItemCreate) -> Item:
        """Create a new item.

        UUID is generated using uuid4(). Initial processing_status is 'pending'.

        Args:
            data: The item data to create

        Returns:
            The created item with all fields populated
        """
        item_id = str(uuid4())
        now = datetime.now(UTC).isoformat()
        metadata_json = json.dumps(data.metadata) if data.metadata else None

        await self.db.execute(
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
        await self.db.commit()

        # Return the created item
        result = await self.get(item_id)
        if result is None:
            raise DatabaseError(f"Failed to retrieve newly created item: {item_id}")
        return result

    async def get(self, id: str) -> Item | None:
        """Get an item by ID.

        Args:
            id: The item's unique identifier

        Returns:
            The item if found, None otherwise
        """
        cursor = await self.db.execute(
            "SELECT * FROM items WHERE id = ?",
            [id],
        )
        row = await cursor.fetchone()

        if row is None:
            return None

        return self._row_to_item(row)

    async def list(self, offset: int = 0, limit: int = 20) -> list[Item]:
        """List items with pagination, ordered by created_at descending.

        Args:
            offset: Number of items to skip
            limit: Maximum number of items to return

        Returns:
            List of items
        """
        cursor = await self.db.execute(
            "SELECT * FROM items ORDER BY created_at DESC LIMIT ? OFFSET ?",
            [limit, offset],
        )
        rows = await cursor.fetchall()
        return [self._row_to_item(row) for row in rows]

    async def update(self, id: str, data: ItemUpdate) -> Item:
        """Update an item.

        Only non-None fields in the update data are applied.
        The updated_at timestamp is automatically updated.

        Args:
            id: The item's unique identifier
            data: The fields to update

        Returns:
            The updated item

        Raises:
            ItemNotFoundError: If the item doesn't exist
        """
        # Check if item exists
        existing = await self.get(id)
        if existing is None:
            raise ItemNotFoundError(id)

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
            values.append(json.dumps(data.metadata))

        # Always update updated_at
        now = datetime.now(UTC).isoformat()
        updates.append("updated_at = ?")
        values.append(now)

        if updates:
            values.append(id)
            await self.db.execute(
                f"UPDATE items SET {', '.join(updates)} WHERE id = ?",
                values,
            )
            await self.db.commit()

        result = await self.get(id)
        if result is None:
            raise DatabaseError(f"Failed to retrieve updated item: {id}")
        return result

    async def delete(self, id: str) -> bool:
        """Delete an item.

        Args:
            id: The item's unique identifier

        Returns:
            True if deleted, False if item didn't exist
        """
        cursor = await self.db.execute(
            "DELETE FROM items WHERE id = ?",
            [id],
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def count(self) -> int:
        """Count total items.

        Returns:
            Total number of items
        """
        cursor = await self.db.execute("SELECT COUNT(*) FROM items")
        result = await cursor.fetchone()
        return result[0] if result else 0

    async def get_by_status(self, status: str) -> list[Item]:
        """Get items filtered by processing status.

        Args:
            status: The processing status to filter by
                   ('pending', 'processing', 'completed', 'failed')

        Returns:
            List of items with the given status
        """
        cursor = await self.db.execute(
            "SELECT * FROM items WHERE processing_status = ? ORDER BY created_at DESC",
            [status],
        )
        rows = await cursor.fetchall()
        return [self._row_to_item(row) for row in rows]

    async def update_status(self, id: str, status: str) -> None:
        """Update an item's processing status.

        Args:
            id: The item's unique identifier
            status: The new processing status

        Raises:
            ItemNotFoundError: If the item doesn't exist
        """
        existing = await self.get(id)
        if existing is None:
            raise ItemNotFoundError(id)

        now = datetime.now(UTC).isoformat()
        await self.db.execute(
            "UPDATE items SET processing_status = ?, updated_at = ? WHERE id = ?",
            [status, now, id],
        )
        await self.db.commit()
