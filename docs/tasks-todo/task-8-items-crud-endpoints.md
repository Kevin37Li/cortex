# Task: Create Items CRUD Endpoints

## Summary
Implement REST API endpoints for item management.

## Acceptance Criteria
- [ ] Endpoints implemented:
  - `POST /api/items` - Create item
  - `GET /api/items` - List items (paginated)
  - `GET /api/items/{id}` - Get single item
  - `PUT /api/items/{id}` - Update item
  - `DELETE /api/items/{id}` - Delete item
- [ ] Request/response models with Pydantic
- [ ] Pagination support (limit, offset query params)
- [ ] Proper HTTP status codes (201 created, 404 not found, etc.)
- [ ] OpenAPI documentation auto-generated
- [ ] Unit tests for all endpoints

## Dependencies
- Task 6: Item repository

## Technical Notes
- Follow REST conventions
- Use dependency injection for repository
- Validate content_type against allowed enum values
- Return ItemSummary for list, full Item for single get

## API Examples
```
POST /api/items
{
  "title": "My Note",
  "content": "Note content...",
  "content_type": "note"
}

GET /api/items?limit=20&offset=0

GET /api/items/550e8400-e29b-41d4-a716-446655440000
```

## Phase
Phase 1: Foundation
