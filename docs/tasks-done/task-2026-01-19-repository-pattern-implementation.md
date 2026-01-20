# Task: Implement Repository Pattern for Database Access

## Summary

Create repository classes that encapsulate all database operations, providing a clean abstraction layer between the API and database.

## Acceptance Criteria

- [x] Base repository class with common CRUD operations (generic type interface)
- [x] `ItemRepository` with item-specific operations including `count()` for pagination
- [x] `ChunkRepository` for chunk management
- [x] Async database operations using `aiosqlite`
- [x] Proper error handling with custom exceptions
- [x] Type hints with Pydantic models for input/output
- [x] UUID generation using `uuid4()` in repository `create()` methods
- [x] Repository module exports via `__init__.py`

## Dependencies

- Task 1: Python backend project structure
- Task 2: SQLite schema setup

## Technical Notes

- Follow patterns in `docs/developer/python-backend/architecture.md`
- Use dependency injection for database connections
- Repositories should not contain business logic - just data access
- Return Pydantic models, not raw dictionaries
- Generate UUIDs using `uuid4()` in `create()` methods (not passed in)
- Exception handling strategy:
  - `get()` returns `None` if not found (caller decides to raise)
  - `update()` raises `ItemNotFoundError` if item doesn't exist
  - `delete()` returns `False` if item doesn't exist
- Vector embeddings: `vec_chunks` table operations will be added in a future task (AI processing pipeline)

## Repository Methods

```python
# BaseRepository - Generic interface for common operations
class BaseRepository[T, CreateT, UpdateT]:
    async def create(self, data: CreateT) -> T
    async def get(self, id: str) -> T | None
    async def list(self, offset: int = 0, limit: int = 20) -> list[T]
    async def update(self, id: str, data: UpdateT) -> T  # raises ItemNotFoundError
    async def delete(self, id: str) -> bool
    async def count(self) -> int

# ItemRepository extends BaseRepository[Item, ItemCreate, ItemUpdate]
class ItemRepository:
    async def create(self, item: ItemCreate) -> Item
    async def get(self, id: str) -> Item | None
    async def list(self, offset: int = 0, limit: int = 20) -> list[Item]
    async def update(self, id: str, item: ItemUpdate) -> Item
    async def delete(self, id: str) -> bool
    async def count(self) -> int  # Required for pagination in Task 4
    async def get_by_status(self, status: str) -> list[Item]
    async def update_status(self, id: str, status: str) -> None

# ChunkRepository
class ChunkRepository:
    async def create_many(self, chunks: list[ChunkCreate]) -> list[Chunk]
    async def get_by_item(self, item_id: str) -> list[Chunk]
    async def delete_by_item(self, item_id: str) -> int
    async def count_by_item(self, item_id: str) -> int
```

## Pydantic Models

```python
# Item models
class ItemCreate(BaseModel):
    title: str
    content: str
    content_type: str  # 'webpage', 'note', 'file'
    source_url: str | None = None
    metadata: dict | None = None

class ItemUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    source_url: str | None = None
    metadata: dict | None = None

class Item(BaseModel):
    id: str
    title: str
    content: str
    content_type: str
    source_url: str | None
    created_at: datetime
    updated_at: datetime
    processing_status: str  # 'pending', 'processing', 'completed', 'failed'
    metadata: dict | None

# Chunk models
class ChunkCreate(BaseModel):
    item_id: str
    chunk_index: int
    content: str
    token_count: int | None = None

class Chunk(BaseModel):
    id: str
    item_id: str
    chunk_index: int
    content: str
    token_count: int | None
    created_at: datetime
```

## Files to Create

- `python-backend/src/db/repositories/__init__.py` - Export repositories
- `python-backend/src/db/repositories/base.py` - Base repository with generic interface
- `python-backend/src/db/repositories/items.py` - ItemRepository
- `python-backend/src/db/repositories/chunks.py` - ChunkRepository
- `python-backend/src/db/models.py` - Pydantic models (Item, ItemCreate, ItemUpdate, Chunk, ChunkCreate)
- `python-backend/src/exceptions.py` - Custom exception hierarchy (ItemNotFoundError, etc.)

## Verification

```python
# Should be able to perform CRUD operations
repo = ItemRepository(db)
item = await repo.create(ItemCreate(title="Test", content="Hello"))
assert item.id is not None
retrieved = await repo.get(item.id)
assert retrieved.title == "Test"
```

---

## Implementation Details

_Tracked: 2026-01-19_

### Files Changed

| File                                             | Change   | Description                                                                                              |
| ------------------------------------------------ | -------- | -------------------------------------------------------------------------------------------------------- |
| `python-backend/src/db/models.py`                | Created  | Pydantic models: Item, ItemCreate, ItemUpdate, Chunk, ChunkCreate (69 lines)                             |
| `python-backend/src/db/repositories/base.py`     | Created  | Abstract base repository with generic CRUD interface (121 lines)                                         |
| `python-backend/src/db/repositories/items.py`    | Created  | ItemRepository with full CRUD + status operations (245 lines)                                            |
| `python-backend/src/db/repositories/chunks.py`   | Created  | ChunkRepository with batch operations (138 lines)                                                        |
| `python-backend/src/db/repositories/__init__.py` | Modified | Export all repository classes                                                                            |
| `python-backend/src/exceptions.py`               | Created  | Custom exception hierarchy: CortexError, ItemNotFoundError, ChunkNotFoundError, DatabaseError (32 lines) |
| `python-backend/tests/test_repositories.py`      | Created  | Comprehensive test suite with 25 test cases (428 lines)                                                  |

