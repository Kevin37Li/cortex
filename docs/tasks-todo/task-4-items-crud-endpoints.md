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
