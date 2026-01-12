# sqlite-vec Vector Storage

Vector embeddings storage using the sqlite-vec extension.

## Overview

[sqlite-vec](https://github.com/asg017/sqlite-vec) is a SQLite extension that adds vector search capabilities. It allows us to store embeddings and perform similarity search in the same database as our other data.

## Why sqlite-vec

| Alternative | Pros | Cons |
|-------------|------|------|
| **Pinecone/Weaviate** | Powerful, scalable | Cloud-based, defeats local-first |
| **ChromaDB** | Local, popular | Separate process, adds complexity |
| **pgvector** | Great with Postgres | Requires PostgreSQL server |
| **sqlite-vec** | Native SQLite, single file | Newer, smaller community |

**Our choice**: sqlite-vec keeps everything in one file. Items, chunks, embeddings, and conversations all live together. This simplifies backup, portability, and the mental model.

## Installation

### Python

```bash
pip install sqlite-vec
```

### Loading the Extension

```python
import sqlite3
import sqlite_vec

db = sqlite3.connect("cortex.db")
db.enable_load_extension(True)
sqlite_vec.load(db)
db.enable_load_extension(False)
```

### Async with aiosqlite

```python
import aiosqlite
import sqlite_vec

async def connect():
    db = await aiosqlite.connect("cortex.db")
    await db.enable_load_extension(True)
    await db.execute("SELECT load_extension(?)", [sqlite_vec.loadable_path()])
    await db.enable_load_extension(False)
    return db
```

## Schema Design

### Vector Table

```sql
-- Create virtual table for vector storage
CREATE VIRTUAL TABLE vec_chunks USING vec0(
    chunk_id INTEGER PRIMARY KEY,
    embedding FLOAT[768]  -- Dimension must match your model
);
```

### Related Tables

```sql
-- Main chunks table
CREATE TABLE chunks (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL REFERENCES items(id),
    content TEXT NOT NULL,
    position INTEGER NOT NULL,  -- Order within document
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(item_id, position)
);

-- Index for fast item lookups
CREATE INDEX idx_chunks_item ON chunks(item_id);
```

### Complete Schema Example

```sql
-- Items (saved content)
CREATE TABLE items (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT,
    content TEXT NOT NULL,
    source TEXT NOT NULL,  -- 'browser_extension', 'manual', 'import'
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'processing', 'ready', 'failed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- Chunks (semantic segments)
CREATE TABLE chunks (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    position INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vector embeddings
CREATE VIRTUAL TABLE vec_chunks USING vec0(
    chunk_id TEXT PRIMARY KEY,
    embedding FLOAT[768]
);

-- Full-text search
CREATE VIRTUAL TABLE chunks_fts USING fts5(
    content,
    content='chunks',
    content_rowid='rowid'
);

-- Keep FTS in sync
CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, content) VALUES (new.rowid, new.content);
END;

CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES('delete', old.rowid, old.content);
END;
```

## Basic Operations

### Insert Embedding

```python
async def insert_embedding(db, chunk_id: str, embedding: list[float]):
    # Convert to bytes for sqlite-vec
    embedding_bytes = struct.pack(f'{len(embedding)}f', *embedding)

    await db.execute(
        "INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)",
        [chunk_id, embedding_bytes]
    )
    await db.commit()
```

### Batch Insert

```python
async def insert_embeddings_batch(
    db,
    chunk_embeddings: list[tuple[str, list[float]]]
):
    for chunk_id, embedding in chunk_embeddings:
        embedding_bytes = struct.pack(f'{len(embedding)}f', *embedding)
        await db.execute(
            "INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)",
            [chunk_id, embedding_bytes]
        )
    await db.commit()
```

### Vector Search

```python
async def vector_search(
    db,
    query_embedding: list[float],
    limit: int = 10
) -> list[dict]:
    query_bytes = struct.pack(f'{len(query_embedding)}f', *query_embedding)

    cursor = await db.execute("""
        SELECT
            v.chunk_id,
            v.distance,
            c.content,
            c.item_id
        FROM vec_chunks v
        JOIN chunks c ON c.id = v.chunk_id
        WHERE v.embedding MATCH ?
          AND k = ?
        ORDER BY v.distance
    """, [query_bytes, limit])

    rows = await cursor.fetchall()
    return [
        {
            "chunk_id": row[0],
            "distance": row[1],
            "content": row[2],
            "item_id": row[3]
        }
        for row in rows
    ]
```

### Delete Embeddings

```python
async def delete_item_embeddings(db, item_id: str):
    # Get chunk IDs for this item
    cursor = await db.execute(
        "SELECT id FROM chunks WHERE item_id = ?",
        [item_id]
    )
    chunk_ids = [row[0] for row in await cursor.fetchall()]

    # Delete from vector table
    for chunk_id in chunk_ids:
        await db.execute(
            "DELETE FROM vec_chunks WHERE chunk_id = ?",
            [chunk_id]
        )

    await db.commit()
```

## Hybrid Search

Combine vector similarity with full-text search for best results.

### Implementation

```python
async def hybrid_search(
    db,
    query: str,
    query_embedding: list[float],
    limit: int = 10
) -> list[dict]:
    # Vector search
    vector_results = await vector_search(db, query_embedding, limit=limit * 2)

    # Full-text search
    cursor = await db.execute("""
        SELECT
            c.id as chunk_id,
            c.content,
            c.item_id,
            bm25(chunks_fts) as score
        FROM chunks_fts
        JOIN chunks c ON c.rowid = chunks_fts.rowid
        WHERE chunks_fts MATCH ?
        ORDER BY score
        LIMIT ?
    """, [query, limit * 2])
    fts_results = await cursor.fetchall()

    # Reciprocal Rank Fusion
    return reciprocal_rank_fusion(vector_results, fts_results, limit)


def reciprocal_rank_fusion(
    vector_results: list[dict],
    fts_results: list,
    limit: int,
    k: int = 60
) -> list[dict]:
    scores = {}

    # Score from vector results
    for rank, result in enumerate(vector_results):
        chunk_id = result["chunk_id"]
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank + 1)

    # Score from FTS results
    for rank, row in enumerate(fts_results):
        chunk_id = row[0]
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank + 1)

    # Sort by combined score
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    # Build final results
    results = []
    seen = set()
    for chunk_id in sorted_ids[:limit]:
        if chunk_id in seen:
            continue
        seen.add(chunk_id)
        # Fetch full chunk data
        # ...
        results.append(...)

    return results
```

## Performance Considerations

### Index Configuration

sqlite-vec uses approximate nearest neighbor (ANN) search:

```sql
-- Default configuration works well for < 100K vectors
CREATE VIRTUAL TABLE vec_chunks USING vec0(
    chunk_id TEXT PRIMARY KEY,
    embedding FLOAT[768]
);

-- For larger datasets, tune the index
CREATE VIRTUAL TABLE vec_chunks USING vec0(
    chunk_id TEXT PRIMARY KEY,
    embedding FLOAT[768],
    -- Adjust based on dataset size
    +nlist = 100,  -- Number of clusters
    +nprobe = 10   -- Clusters to search
);
```

### Benchmarks

Approximate performance on typical hardware:

| Dataset Size | Insert (per item) | Search (top 10) |
|--------------|-------------------|-----------------|
| 10K chunks | ~1ms | ~5ms |
| 100K chunks | ~1ms | ~20ms |
| 1M chunks | ~2ms | ~100ms |

### Memory Usage

sqlite-vec loads index into memory:
- ~4 bytes × dimensions × chunks for vectors
- 768 dims × 100K chunks ≈ 300MB

For very large datasets, consider:
- Disk-based index options
- Sharding by time period
- Archiving old content

## Migration Strategy

### Changing Embedding Models

If you switch embedding models (e.g., from 768 to 1536 dimensions):

```python
async def migrate_embeddings(db, new_model_dims: int):
    # 1. Create new vector table
    await db.execute(f"""
        CREATE VIRTUAL TABLE vec_chunks_new USING vec0(
            chunk_id TEXT PRIMARY KEY,
            embedding FLOAT[{new_model_dims}]
        )
    """)

    # 2. Re-embed all chunks (this is the slow part)
    cursor = await db.execute("SELECT id, content FROM chunks")
    chunks = await cursor.fetchall()

    for chunk_id, content in chunks:
        new_embedding = await provider.embed(content)
        embedding_bytes = struct.pack(f'{len(new_embedding)}f', *new_embedding)
        await db.execute(
            "INSERT INTO vec_chunks_new VALUES (?, ?)",
            [chunk_id, embedding_bytes]
        )

    # 3. Swap tables
    await db.execute("DROP TABLE vec_chunks")
    await db.execute("ALTER TABLE vec_chunks_new RENAME TO vec_chunks")

    # 4. Update metadata
    await db.execute(
        "UPDATE settings SET value = ? WHERE key = 'embedding_model'",
        [new_model_name]
    )

    await db.commit()
```

## Risks & Mitigations

### Risk: sqlite-vec Maturity

**Concern**: sqlite-vec is newer than alternatives like ChromaDB.

**Mitigations**:
- Extensive testing with realistic data volumes
- Regular backups of the database file
- Fallback plan: migrate to ChromaDB if critical issues arise (similar API)
- sqlite-vec is actively maintained and used in production by others

### Risk: Extension Loading

**Concern**: Loading native extensions can be platform-specific.

**Mitigations**:
- Bundle pre-compiled extensions for all platforms
- Test on all platforms in CI
- Graceful degradation: disable vector search if extension fails

## Debugging

### Check Extension Loaded

```python
cursor = await db.execute("SELECT vec_version()")
version = await cursor.fetchone()
print(f"sqlite-vec version: {version[0]}")
```

### Inspect Vector Table

```python
# Count vectors
cursor = await db.execute("SELECT COUNT(*) FROM vec_chunks")
count = await cursor.fetchone()
print(f"Stored vectors: {count[0]}")

# Check dimensions
cursor = await db.execute("""
    SELECT vec_length(embedding) FROM vec_chunks LIMIT 1
""")
dims = await cursor.fetchone()
print(f"Embedding dimensions: {dims[0]}")
```

## Related Documentation

- [Embeddings](../ai/embeddings.md) - Embedding generation strategy
- [Data Persistence](./data-persistence.md) - Overall storage patterns
