# Task: Implement Repository Pattern for Database Access

## Summary

Create repository classes that encapsulate all database operations, providing a clean abstraction layer between the API and database.

## Acceptance Criteria

- [ ] Base repository class with common CRUD operations
- [ ] `ItemRepository` with item-specific operations
- [ ] `ChunkRepository` for chunk management
- [ ] Async database operations using `aiosqlite`
- [ ] Proper error handling with custom exceptions
- [ ] Type hints with Pydantic models for input/output

## Dependencies

- Task 1: Python backend project structure
- Task 2: SQLite schema setup

## Technical Notes

- Follow patterns in `docs/developer/python-backend/architecture.md`
- Use dependency injection for database connections
- Repositories should not contain business logic - just data access
- Return Pydantic models, not raw dictionaries

## Repository Methods

```python
# ItemRepository
class ItemRepository:
    async def create(self, item: ItemCreate) -> Item
    async def get(self, id: str) -> Item | None
    async def list(self, offset: int, limit: int) -> list[Item]
    async def update(self, id: str, item: ItemUpdate) -> Item
    async def delete(self, id: str) -> bool
    async def get_by_status(self, status: str) -> list[Item]
    async def update_status(self, id: str, status: str) -> None

# ChunkRepository
class ChunkRepository:
    async def create_many(self, chunks: list[ChunkCreate]) -> list[Chunk]
    async def get_by_item(self, item_id: str) -> list[Chunk]
    async def delete_by_item(self, item_id: str) -> int
```

## Files to Create

- `python-backend/src/db/repositories/base.py` - Base repository
- `python-backend/src/db/repositories/items.py` - ItemRepository
- `python-backend/src/db/repositories/chunks.py` - ChunkRepository
- `python-backend/src/db/models.py` - Pydantic models for Item, Chunk, etc.
- `python-backend/src/exceptions.py` - Custom exception hierarchy

## Verification

```python
# Should be able to perform CRUD operations
repo = ItemRepository(db)
item = await repo.create(ItemCreate(title="Test", content="Hello"))
assert item.id is not None
retrieved = await repo.get(item.id)
assert retrieved.title == "Test"
```
