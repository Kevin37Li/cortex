"""Tests for repository classes."""

import aiosqlite
import pytest
from src.db.models import ChunkCreate, ItemCreate, ItemUpdate
from src.db.repositories import ChunkRepository, ItemRepository
from src.exceptions import ItemNotFoundError


class TestItemRepository:
    """Test ItemRepository CRUD operations."""

    async def test_create_item(self, db_connection: aiosqlite.Connection):
        """Test creating an item generates UUID and returns correct data."""
        repo = ItemRepository(db_connection)

        item = await repo.create(
            ItemCreate(
                title="Test Item",
                content="Test content",
                content_type="note",
            )
        )

        assert item.id is not None
        assert len(item.id) == 36  # UUID format
        assert item.title == "Test Item"
        assert item.content == "Test content"
        assert item.content_type == "note"
        assert item.processing_status == "pending"
        assert item.source_url is None
        assert item.metadata is None
        assert item.created_at is not None
        assert item.updated_at is not None

    async def test_create_item_with_optional_fields(
        self, db_connection: aiosqlite.Connection
    ):
        """Test creating an item with all optional fields."""
        repo = ItemRepository(db_connection)

        item = await repo.create(
            ItemCreate(
                title="Test Item",
                content="Test content",
                content_type="webpage",
                source_url="https://example.com",
                metadata={"author": "Test Author", "tags": ["python", "testing"]},
            )
        )

        assert item.source_url == "https://example.com"
        assert item.metadata == {"author": "Test Author", "tags": ["python", "testing"]}

    async def test_get_item(self, db_connection: aiosqlite.Connection):
        """Test getting an item by ID."""
        repo = ItemRepository(db_connection)

        created = await repo.create(
            ItemCreate(
                title="Test Item",
                content="Test content",
                content_type="note",
            )
        )

        retrieved = await repo.get(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == "Test Item"

    async def test_get_item_not_found(self, db_connection: aiosqlite.Connection):
        """Test getting a non-existent item returns None."""
        repo = ItemRepository(db_connection)

        result = await repo.get("nonexistent-id")

        assert result is None

    async def test_list_items(self, db_connection: aiosqlite.Connection):
        """Test listing items with pagination."""
        repo = ItemRepository(db_connection)

        # Create 5 items
        for i in range(5):
            await repo.create(
                ItemCreate(
                    title=f"Item {i}",
                    content=f"Content {i}",
                    content_type="note",
                )
            )

        # List with default pagination
        items = await repo.list()
        assert len(items) == 5

        # List with limit
        items = await repo.list(limit=3)
        assert len(items) == 3

        # List with offset
        items = await repo.list(offset=3)
        assert len(items) == 2

    async def test_list_items_order(self, db_connection: aiosqlite.Connection):
        """Test that items are listed in descending order by created_at."""
        repo = ItemRepository(db_connection)

        # Create items
        item1 = await repo.create(
            ItemCreate(title="First", content="Content", content_type="note")
        )
        item2 = await repo.create(
            ItemCreate(title="Second", content="Content", content_type="note")
        )

        items = await repo.list()

        # Most recent should be first
        assert items[0].id == item2.id
        assert items[1].id == item1.id

    async def test_update_item(self, db_connection: aiosqlite.Connection):
        """Test updating an item."""
        repo = ItemRepository(db_connection)

        created = await repo.create(
            ItemCreate(
                title="Original Title",
                content="Original content",
                content_type="note",
            )
        )

        updated = await repo.update(
            created.id,
            ItemUpdate(title="Updated Title"),
        )

        assert updated.title == "Updated Title"
        assert updated.content == "Original content"  # Unchanged
        assert updated.updated_at > created.updated_at

    async def test_update_item_partial(self, db_connection: aiosqlite.Connection):
        """Test partial update only changes specified fields."""
        repo = ItemRepository(db_connection)

        created = await repo.create(
            ItemCreate(
                title="Title",
                content="Content",
                content_type="note",
                source_url="https://example.com",
            )
        )

        updated = await repo.update(
            created.id,
            ItemUpdate(content="New content"),
        )

        assert updated.title == "Title"  # Unchanged
        assert updated.content == "New content"  # Changed
        assert updated.source_url == "https://example.com"  # Unchanged

    async def test_update_item_not_found(self, db_connection: aiosqlite.Connection):
        """Test updating a non-existent item raises ItemNotFoundError."""
        repo = ItemRepository(db_connection)

        with pytest.raises(ItemNotFoundError) as exc_info:
            await repo.update("nonexistent-id", ItemUpdate(title="New Title"))

        assert exc_info.value.item_id == "nonexistent-id"

    async def test_delete_item(self, db_connection: aiosqlite.Connection):
        """Test deleting an item."""
        repo = ItemRepository(db_connection)

        created = await repo.create(
            ItemCreate(title="To Delete", content="Content", content_type="note")
        )

        result = await repo.delete(created.id)

        assert result is True
        assert await repo.get(created.id) is None

    async def test_delete_item_not_found(self, db_connection: aiosqlite.Connection):
        """Test deleting a non-existent item returns False."""
        repo = ItemRepository(db_connection)

        result = await repo.delete("nonexistent-id")

        assert result is False

    async def test_count_items(self, db_connection: aiosqlite.Connection):
        """Test counting items."""
        repo = ItemRepository(db_connection)

        assert await repo.count() == 0

        for i in range(3):
            await repo.create(
                ItemCreate(title=f"Item {i}", content="Content", content_type="note")
            )

        assert await repo.count() == 3

    async def test_get_by_status(self, db_connection: aiosqlite.Connection):
        """Test filtering items by processing status."""
        repo = ItemRepository(db_connection)

        # Create items with different statuses
        item1 = await repo.create(
            ItemCreate(title="Item 1", content="Content", content_type="note")
        )
        item2 = await repo.create(
            ItemCreate(title="Item 2", content="Content", content_type="note")
        )

        # Update one to completed
        await repo.update_status(item2.id, "completed")

        pending_items = await repo.get_by_status("pending")
        completed_items = await repo.get_by_status("completed")

        assert len(pending_items) == 1
        assert pending_items[0].id == item1.id
        assert len(completed_items) == 1
        assert completed_items[0].id == item2.id

    async def test_update_status(self, db_connection: aiosqlite.Connection):
        """Test updating item processing status."""
        repo = ItemRepository(db_connection)

        created = await repo.create(
            ItemCreate(title="Item", content="Content", content_type="note")
        )

        assert created.processing_status == "pending"

        await repo.update_status(created.id, "processing")
        item = await repo.get(created.id)
        assert item.processing_status == "processing"

        await repo.update_status(created.id, "completed")
        item = await repo.get(created.id)
        assert item.processing_status == "completed"

    async def test_update_status_not_found(self, db_connection: aiosqlite.Connection):
        """Test updating status of non-existent item raises ItemNotFoundError."""
        repo = ItemRepository(db_connection)

        with pytest.raises(ItemNotFoundError):
            await repo.update_status("nonexistent-id", "completed")


class TestChunkRepository:
    """Test ChunkRepository operations."""

    async def _create_test_item(self, db_connection: aiosqlite.Connection) -> str:
        """Helper to create a test item and return its ID."""
        item_repo = ItemRepository(db_connection)
        item = await item_repo.create(
            ItemCreate(title="Test Item", content="Test content", content_type="note")
        )
        return item.id

    async def test_create_many_chunks(self, db_connection: aiosqlite.Connection):
        """Test creating multiple chunks at once."""
        item_id = await self._create_test_item(db_connection)
        repo = ChunkRepository(db_connection)

        chunks_data = [
            ChunkCreate(
                item_id=item_id,
                chunk_index=0,
                content="First chunk",
                token_count=10,
            ),
            ChunkCreate(
                item_id=item_id,
                chunk_index=1,
                content="Second chunk",
                token_count=12,
            ),
            ChunkCreate(
                item_id=item_id,
                chunk_index=2,
                content="Third chunk",
            ),
        ]

        created = await repo.create_many(chunks_data)

        assert len(created) == 3
        assert all(chunk.id is not None for chunk in created)
        assert created[0].chunk_index == 0
        assert created[0].content == "First chunk"
        assert created[0].token_count == 10
        assert created[2].token_count is None

    async def test_create_many_empty_list(self, db_connection: aiosqlite.Connection):
        """Test creating chunks with empty list returns empty list."""
        repo = ChunkRepository(db_connection)

        result = await repo.create_many([])

        assert result == []

    async def test_get_by_item(self, db_connection: aiosqlite.Connection):
        """Test getting all chunks for an item."""
        item_id = await self._create_test_item(db_connection)
        repo = ChunkRepository(db_connection)

        # Create chunks
        await repo.create_many(
            [
                ChunkCreate(item_id=item_id, chunk_index=0, content="Chunk 0"),
                ChunkCreate(item_id=item_id, chunk_index=1, content="Chunk 1"),
                ChunkCreate(item_id=item_id, chunk_index=2, content="Chunk 2"),
            ]
        )

        chunks = await repo.get_by_item(item_id)

        assert len(chunks) == 3
        # Should be ordered by chunk_index
        assert chunks[0].chunk_index == 0
        assert chunks[1].chunk_index == 1
        assert chunks[2].chunk_index == 2

    async def test_get_by_item_no_chunks(self, db_connection: aiosqlite.Connection):
        """Test getting chunks for item with no chunks returns empty list."""
        item_id = await self._create_test_item(db_connection)
        repo = ChunkRepository(db_connection)

        chunks = await repo.get_by_item(item_id)

        assert chunks == []

    async def test_delete_by_item(self, db_connection: aiosqlite.Connection):
        """Test deleting all chunks for an item."""
        item_id = await self._create_test_item(db_connection)
        repo = ChunkRepository(db_connection)

        await repo.create_many(
            [
                ChunkCreate(item_id=item_id, chunk_index=0, content="Chunk 0"),
                ChunkCreate(item_id=item_id, chunk_index=1, content="Chunk 1"),
            ]
        )

        deleted = await repo.delete_by_item(item_id)

        assert deleted == 2
        assert await repo.get_by_item(item_id) == []

    async def test_delete_by_item_none_exist(self, db_connection: aiosqlite.Connection):
        """Test deleting chunks when none exist returns 0."""
        item_id = await self._create_test_item(db_connection)
        repo = ChunkRepository(db_connection)

        deleted = await repo.delete_by_item(item_id)

        assert deleted == 0

    async def test_count_by_item(self, db_connection: aiosqlite.Connection):
        """Test counting chunks for an item."""
        item_id = await self._create_test_item(db_connection)
        repo = ChunkRepository(db_connection)

        assert await repo.count_by_item(item_id) == 0

        await repo.create_many(
            [
                ChunkCreate(item_id=item_id, chunk_index=0, content="Chunk 0"),
                ChunkCreate(item_id=item_id, chunk_index=1, content="Chunk 1"),
                ChunkCreate(item_id=item_id, chunk_index=2, content="Chunk 2"),
            ]
        )

        assert await repo.count_by_item(item_id) == 3

    async def test_cascade_delete(self, db_connection: aiosqlite.Connection):
        """Test that deleting an item cascades to delete its chunks."""
        item_repo = ItemRepository(db_connection)
        chunk_repo = ChunkRepository(db_connection)

        # Create item and chunks
        item = await item_repo.create(
            ItemCreate(title="Item", content="Content", content_type="note")
        )
        await chunk_repo.create_many(
            [
                ChunkCreate(item_id=item.id, chunk_index=0, content="Chunk"),
            ]
        )

        assert await chunk_repo.count_by_item(item.id) == 1

        # Delete item
        await item_repo.delete(item.id)

        # Chunks should be deleted due to CASCADE
        assert await chunk_repo.count_by_item(item.id) == 0
