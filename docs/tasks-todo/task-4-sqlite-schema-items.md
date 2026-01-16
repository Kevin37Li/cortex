# Task: Define SQLite Schema for Items Table

## Summary
Create the database schema for the items table, including migrations infrastructure.

## Acceptance Criteria
- [ ] Schema migration system (simple version-based or use alembic)
- [ ] Items table with columns:
  ```sql
  CREATE TABLE items (
    id TEXT PRIMARY KEY,           -- UUID
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_type TEXT NOT NULL,    -- 'webpage', 'note', 'markdown'
    source_url TEXT,               -- For web captures
    summary TEXT,                  -- AI-generated
    raw_content TEXT,              -- Original HTML/source
    processing_status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,      -- ISO8601
    updated_at TEXT NOT NULL,
    processed_at TEXT
  );
  ```
- [ ] Indexes on commonly queried fields (created_at, processing_status)
- [ ] Migration runs automatically on app startup
- [ ] Unit tests for schema creation

## Dependencies
- Task 3: sqlite-vec extension (for later vector columns)

## Technical Notes
- Use TEXT for dates with ISO8601 format (SQLite best practice)
- UUIDs as TEXT primary keys
- processing_status enum: 'pending', 'processing', 'completed', 'failed'
- Vector embedding columns added in Phase 2 (content processing)

## Phase
Phase 1: Foundation
