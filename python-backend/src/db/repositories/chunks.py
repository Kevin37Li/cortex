"""Repository for chunk database operations."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import aiosqlite

from ..models import Chunk, ChunkCreate


class ChunkRepository:
    """Repository for managing chunks in the database.

    Chunks are semantic segments of content extracted from items for embedding
    and search. This repository focuses on batch operations since chunks are
    typically created and managed as groups belonging to an item.

    Unlike ItemRepository, this doesn't extend BaseRepository because chunks
    have a different access pattern (batch operations, parent-child relationship).
    """

    def __init__(self, db: aiosqlite.Connection) -> None:
        """Initialize the repository with a database connection.

        Args:
            db: An aiosqlite connection with row_factory set
        """
        self.db = db

    def _row_to_chunk(self, row: aiosqlite.Row) -> Chunk:
        """Convert a database row to a Chunk model."""
        return Chunk(
            id=row["id"],
            item_id=row["item_id"],
            chunk_index=row["chunk_index"],
            content=row["content"],
            token_count=row["token_count"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    async def create_many(self, chunks: list[ChunkCreate]) -> list[Chunk]:
        """Create multiple chunks in a batch operation.

        UUIDs are generated using uuid4() for each chunk.

        Args:
            chunks: List of chunk data to create

        Returns:
            List of created chunks with all fields populated
        """
        if not chunks:
            return []

        now = datetime.now(UTC).isoformat()
        created_chunks: list[Chunk] = []

        for chunk_data in chunks:
            chunk_id = str(uuid4())

            await self.db.execute(
                """
                INSERT INTO chunks (id, item_id, chunk_index, content, token_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    chunk_id,
                    chunk_data.item_id,
                    chunk_data.chunk_index,
                    chunk_data.content,
                    chunk_data.token_count,
                    now,
                ],
            )

            created_chunks.append(
                Chunk(
                    id=chunk_id,
                    item_id=chunk_data.item_id,
                    chunk_index=chunk_data.chunk_index,
                    content=chunk_data.content,
                    token_count=chunk_data.token_count,
                    created_at=datetime.fromisoformat(now),
                )
            )

        await self.db.commit()
        return created_chunks

    async def get_by_item(self, item_id: str) -> list[Chunk]:
        """Get all chunks for a specific item, ordered by chunk_index.

        Args:
            item_id: The parent item's unique identifier

        Returns:
            List of chunks belonging to the item, in order
        """
        cursor = await self.db.execute(
            "SELECT * FROM chunks WHERE item_id = ? ORDER BY chunk_index",
            [item_id],
        )
        rows = await cursor.fetchall()
        return [self._row_to_chunk(row) for row in rows]

    async def delete_by_item(self, item_id: str) -> int:
        """Delete all chunks for a specific item.

        Args:
            item_id: The parent item's unique identifier

        Returns:
            Number of chunks deleted
        """
        cursor = await self.db.execute(
            "DELETE FROM chunks WHERE item_id = ?",
            [item_id],
        )
        await self.db.commit()
        return cursor.rowcount

    async def count_by_item(self, item_id: str) -> int:
        """Count chunks for a specific item.

        Args:
            item_id: The parent item's unique identifier

        Returns:
            Number of chunks belonging to the item
        """
        cursor = await self.db.execute(
            "SELECT COUNT(*) FROM chunks WHERE item_id = ?",
            [item_id],
        )
        result = await cursor.fetchone()
        return result[0] if result else 0
