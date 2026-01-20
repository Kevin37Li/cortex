# Task: Set Up SQLite Schema with sqlite-vec Extension

## Summary

Create the SQLite database schema for storing items, chunks, and embeddings using the sqlite-vec extension for vector operations.

## Acceptance Criteria

- [ ] SQLite database file created at `~/.cortex/cortex.db` (or configurable path)
- [ ] Core tables created:
  - `items` - main content items (web pages, notes, files)
  - `chunks` - semantic chunks of content for embedding
  - `vec_chunks` - vector embeddings using sqlite-vec
- [ ] FTS5 virtual table for full-text search on chunks (with sync triggers)
- [ ] sqlite-vec extension loaded and working
- [ ] Database initialization script/migration system
- [ ] Proper indexes for common queries

## Dependencies

- Task 1: Python backend project structure

## Technical Notes

- sqlite-vec provides vector similarity search (cosine distance)
- Use embedding dimension 768 (nomic-embed-text) or 1536 (OpenAI)
- FTS5 for keyword search with BM25 ranking (on chunks for semantic retrieval)
- Use `aiosqlite` for async operations
- FTS triggers keep `chunks_fts` synchronized with `chunks` table

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
CREATE VIRTUAL TABLE vec_chunks USING vec0(
    chunk_id TEXT PRIMARY KEY,
    embedding FLOAT[768]  -- adjust dimension based on model
);

-- Full-text search on chunks
CREATE VIRTUAL TABLE chunks_fts USING fts5(
    content,
    content='chunks',
    content_rowid='rowid'
);

-- FTS sync triggers
CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, content) VALUES (new.rowid, new.content);
END;

CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES ('delete', old.rowid, old.content);
END;

CREATE TRIGGER chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES ('delete', old.rowid, old.content);
    INSERT INTO chunks_fts(rowid, content) VALUES (new.rowid, new.content);
END;

-- Indexes
CREATE INDEX idx_items_status ON items(processing_status);
CREATE INDEX idx_items_created ON items(created_at DESC);
CREATE INDEX idx_chunks_item ON chunks(item_id);
```

## Files to Create/Modify

- `python-backend/pyproject.toml` - Add `sqlite-vec>=0.1.6` dependency
- `python-backend/src/db/database.py` - Database connection and initialization (ensure `~/.cortex/` directory exists)
- `python-backend/src/db/schema.sql` - Schema definitions
- `python-backend/src/db/migrations/` - Future migration support (optional for MVP)

## Verification

```python
# Database should initialize without errors
# Vector operations should work (async pattern):
import sqlite_vec
import aiosqlite

async def verify_sqlite_vec():
    async with aiosqlite.connect(db_path) as db:
        await db.enable_load_extension(True)
        await db.execute("SELECT load_extension(?)", [sqlite_vec.loadable_path()])
        # Test vector operations
        result = await db.execute("SELECT vec_version()")
        print(await result.fetchone())
