# Task: Implement Base Repository Pattern

## Summary
Create abstract base repository class establishing patterns for data access layer.

## Acceptance Criteria
- [ ] Abstract `BaseRepository` class with:
  - Generic type parameter for entity type
  - Common CRUD method signatures (create, get, get_all, update, delete)
  - Database connection injection
  - Transaction support utilities
- [ ] Pydantic base models for entities:
  - `BaseEntity` with id, created_at, updated_at
  - Serialization/deserialization helpers for SQLite
- [ ] Row-to-model and model-to-row mapping utilities
- [ ] Unit tests for base utilities

## Dependencies
- Task 4: SQLite schema (need schema to test against)

## Technical Notes
- Use Pydantic v2 for data models
- Repository methods should be async
- Consider using `dataclasses` or Pydantic for SQLite row mapping
- Follow patterns from `docs/developer/python-backend/architecture.md`

## Phase
Phase 1: Foundation