**Total new code:** 1,033 lines

### Dependencies Added

None - uses existing `aiosqlite` and `pydantic` dependencies from Task 2.

### Acceptance Criteria Status

- [x] Base repository class with common CRUD operations - Implemented in `base.py:15-121`
- [x] `ItemRepository` with item-specific operations including `count()` - Implemented in `items.py:16-245`
- [x] `ChunkRepository` for chunk management - Implemented in `chunks.py:13-138`
- [x] Async database operations using `aiosqlite` - All methods use `async/await`
- [x] Proper error handling with custom exceptions - `exceptions.py` with hierarchy
- [x] Type hints with Pydantic models for input/output - All methods fully typed
- [x] UUID generation using `uuid4()` in repository `create()` methods - `items.py:57`, `chunks.py:61`
- [x] Repository module exports via `__init__.py` - Exports BaseRepository, ItemRepository, ChunkRepository

---

## Learning Report

_Generated: 2026-01-19_

### Summary

Implemented a complete repository pattern for the Cortex Python backend, providing type-safe database access with full CRUD operations. The implementation includes:

- **6 new files** totaling 1,033 lines of code
- **25 test cases** covering all repository operations
- **100% acceptance criteria** completion

### Patterns & Decisions

1. **Generic Base Repository with ABC**
   - Used Python's `Generic[T, CreateT, UpdateT]` with `ABC` for the base class
   - Provides compile-time type safety and runtime interface enforcement
   - Rationale: Ensures consistent API across all repositories while allowing type-specific implementations

2. **ChunkRepository Does Not Extend BaseRepository**
   - Decision: ChunkRepository has a standalone implementation
   - Rationale: Chunks have a fundamentally different access pattern (batch operations, always via parent item) that doesn't fit the standard CRUD interface
   - Trade-off: Less code reuse but cleaner API for chunk-specific operations

3. **Exception Handling Strategy (as per spec)**
   - `get()` returns `None` for not found - caller decides action
   - `update()` raises `ItemNotFoundError` - prevents silent failures
   - `delete()` returns `bool` - allows idempotent deletes

4. **Row-to-Model Conversion Pattern**
   - Private `_row_to_item()` / `_row_to_chunk()` methods handle conversion
   - Handles JSON deserialization for metadata field
   - Handles datetime parsing from ISO format strings

5. **DatabaseError for Post-Operation Failures**
   - Added during code review: `create()` and `update()` now raise `DatabaseError` if the subsequent `get()` returns `None`
   - Prevents masking of database issues with `type: ignore` comments

### Challenges & Solutions

1. **Type Safety for Optional Returns**
   - Challenge: `create()` must return `T` but calls `get()` which returns `T | None`
   - Initial solution: Used `type: ignore` comment
   - Final solution: Added explicit `None` check that raises `DatabaseError` (caught in CodeRabbit review)

2. **JSON Metadata Handling**
   - Challenge: SQLite stores JSON as TEXT, needs parsing on read
   - Solution: `json.loads()` in `_row_to_item()` with type check for string values

3. **Datetime Handling**
   - Challenge: SQLite stores datetimes as ISO strings
   - Solution: `datetime.fromisoformat()` in row conversion, `datetime.now(UTC).isoformat()` for writes
   - Note: Used `datetime.UTC` alias per Python 3.11+ best practices (enforced by ruff UP017 rule)

### Lessons Learned

1. **What Worked Well**
   - Task spec was comprehensive with clear method signatures
   - Following existing patterns from `docs/developer/python-backend/architecture.md` made implementation straightforward
   - Test-first approach for validation logic caught edge cases early

2. **What Could Be Improved**
   - Initial use of `type: ignore` was a code smell - explicit error handling is better
   - Could consider adding a `VectorChunkRepository` stub for future vector operations

3. **Recommendations for Similar Tasks**
   - Always validate return values after database operations instead of using type: ignore
   - Consider batch operations from the start (like ChunkRepository's `create_many`)
   - Keep repository methods focused on data access - business logic belongs in services

### Documentation Impact

1. **Existing Docs to Review**
   - `docs/developer/python-backend/architecture.md` - Should include repository patterns now that they're implemented
   - May need examples of repository usage in API routes (for Task 4)

2. **New Patterns to Document**
   - Exception handling strategy for repositories
   - Row-to-model conversion pattern
   - When to extend BaseRepository vs standalone implementation

3. **Areas Where Documentation Helped**
   - Task spec's method signatures matched exactly what was implemented
   - Exception handling strategy was clearly defined upfront