```

---

## Implementation Details

_Tracked: 2026-01-18_

### Commits

- `ddcf6b5` - Update SQLite schema documentation: rename `item_embeddings` to `vec_chunks`, enhance FTS5 integration for chunks with sync triggers
- (Uncommitted) - Database implementation files and comprehensive test suite

### Files Changed

| File                                    | Change   | Description                                                                                         |
| --------------------------------------- | -------- | --------------------------------------------------------------------------------------------------- |
| `python-backend/pyproject.toml`         | Modified | Added `aiosqlite>=0.20.0` and `sqlite-vec>=0.1.6` dependencies                                      |
| `python-backend/src/db/__init__.py`     | Modified | Exports `init_database`, `verify_database`, `get_connection`, `EMBEDDING_DIMENSION`                 |
| `python-backend/src/db/database.py`     | Created  | Core database module with async initialization, connection management, and verification             |
| `python-backend/src/db/schema.sql`      | Created  | SQL schema with items, chunks, chunks_fts tables, triggers, and indexes                             |
| `python-backend/src/main.py`            | Modified | Integrated database initialization on startup via lifespan manager, added `/api/db/status` endpoint |
| `python-backend/tests/test_database.py` | Created  | Comprehensive test suite with 20+ tests covering all database functionality                         |

### Dependencies Added

- `aiosqlite>=0.20.0` - Async SQLite operations
- `sqlite-vec>=0.1.6` - Vector similarity search extension

### Acceptance Criteria Status

- [x] SQLite database file created at `~/.cortex/cortex.db` (or configurable path) - Implemented in `config.py:12` with `CORTEX_DB_PATH` env override
- [x] Core tables created (`items`, `chunks`, `vec_chunks`) - Implemented in `schema.sql:5-25` and `database.py:28-41`
- [x] FTS5 virtual table for full-text search with sync triggers - Implemented in `schema.sql:27-47`
- [x] sqlite-vec extension loaded and working - Implemented in `database.py:21-25` with verification in `database.py:70-73`
- [x] Database initialization script - Implemented as `init_database()` in `database.py:50-83`
- [x] Proper indexes for common queries - Implemented in `schema.sql:49-54`

---

## Learning Report

_Generated: 2026-01-18_

### Summary

Implemented a complete SQLite database layer for the Cortex backend with vector similarity search capabilities. The implementation includes:

- **6 files changed** (3 created, 3 modified)
- **~450 lines of code** across database module, schema, and tests
- **20+ tests** covering extension loading, schema creation, FTS triggers, and full initialization
- **100% acceptance criteria met**

### Patterns & Decisions

#### 1. Separation of Schema from Vector Table Creation

The `vec_chunks` virtual table must be created programmatically in Python rather than in `schema.sql` because the `vec0` table type is only available after loading the sqlite-vec extension. This led to a clean separation:

- `schema.sql` - Standard SQL tables, FTS5, triggers, indexes
- `_create_vec_table()` - Vector table creation after extension load

#### 2. Async Generator for Connection Management

Used `AsyncIterator` pattern for `get_connection()` (`database.py:86-102`) to provide a clean context manager that:

- Enables foreign keys on every connection
- Loads sqlite-vec extension
- Sets row factory for dict-like access
- Properly cleans up resources

#### 3. Idempotent Initialization

All schema elements use `IF NOT EXISTS` clauses, making `init_database()` safe to call multiple times. This is verified by `test_init_database_idempotent`.

#### 4. Defensive Database Verification

The `verify_database()` function was enhanced during code review to check for database existence before connecting, preventing `aiosqlite.connect()` from silently creating an empty file. Returns HTTP 404 via the `/api/db/status` endpoint if database is missing.

### Challenges & Solutions

#### 1. sqlite-vec Extension Loading Pattern

**Challenge:** The sqlite-vec extension requires a specific loading sequence: enable extension loading → load extension → disable extension loading (for security).

**Solution:** Created `_load_sqlite_vec()` helper (`database.py:21-25`) that encapsulates this pattern and is reused in both initialization and connection retrieval.

#### 2. FTS5 Contentless Table with Sync Triggers

**Challenge:** FTS5 contentless tables (`content='chunks'`) require manual synchronization via triggers, and the delete operation uses a special syntax.

**Solution:** Implemented three triggers (`chunks_ai`, `chunks_ad`, `chunks_au`) with proper delete syntax: `INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES ('delete', ...)`. Verified with dedicated tests.

#### 3. Test Isolation with Mock Settings

**Challenge:** Tests need to use temporary databases without affecting the real `~/.cortex/cortex.db` file.

**Solution:** Created `mock_settings` fixture that patches `src.db.database.settings` with a temporary path, allowing full integration testing without side effects.

### Lessons Learned

1. **sqlite-vec is reliable**: The extension loaded consistently across test runs and the async wrapper works well with aiosqlite
2. **FTS5 trigger syntax is non-obvious**: The delete operation for contentless FTS tables requires the special first-column syntax
3. **Pytest fixtures work well with async**: The `pytest-asyncio` plugin with `asyncio_mode = "auto"` made async testing straightforward
4. **Code review catches real issues**: The CodeRabbit review identified the silent file creation bug in `verify_database()` which was a genuine error handling gap

### Documentation Impact

#### Docs That May Need Updates

- `docs/developer/data-storage/sqlite-vec.md` - Should document the actual implementation patterns used
- `docs/developer/python-backend/architecture.md` - Should reference the database layer structure

#### New Patterns to Document

- sqlite-vec extension loading sequence
- FTS5 contentless table trigger pattern
- Async generator pattern for database connections
- Test fixture pattern for mocking settings

#### Documentation That Was Helpful

- The task spec's schema design was directly usable
- Technical notes about FTS5 triggers were accurate
