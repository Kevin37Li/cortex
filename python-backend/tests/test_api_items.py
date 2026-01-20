"""Tests for items API endpoints."""

from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from src.db.database import init_database
from src.main import app


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    return tmp_path / "test.db"


@pytest.fixture
async def client(temp_db_path: Path):
    """Create a test client with temporary database."""
    with patch("src.config.settings.db_path", temp_db_path):
        # Initialize database
        await init_database()
        # Create async client
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


class TestCreateItem:
    """Test POST /api/items/ endpoint."""

    async def test_create_item_success(self, client: AsyncClient):
        """Test creating an item returns 201 and the item data."""
        response = await client.post(
            "/api/items/",
            json={
                "title": "Test Item",
                "content": "Test content",
                "content_type": "note",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Item"
        assert data["content"] == "Test content"
        assert data["content_type"] == "note"
        assert data["processing_status"] == "pending"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_item_with_optional_fields(self, client: AsyncClient):
        """Test creating an item with all fields."""
        response = await client.post(
            "/api/items/",
            json={
                "title": "Test Item",
                "content": "Test content",
                "content_type": "webpage",
                "source_url": "https://example.com",
                "metadata": {"key": "value"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["source_url"] == "https://example.com"
        assert data["metadata"] == {"key": "value"}

    async def test_create_item_validation_error(self, client: AsyncClient):
        """Test creating an item with missing required fields returns 422."""
        response = await client.post(
            "/api/items/",
            json={
                "title": "Test Item",
                # missing content and content_type
            },
        )

        assert response.status_code == 422


class TestListItems:
    """Test GET /api/items/ endpoint."""

    async def test_list_items_empty(self, client: AsyncClient):
        """Test listing items when none exist."""
        response = await client.get("/api/items/")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["offset"] == 0
        assert data["limit"] == 20

    async def test_list_items_with_data(self, client: AsyncClient):
        """Test listing items returns created items."""
        # Create some items
        for i in range(3):
            await client.post(
                "/api/items/",
                json={
                    "title": f"Item {i}",
                    "content": f"Content {i}",
                    "content_type": "note",
                },
            )

        response = await client.get("/api/items/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 3

    async def test_list_items_pagination(self, client: AsyncClient):
        """Test pagination works correctly."""
        # Create 5 items
        for i in range(5):
            await client.post(
                "/api/items/",
                json={
                    "title": f"Item {i}",
                    "content": f"Content {i}",
                    "content_type": "note",
                },
            )

        # Get first page
        response = await client.get("/api/items/", params={"offset": 0, "limit": 2})
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["offset"] == 0
        assert data["limit"] == 2

        # Get second page
        response = await client.get("/api/items/", params={"offset": 2, "limit": 2})
        data = response.json()
        assert len(data["items"]) == 2
        assert data["offset"] == 2

    async def test_list_items_pagination_validation(self, client: AsyncClient):
        """Test pagination parameter validation."""
        # Negative offset
        response = await client.get("/api/items/", params={"offset": -1})
        assert response.status_code == 422

        # Limit too high
        response = await client.get("/api/items/", params={"limit": 101})
        assert response.status_code == 422

        # Limit too low
        response = await client.get("/api/items/", params={"limit": 0})
        assert response.status_code == 422


class TestGetItem:
    """Test GET /api/items/{id} endpoint."""

    async def test_get_item_success(self, client: AsyncClient):
        """Test getting an existing item."""
        # Create an item
        create_response = await client.post(
            "/api/items/",
            json={
                "title": "Test Item",
                "content": "Test content",
                "content_type": "note",
            },
        )
        item_id = create_response.json()["id"]

        # Get the item
        response = await client.get(f"/api/items/{item_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == item_id
        assert data["title"] == "Test Item"

    async def test_get_item_not_found(self, client: AsyncClient):
        """Test getting a non-existent item returns 404."""
        response = await client.get("/api/items/nonexistent-id")

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "item_not_found"


class TestUpdateItem:
    """Test PUT /api/items/{id} endpoint."""

    async def test_update_item_success(self, client: AsyncClient):
        """Test updating an existing item."""
        # Create an item
        create_response = await client.post(
            "/api/items/",
            json={
                "title": "Original Title",
                "content": "Original content",
                "content_type": "note",
            },
        )
        item_id = create_response.json()["id"]

        # Update the item
        response = await client.put(
            f"/api/items/{item_id}",
            json={"title": "Updated Title"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["content"] == "Original content"

    async def test_update_item_not_found(self, client: AsyncClient):
        """Test updating a non-existent item returns 404."""
        response = await client.put(
            "/api/items/nonexistent-id",
            json={"title": "New Title"},
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "item_not_found"


class TestDeleteItem:
    """Test DELETE /api/items/{id} endpoint."""

    async def test_delete_item_success(self, client: AsyncClient):
        """Test deleting an existing item."""
        # Create an item
        create_response = await client.post(
            "/api/items/",
            json={
                "title": "Test Item",
                "content": "Test content",
                "content_type": "note",
            },
        )
        item_id = create_response.json()["id"]

        # Delete the item
        response = await client.delete(f"/api/items/{item_id}")

        assert response.status_code == 204

        # Verify it's deleted
        get_response = await client.get(f"/api/items/{item_id}")
        assert get_response.status_code == 404

    async def test_delete_item_not_found(self, client: AsyncClient):
        """Test deleting a non-existent item returns 404."""
        response = await client.delete("/api/items/nonexistent-id")

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "item_not_found"
