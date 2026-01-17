# Task: Implement CRUD Endpoints for Items

## Summary

Create REST API endpoints for creating, reading, updating, and deleting items.

## Acceptance Criteria

- [ ] `POST /api/items` - Create new item
- [ ] `GET /api/items` - List items with pagination
- [ ] `GET /api/items/{id}` - Get single item
- [ ] `PUT /api/items/{id}` - Update item
- [ ] `DELETE /api/items/{id}` - Delete item
- [ ] Proper HTTP status codes (201, 200, 404, 422)
- [ ] Request/response validation with Pydantic
- [ ] OpenAPI documentation auto-generated

## Dependencies

- Task 1: Python backend project structure
- Task 2: SQLite schema setup
- Task 3: Repository pattern implementation

## Technical Notes

- Use FastAPI's dependency injection for repositories
- Follow REST conventions for URL structure
- Pagination uses `offset` and `limit` query params
- Return proper error responses for validation failures

## API Specification

```python
# Create item
POST /api/items
Request: {
    "title": "string",
    "content": "string",
    "content_type": "webpage" | "note" | "file",
    "source_url": "string | null"
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
    "processing_status": "pending"
}

# List items
GET /api/items?offset=0&limit=20
Response: 200 OK
{
    "items": [...],
    "total": 100,
    "offset": 0,
    "limit": 20
}

# Get single item
GET /api/items/{id}
Response: 200 OK | 404 Not Found

# Update item
PUT /api/items/{id}
Request: { "title": "string", "content": "string" }
Response: 200 OK | 404 Not Found

# Delete item
DELETE /api/items/{id}
Response: 204 No Content | 404 Not Found
```

## Files to Create/Modify

- `python/app/api/routes/__init__.py`
- `python/app/api/routes/items.py` - Item endpoints
- `python/app/api/deps.py` - Dependency injection helpers
- `python/app/main.py` - Register routes

## Verification

```bash
# Create item
curl -X POST http://localhost:8742/api/items \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "content": "Hello", "content_type": "note"}'

# List items
curl http://localhost:8742/api/items

# Check OpenAPI docs
open http://localhost:8742/docs
```
