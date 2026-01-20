# Task: Implement CRUD Endpoints for Items

## Summary

Create REST API endpoints for creating, reading, updating, and deleting items.

## Acceptance Criteria

- [ ] `POST /api/items` - Create new item (201 Created)
- [ ] `GET /api/items` - List items with pagination (200 OK)
- [ ] `GET /api/items/{id}` - Get single item (200 OK, 404 Not Found)
- [ ] `PUT /api/items/{id}` - Update item (200 OK, 404 Not Found)
- [ ] `DELETE /api/items/{id}` - Delete item (204 No Content, 404 Not Found)
- [ ] Proper HTTP status codes with explicit decorators
- [ ] Request/response validation with Pydantic
- [ ] Exception handlers for consistent error responses
- [ ] OpenAPI documentation auto-generated with error responses documented

## Dependencies

- Task 1: Python backend project structure
- Task 2: SQLite schema setup
- Task 3: Repository pattern implementation

## Technical Notes

- Use FastAPI's `Depends()` pattern for repository injection
- Follow REST conventions for URL structure
- Pagination uses `offset` and `limit` query params with validation
- Return proper error responses for validation failures
- Register exception handlers in `main.py` for consistent error format

## Pydantic Models

Existing models in `python-backend/src/db/models.py`:

- `ItemCreate` - Input model for creating items
- `ItemUpdate` - Input model for updating items (all fields optional)
- `Item` - Output model with `model_config = {"from_attributes": True}`

**New model to add** for paginated list response:

```python
# Add to python-backend/src/db/models.py

class ItemListResponse(BaseModel):
    """Paginated response for listing items."""
    items: list[Item]
    total: int
    offset: int
    limit: int
```

## Dependency Injection Pattern

```python
# python-backend/src/api/deps.py
from typing import AsyncIterator

from ..db.database import get_connection
from ..db.repositories import ItemRepository


async def get_item_repository() -> AsyncIterator[ItemRepository]:
    async for db in get_connection():
        yield ItemRepository(db)
```

## API Specification

```python
# Create item
@router.post("/", response_model=Item, status_code=201,
             responses={422: {"description": "Validation error"}})
POST /api/items
Request: {
    "title": "string",
    "content": "string",
    "content_type": "webpage" | "note" | "file",
    "source_url": "string | null",
    "metadata": "object | null"
}
Response: 201 Created
{
    "id": "uuid",
    "title": "string",
    "content": "string",
    "content_type": "string",
    "source_url": "string | null",
    "created_at": "datetime",
    "updated_at": "datetime",
    "processing_status": "pending",
    "metadata": "object | null"
}

# List items (with validated pagination params)
@router.get("/", response_model=ItemListResponse)
async def list_items(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    repo: ItemRepository = Depends(get_item_repository)
):
GET /api/items?offset=0&limit=20
Response: 200 OK
{
    "items": [...],
    "total": 100,
    "offset": 0,
    "limit": 20
}

# Get single item
@router.get("/{id}", response_model=Item,
            responses={404: {"description": "Item not found"}})
GET /api/items/{id}
Response: 200 OK | 404 Not Found

# Update item
@router.put("/{id}", response_model=Item,
            responses={404: {"description": "Item not found"}})
PUT /api/items/{id}
Request: { "title": "string | null", "content": "string | null", "source_url": "string | null", "metadata": "object | null" }
Response: 200 OK | 404 Not Found

# Delete item
# Note: ItemRepository.delete() returns False if item doesn't exist.
# Check return value and raise ItemNotFoundError for 404 response.
@router.delete("/{id}", status_code=204,
               responses={404: {"description": "Item not found"}})
async def delete_item(id: str, repo: ItemRepository = Depends(get_item_repository)):
    deleted = await repo.delete(id)
    if not deleted:
        raise ItemNotFoundError(id)
    return Response(status_code=204)
DELETE /api/items/{id}
Response: 204 No Content | 404 Not Found
```

**Required imports for routes:**

```python
from fastapi import APIRouter, Depends, Query, Response
from ..db.models import Item, ItemCreate, ItemUpdate, ItemListResponse
from ..exceptions import ItemNotFoundError
from .deps import get_item_repository
```

## Exception Handlers

Register in `main.py` for consistent error responses:

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from .exceptions import ItemNotFoundError, DatabaseError

@app.exception_handler(ItemNotFoundError)
async def item_not_found_handler(request: Request, exc: ItemNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": "item_not_found", "message": str(exc)}
    )

@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    return JSONResponse(
        status_code=500,
        content={"error": "database_error", "message": "Internal database error"}
    )
```

## Files to Create/Modify

- `python-backend/src/api/__init__.py` - Package init (if not exists)
- `python-backend/src/api/items.py` - Item endpoints
- `python-backend/src/api/deps.py` - Dependency injection helpers
- `python-backend/src/db/models.py` - Add `ItemListResponse` model
- `python-backend/src/main.py` - Register routes and exception handlers

## Verification

```bash
# Create item
curl -X POST http://localhost:8742/api/items \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "content": "Hello", "content_type": "note"}'

# List items
curl http://localhost:8742/api/items

# Get single item (replace {id} with actual UUID)
curl http://localhost:8742/api/items/{id}

# Update item
curl -X PUT http://localhost:8742/api/items/{id} \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title"}'

# Delete item
curl -X DELETE http://localhost:8742/api/items/{id}

# Test 404 error
curl http://localhost:8742/api/items/nonexistent-id

