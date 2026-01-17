# Task: Write Tests for Repository Patterns and CRUD Endpoints

## Summary

Create comprehensive test coverage for the repository layer and items CRUD API endpoints.

## Acceptance Criteria

- [ ] Unit tests for `ItemRepository` CRUD operations
- [ ] Unit tests for `ChunkRepository` operations
- [ ] Integration tests for all `/api/items` endpoints
- [ ] Tests for error cases (not found, validation errors)
- [ ] Tests for pagination behavior
- [ ] All tests pass with in-memory SQLite
- [ ] Coverage > 80% for tested modules

## Dependencies

- Task 3: Repository pattern implementation
- Task 4: Items CRUD endpoints
- Task 7: Pytest infrastructure

## Technical Notes

- Follow patterns in `docs/developer/quality-tooling/testing.md`
- Test both success and error paths
- Use fixtures for database and test client
- Mock external dependencies if needed

## Test Cases

### Repository Tests (`tests/unit/test_item_repository.py`)

```python
async def test_create_item(item_repo):
    item = await item_repo.create(ItemCreate(
        title="Test",
        content="Hello world",
        content_type="note"
    ))
    assert item.id is not None
    assert item.title == "Test"
    assert item.processing_status == "pending"

async def test_get_item_not_found(item_repo):
    result = await item_repo.get("nonexistent-id")
    assert result is None

async def test_list_items_pagination(item_repo):
    # Create 25 items
    for i in range(25):
        await item_repo.create(ItemCreate(...))

    # First page
    page1 = await item_repo.list(offset=0, limit=10)
    assert len(page1) == 10

    # Second page
    page2 = await item_repo.list(offset=10, limit=10)
    assert len(page2) == 10

async def test_update_item(item_repo):
    item = await item_repo.create(ItemCreate(...))
    updated = await item_repo.update(item.id, ItemUpdate(title="New Title"))
    assert updated.title == "New Title"

async def test_delete_item(item_repo):
    item = await item_repo.create(ItemCreate(...))
    result = await item_repo.delete(item.id)
    assert result is True
    assert await item_repo.get(item.id) is None
```

### Endpoint Tests (`tests/api/test_items.py`)

```python
def test_create_item(client):
    response = client.post("/api/items", json={
        "title": "Test",
        "content": "Hello",
        "content_type": "note"
    })
    assert response.status_code == 201
    assert response.json()["id"] is not None

def test_create_item_validation_error(client):
    response = client.post("/api/items", json={
        "title": "",  # Empty title should fail
        "content": "Hello"
    })
    assert response.status_code == 422

def test_get_item_not_found(client):
    response = client.get("/api/items/nonexistent-id")
    assert response.status_code == 404

def test_list_items_empty(client):
    response = client.get("/api/items")
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0
```

## Files to Create

```
python/tests/
├── unit/
│   ├── test_item_repository.py
│   └── test_chunk_repository.py
└── api/
    ├── __init__.py
    └── test_items.py
```

## Verification

```bash
cd python

# Run all tests
uv run pytest -v

# Run with coverage report
uv run pytest --cov=app --cov-report=html

# Check coverage threshold
uv run pytest --cov=app --cov-fail-under=80
```
