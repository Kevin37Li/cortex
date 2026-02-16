# Task: Implement Search Service (Vector, FTS, Hybrid)

## Summary

Create `SearchService` in `python-backend/src/services/search.py` that implements three search strategies: vector similarity search (sqlite-vec), full-text search (FTS5), and hybrid search combining both via Reciprocal Rank Fusion (RRF). This is the core search logic consumed by the LangGraph workflow and API endpoint.

## Acceptance Criteria

- [ ] `python-backend/src/services/search.py` created with `SearchService` class
- [ ] `vector_search(query, db, limit)` method: generates query embedding via `EmbeddingService.embed_query()`, queries `vec_chunks` for nearest neighbors, joins to `chunks` and `items` tables, returns `list[ChunkSearchResult]` sorted by similarity
- [ ] `fts_search(query, db, limit)` method: queries `chunks_fts` using FTS5 MATCH, joins to `chunks` and `items` tables, returns `list[ChunkSearchResult]` sorted by FTS5 rank
- [ ] `hybrid_search(query, db, limit)` method: runs both `vector_search` and `fts_search`, combines via `reciprocal_rank_fusion()`, deduplicates by `chunk_id`, returns fused `list[ChunkSearchResult]`
- [ ] `reciprocal_rank_fusion(vector_results, fts_results, k=60)` implemented as a standalone function
- [ ] `enrich_results(results, db)` method: converts `list[ChunkSearchResult]` to `list[SearchResultItem]` by joining item title and content_type
- [ ] Vector search normalizes sqlite-vec distances to [0, 1] scores (closer = higher score)
- [ ] FTS search normalizes FTS5 rank values to [0, 1] scores
- [ ] `SearchService.__init__` accepts `EmbeddingService` for query embedding
- [ ] All methods accept `db: aiosqlite.Connection` parameter (stateless pattern)
- [ ] Methods raise `SearchError` on failure (not bare exceptions)
- [ ] `SearchService` exported from `python-backend/src/services/__init__.py`
- [ ] Ruff and mypy pass

## Dependencies

- Task 1: Search models (`ChunkSearchResult`, `SearchResultItem`, `SearchError`)
- Phase 2: `EmbeddingService.embed_query()` exists (`python-backend/src/services/embeddings.py:128`)
- Phase 1: Database schema has `vec_chunks` (sqlite-vec), `chunks_fts` (FTS5), `chunks`, `items` tables

## Technical Notes

### SearchService Structure

```python
class SearchService:
    """Hybrid search combining vector similarity and full-text search.

    Stateless - db connection passed via method parameters.
    """

    def __init__(self, embedding_service: EmbeddingService) -> None:
        self._embedding_service = embedding_service

    async def vector_search(
        self, query: str, db: aiosqlite.Connection, limit: int = 20
    ) -> list[ChunkSearchResult]: ...

    async def fts_search(
        self, query: str, db: aiosqlite.Connection, limit: int = 20
    ) -> list[ChunkSearchResult]: ...

    async def hybrid_search(
        self, query: str, db: aiosqlite.Connection, limit: int = 20
    ) -> list[ChunkSearchResult]: ...

    async def enrich_results(
        self, results: list[ChunkSearchResult], db: aiosqlite.Connection
    ) -> list[SearchResultItem]: ...
```

### Vector Search SQL

sqlite-vec uses the `vec0` virtual table with KNN search via a special `WHERE` clause. The `embedding MATCH` operator finds nearest neighbors, and `k = ?` limits results:

```python
import sqlite_vec

query_embedding = await self._embedding_service.embed_query(query, db)
serialized = sqlite_vec.serialize_float32(query_embedding)

cursor = await db.execute(
    """
    SELECT v.chunk_id, v.distance
    FROM vec_chunks v
    WHERE v.embedding MATCH ? AND k = ?
    ORDER BY v.distance
    """,
    [serialized, limit],
)
rows = await cursor.fetchall()
```

**Distance to score normalization**: sqlite-vec returns cosine distance (0 = identical, 2 = opposite for normalized vectors). Convert to a [0, 1] similarity score:

```python
score = 1.0 - (distance / 2.0)  # 0 distance → 1.0 score, 2 distance → 0.0 score
```

Then join to chunks table to get `item_id` and `content`:

```python
cursor = await db.execute(
    """
    SELECT c.id, c.item_id, c.content
    FROM chunks c
    WHERE c.id = ?
    """,
    [chunk_id],
)
```

Or batch the join for efficiency:

```python
chunk_ids = [row["chunk_id"] for row in rows]
placeholders = ",".join("?" * len(chunk_ids))
cursor = await db.execute(
    f"SELECT id, item_id, content FROM chunks WHERE id IN ({placeholders})",
    chunk_ids,
)
```

### FTS5 Search SQL

The `chunks_fts` table is a contentless FTS5 table synced via triggers. Query it and join back to `chunks`:

```python
cursor = await db.execute(
    """
    SELECT c.id AS chunk_id, c.item_id, c.content, fts.rank
    FROM chunks_fts fts
    JOIN chunks c ON c.rowid = fts.rowid
    WHERE chunks_fts MATCH ?
    ORDER BY fts.rank
    LIMIT ?
    """,
    [query, limit],
)
```

**FTS5 rank normalization**: FTS5 `rank` is a negative relevance score (more negative = more relevant). Normalize to [0, 1]:

```python
# ranks are negative; most relevant is most negative
if not rows:
    return []
min_rank = min(row["rank"] for row in rows)  # Most relevant (most negative)
max_rank = max(row["rank"] for row in rows)  # Least relevant
range_val = max_rank - min_rank
for row in rows:
    if range_val == 0:
        score = 1.0  # All equal relevance
    else:
        score = (max_rank - row["rank"]) / range_val  # Normalize to [0, 1]
```

**FTS5 query safety**: FTS5 MATCH can raise errors on malformed queries. Sanitize by escaping special characters or wrapping in double quotes:

```python
def _sanitize_fts_query(self, query: str) -> str:
    """Escape FTS5 special characters for safe MATCH queries."""
    # Wrap each word in double quotes to treat as literal
    words = query.strip().split()
    if not words:
        return '""'
    return " ".join(f'"{word}"' for word in words)
```

### Reciprocal Rank Fusion (RRF)

RRF combines two ranked lists using the formula: `score(d) = sum(1 / (k + rank_i))` for each ranking system `i`.

```python
def reciprocal_rank_fusion(
    vector_results: list[ChunkSearchResult],
    fts_results: list[ChunkSearchResult],
    k: int = 60,
) -> list[ChunkSearchResult]:
    """Combine vector and FTS results using Reciprocal Rank Fusion.

    Args:
        vector_results: Results from vector similarity search, ordered by relevance
        fts_results: Results from FTS5 search, ordered by relevance
        k: RRF constant (default 60, standard value from the RRF paper)

    Returns:
        Combined and re-ranked results
    """
    scores: dict[str, float] = {}
    result_map: dict[str, ChunkSearchResult] = {}

    for rank, result in enumerate(vector_results, 1):
        scores[result.chunk_id] = scores.get(result.chunk_id, 0) + 1 / (k + rank)
        result_map[result.chunk_id] = result

    for rank, result in enumerate(fts_results, 1):
        scores[result.chunk_id] = scores.get(result.chunk_id, 0) + 1 / (k + rank)
        if result.chunk_id not in result_map:
            result_map[result.chunk_id] = result

    # Sort by RRF score descending
    sorted_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)

    # Normalize RRF scores to [0, 1]
    if sorted_ids:
        max_score = scores[sorted_ids[0]]
        return [
            result_map[cid].model_copy(update={"score": scores[cid] / max_score})
            for cid in sorted_ids
        ]
    return []
```

### Result Enrichment

Convert `ChunkSearchResult` to `SearchResultItem` by fetching item metadata:

```python
async def enrich_results(
    self, results: list[ChunkSearchResult], db: aiosqlite.Connection
) -> list[SearchResultItem]:
    if not results:
        return []

    # Batch fetch items
    item_ids = list({r.item_id for r in results})
    placeholders = ",".join("?" * len(item_ids))
    cursor = await db.execute(
        f"SELECT id, title, content_type FROM items WHERE id IN ({placeholders})",
        item_ids,
    )
    rows = await cursor.fetchall()
    item_map = {row["id"]: row for row in rows}

    enriched = []
    for rank, result in enumerate(results, 1):
        item = item_map.get(result.item_id)
        if item is None:
            continue  # Skip orphaned chunks
        enriched.append(SearchResultItem(
            item_id=result.item_id,
            item_title=item["title"],
            content_type=ContentType(item["content_type"]),
            chunk_id=result.chunk_id,
            chunk_content=result.content,
            score=result.score,
            rank=rank,
        ))
    return enriched
```

### Error Handling

Wrap all search operations in try/except and raise `SearchError`:

```python
async def vector_search(self, query: str, db: aiosqlite.Connection, limit: int = 20):
    try:
        # ... search logic
    except EmbeddingError as e:
        raise SearchError(
            f"Vector search failed: {e}", query=query, step="vector_search"
        ) from e
    except Exception as e:
        if isinstance(e, SearchError):
            raise
        raise SearchError(
            f"Unexpected vector search error: {e}", query=query, step="vector_search"
        ) from e
```

### Edge Cases

- **Empty query**: Raise `SearchError` for blank/whitespace-only queries
- **No embeddings in DB**: `vector_search` returns empty list (not an error)
- **FTS5 no matches**: `fts_search` returns empty list
- **Hybrid with one empty**: RRF still works with only one input list populated

## Files to Create/Modify

**Create:**

- `python-backend/src/services/search.py`

**Modify:**

- `python-backend/src/services/__init__.py` - Export `SearchService`

## Verification

```bash
cd python-backend
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/
```
