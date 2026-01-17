# Task: Set Up SQLite Schema with sqlite-vec Extension

## Summary

Create the SQLite database schema for storing items, chunks, and embeddings using the sqlite-vec extension for vector operations.

## Acceptance Criteria

- [ ] SQLite database file created at `~/.cortex/cortex.db` (or configurable path)
- [ ] Core tables created:
  - `items` - main content items (web pages, notes, files)
  - `chunks` - semantic chunks of content for embedding
  - `item_embeddings` - vector embeddings using sqlite-vec
- [ ] FTS5 virtual table for full-text search on items
- [ ] sqlite-vec extension loaded and working
- [ ] Database initialization script/migration system
- [ ] Proper indexes for common queries

## Dependencies

- Task 1: Python backend project structure

## Technical Notes

- sqlite-vec provides vector similarity search (cosine distance)
- Use embedding dimension 768 (nomic-embed-text) or 1536 (OpenAI)
- FTS5 for keyword search with BM25 ranking
- Use `aiosqlite` for async operations

## Schema Design

```sql
-- Items table
CREATE TABLE items (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_type TEXT NOT NULL,  -- 'webpage', 'note', 'file'
    source_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    processing_status TEXT DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
    metadata JSON
);

-- Chunks table
CREATE TABLE chunks (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    token_count INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Vector embeddings (sqlite-vec)
CREATE VIRTUAL TABLE item_embeddings USING vec0(
    chunk_id TEXT PRIMARY KEY,
    embedding FLOAT[768]  -- adjust dimension based on model
);

-- Full-text search
CREATE VIRTUAL TABLE items_fts USING fts5(
    title,
    content,
    content='items',
    content_rowid='rowid'
);

-- Indexes
CREATE INDEX idx_items_status ON items(processing_status);
CREATE INDEX idx_items_created ON items(created_at DESC);
CREATE INDEX idx_chunks_item ON chunks(item_id);
```

## Files to Create/Modify

- `python-backend/src/db/database.py` - Database connection and initialization
- `python-backend/src/db/schema.sql` - Schema definitions
- `python-backend/src/db/migrations/` - Future migration support (optional for MVP)

## Verification

```python
# Database should initialize without errors
# Vector operations should work:
from sqlite_vec import load
conn.enable_load_extension(True)
conn.load_extension(load())
```