# Check OpenAPI docs
open http://localhost:8742/docs
```

---

## Implementation Details

_Tracked: 2026-01-20_

### Files Changed

| File                                     | Change   | Description                                               |
| ---------------------------------------- | -------- | --------------------------------------------------------- |
| `python-backend/src/api/items.py`        | Created  | CRUD endpoints for items (91 lines)                       |
| `python-backend/src/api/deps.py`         | Created  | Dependency injection helper for ItemRepository (16 lines) |
| `python-backend/src/api/__init__.py`     | Modified | Added items_router export                                 |
| `python-backend/src/db/models.py`        | Modified | Added ItemListResponse Pydantic model                     |
| `python-backend/src/main.py`             | Modified | Added exception handlers and router registration          |
| `python-backend/pyproject.toml`          | Modified | Added ruff ignore for B008 (FastAPI Depends pattern)      |
| `python-backend/tests/test_api_items.py` | Created  | Comprehensive API endpoint tests (264 lines, 13 tests)    |

### Dependencies Added

- None - used existing FastAPI and Pydantic dependencies

### Acceptance Criteria Status

- [x] `POST /api/items` - Create new item (201 Created) - Implemented in `items.py:13-27`
- [x] `GET /api/items` - List items with pagination (200 OK) - Implemented in `items.py:30-42`
- [x] `GET /api/items/{id}` - Get single item (200 OK, 404 Not Found) - Implemented in `items.py:45-58`
- [x] `PUT /api/items/{id}` - Update item (200 OK, 404 Not Found) - Implemented in `items.py:61-75`
- [x] `DELETE /api/items/{id}` - Delete item (204 No Content, 404 Not Found) - Implemented in `items.py:78-91`
- [x] Proper HTTP status codes with explicit decorators - All endpoints use `status_code` and `responses` parameters
- [x] Request/response validation with Pydantic - Uses `ItemCreate`, `ItemUpdate`, `Item`, `ItemListResponse`
- [x] Exception handlers for consistent error responses - `ItemNotFoundError` and `DatabaseError` handlers in `main.py:33-47`
- [x] OpenAPI documentation auto-generated with error responses documented - All endpoints include `responses` parameter

---

## Learning Report

_Generated: 2026-01-20_

### Summary

Implemented a complete REST API for items with full CRUD operations. The implementation follows FastAPI best practices with dependency injection, proper exception handling, and comprehensive test coverage.

**Key Metrics:**

- 7 files changed (3 created, 4 modified)
- 371 lines of new code
- 13 API tests passing
- 5 API endpoints implemented
- All automated checks passing (typecheck, lint, format, tests)

### Patterns & Decisions

#### 1. Dependency Injection with AsyncIterator

Used `AsyncIterator[ItemRepository]` pattern for dependency injection:

```python
async def get_item_repository() -> AsyncIterator[ItemRepository]:
    async for db in get_connection():
        yield ItemRepository(db)
```

This leverages FastAPI's built-in dependency injection and ensures proper cleanup of database connections through the async generator pattern.

#### 2. Centralized Exception Handlers

Registered exception handlers in `main.py` rather than handling errors in each endpoint:

- `ItemNotFoundError` → 404 with `{"error": "item_not_found", "message": "..."}`
- `DatabaseError` → 500 with `{"error": "database_error", "message": "Internal database error"}`

This provides consistent error response format across all endpoints without duplicating code.

#### 3. Explicit HTTP Status Codes

Used FastAPI decorators to explicitly declare status codes and error responses:

```python
@router.post("/", response_model=Item, status_code=201,
             responses={422: {"description": "Validation error"}})
```

This improves OpenAPI documentation and makes the API contract explicit.

#### 4. Ruff B008 Ignore

Added `B008` to ruff ignore list because FastAPI's `Depends()` and `Query()` patterns require function calls in default arguments - this is intentional, not a code smell.

### Challenges & Solutions

#### 1. Delete Endpoint 404 Handling

**Challenge:** `ItemRepository.delete()` returns a boolean indicating success, but doesn't raise an exception for non-existent items.

**Solution:** Check the return value and explicitly raise `ItemNotFoundError`:

```python
deleted = await repo.delete(id)
if not deleted:
    raise ItemNotFoundError(id)
return Response(status_code=204)
```

#### 2. Test Fixture for Database Isolation

**Challenge:** Tests needed isolated database instances to prevent cross-test pollution.

**Solution:** Used pytest fixture with `tmp_path` and patched `settings.db_path`:

```python
@pytest.fixture
async def client(temp_db_path: Path):
    with patch("src.config.settings.db_path", temp_db_path):
        await init_database()
        # ... client setup
```

### Lessons Learned

1. **Task spec quality matters**: The detailed API specification in the task file made implementation straightforward - exact function signatures, imports, and patterns were provided.

2. **Exception handlers simplify endpoint code**: Centralizing error handling in `main.py` keeps endpoint functions focused on business logic.

3. **Test isolation is critical**: Each test gets a fresh database via the fixture, preventing flaky tests from shared state.

4. **Pagination validation in Query params**: Using `Query(default=0, ge=0)` and `Query(default=20, ge=1, le=100)` provides automatic validation with proper 422 error responses.

### Documentation Impact

1. **Python Backend Architecture** (`docs/developer/python-backend/architecture.md`)
   - Should document the dependency injection pattern used for repositories
   - Should include the exception handler pattern

2. **API Documentation**
   - OpenAPI docs are auto-generated at `/docs`
   - Error response format (`{"error": "...", "message": "..."}`) should be documented as a standard

3. **Testing Patterns**
   - The async test fixture pattern with `httpx.AsyncClient` and `ASGITransport` should be documented for future endpoint tests
