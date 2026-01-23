# Task: Write Tests for Repository Patterns and CRUD Endpoints

## Summary

Create comprehensive test coverage for the repository layer and items CRUD API endpoints.

## Acceptance Criteria

- [x] Unit tests for `ItemRepository` CRUD operations
- [x] Unit tests for `ChunkRepository` operations
- [x] Integration tests for all `/api/items` endpoints
- [x] Tests for error cases (not found, validation errors)
- [x] Tests for pagination behavior
- [x] All tests pass with in-memory SQLite
- [x] Coverage > 80% for tested modules

## Dependencies

- Task 3: Repository pattern implementation
- Task 4: Items CRUD endpoints
- Task 7: Pytest infrastructure

## Technical Notes

- Follow patterns in `docs/developer/quality-tooling/testing.md`
- Test both success and error paths
- Use fixtures for database and test client
- Mock external dependencies if needed

## Implementation

### Repository Tests (`tests/test_repositories.py`)

Class-based async tests following the established pattern:

```python
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
        assert item.title == "Test Item"
        assert item.processing_status == "pending"

    async def test_get_item_not_found(self, db_connection: aiosqlite.Connection):
        """Test getting a non-existent item returns None."""
        repo = ItemRepository(db_connection)
        result = await repo.get("nonexistent-id")
        assert result is None

    # ... 16 total tests covering all CRUD operations
```

Coverage: 16 tests for `ItemRepository`, 8 tests for `ChunkRepository`

### Endpoint Tests (`tests/test_api_items.py`)

Class-based async tests using `AsyncClient`:

```python
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
        assert "id" in data

    async def test_create_item_validation_error(self, client: AsyncClient):
        """Test creating an item with missing required fields returns 422."""
        response = await client.post("/api/items/", json={"title": "Test Item"})
        assert response.status_code == 422
```

Coverage: 13 tests covering all CRUD endpoints with error cases

## Files Created

```
python-backend/tests/
├── __init__.py
├── conftest.py           # Shared fixtures (db_connection, client, temp_db_path)
├── test_repositories.py  # Repository unit tests (24 tests)
└── test_api_items.py     # API endpoint tests (13 tests)
```

## Verification

```bash
cd python-backend

# Run all tests
uv run pytest -v

# Run with coverage report
uv run pytest --cov=src --cov-report=term-missing

# Check coverage threshold
uv run pytest --cov=src --cov-fail-under=80
```

## Results

- **89 tests passing** (includes other test files)
- **92% overall coverage** (exceeds 80% threshold)
- Key module coverage:
  - `src/db/repositories/items.py`: 92%
  - `src/db/repositories/chunks.py`: 100%
  - `src/api/items.py`: 100%
  - `src/db/models.py`: 100%
