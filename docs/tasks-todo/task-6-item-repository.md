# Task: Implement Item Repository

## Summary
Create the ItemRepository for CRUD operations on items.

## Acceptance Criteria
- [ ] `ItemRepository` class extending BaseRepository with:
  - `create(item: ItemCreate) -> Item`
  - `get(id: str) -> Item | None`
  - `get_all(limit: int, offset: int) -> list[Item]`
  - `update(id: str, item: ItemUpdate) -> Item`
  - `delete(id: str) -> bool`
  - `update_status(id: str, status: ProcessingStatus) -> Item`
- [ ] Pydantic models:
  - `Item` (full entity)
  - `ItemCreate` (input for creation)
  - `ItemUpdate` (partial update)
  - `ItemSummary` (list view, without full content)
- [ ] Query for items by status (for processing queue)
- [ ] Unit tests with in-memory SQLite

## Dependencies
- Task 5: Base repository pattern

## Technical Notes
- UUID generation on create (use `uuid.uuid4()`)
- Timestamps set automatically
- Return ItemSummary for list endpoints to reduce payload size

## Phase
Phase 1: Foundation
