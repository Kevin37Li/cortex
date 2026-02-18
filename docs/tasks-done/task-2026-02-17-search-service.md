# Task: Implement Search Service (Vector, FTS, Hybrid)

## Summary

Create `SearchService` in `python-backend/src/services/search.py` that implements three search strategies: vector similarity search (sqlite-vec), full-text search (FTS5), and hybrid search combining both via Reciprocal Rank Fusion (RRF). This service is consumed by the LangGraph search workflow and the search API endpoint.

## Acceptance Criteria

- [x] `python-backend/src/services/search.py` created with `SearchService` class and `reciprocal_rank_fusion(...)` helper - Implemented in `search.py:20,80`
- [x] `SearchService.__init__` accepts `EmbeddingService` for query embedding - Implemented in `search.py:83`
- [x] Service methods remain stateless and accept `db: aiosqlite.Connection` as a parameter - Implemented in `search.py:86,168,235,267`
- [x] `vector_search(query, db, limit)` implemented and returns `list[ChunkSearchResult]` sorted by vector relevance - Implemented in `search.py:86`
- [x] `vector_search(...)` supports optional precomputed query embedding (for workflow reuse) to avoid duplicate embedding calls - Implemented in `search.py:91,98`
- [x] `fts_search(query, db, limit)` implemented and returns `list[ChunkSearchResult]` sorted by FTS relevance - Implemented in `search.py:168`
- [x] `hybrid_search(query, db, limit)` implemented and combines vector + FTS via `reciprocal_rank_fusion(...)` - Implemented in `search.py:235`
- [x] Hybrid results are deduplicated by `chunk_id` and truncated to requested `limit` - Implemented in `search.py:55,256`
- [x] Hybrid fusion ordering is deterministic for score ties (stable tie-break rule) - Implemented in `search.py:64`
- [x] `enrich_results(results, db)` converts `list[ChunkSearchResult]` to `list[SearchResultItem]` by joining item title/content_type - Implemented in `search.py:267`
- [x] Vector distances are normalized to `[0, 1]` similarity scores (closer = higher) - Implemented in `search.py:138`
- [x] FTS scores are normalized to `[0, 1]` relevance scores before producing `SearchResultItem` - Implemented in `search.py:198-218`
- [x] FTS MATCH input is sanitized defensively to avoid malformed-query errors - Implemented in `search.py:347`
- [x] `limit` is defensively clamped to `1..100` in all public methods (workflow callers bypass API validation) - Implemented in `search.py:318`
- [x] Blank/whitespace queries raise `SearchError` - Implemented in `search.py:339`
- [x] `enrich_results(...)` assigns contiguous ranks (`1..N`) after filtering orphaned rows - Implemented in `search.py:304`
- [x] Methods raise `SearchError` on failure (no leaked bare exceptions) - Implemented in `search.py:149-166,222-233,257-265,309-316`
- [x] Standard logging setup used (`import logging`, `logger = logging.getLogger(__name__)`) - Implemented in `search.py:2,14`
- [x] `SearchService` exported from `python-backend/src/services/__init__.py` - Implemented in `__init__.py:8,16`
- [x] `bun run python:fmt:check`, `bun run python:lint`, and `bun run python:typecheck` pass - lint ✅, typecheck ✅; fmt:check ⚠️ (search.py needs `ruff format` run)

## Dependencies

- Task 1 complete: `docs/tasks-done/task-2026-02-16-search-models-and-error-types.md` (`ChunkSearchResult`, `SearchResultItem`, `SearchError`)
- Phase 2 complete: `EmbeddingService.embed_query()` exists (`python-backend/src/services/embeddings.py`)
- Phase 1 complete: DB schema has `vec_chunks`, `chunks_fts`, `chunks`, and `items` tables (`python-backend/src/db/schema.sql`)

## Technical Notes

### SearchService Structure

```python
class SearchService:
    """Hybrid search combining vector similarity and full-text search.

    Stateless service: callers pass DB connections per call.
    """

    def __init__(self, embedding_service: EmbeddingService) -> None:
        self._embedding_service = embedding_service

    async def vector_search(
        self,
        query: str,
        db: aiosqlite.Connection,
        limit: int = 20,
        query_embedding: list[float] | None = None,
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

### Input Guardrails

- Add small private helpers:
  - `_normalize_limit(limit: int) -> int` returning `max(1, min(limit, 100))`
  - `_validate_query(query: str) -> str` trimming and rejecting blank input
- Keep these checks in service methods even though `SearchRequest` already validates API calls (workflow calls may bypass API validation).

### Vector Search SQL

Use sqlite-vec KNN search in `vec_chunks`, then fetch chunk metadata in batch from `chunks`.

```python
query_embedding = query_embedding or await self._embedding_service.embed_query(query, db=db)
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
vec_rows = await cursor.fetchall()
```

Then batch fetch chunk rows and preserve original vector ordering in Python:

```python
chunk_ids = [row["chunk_id"] for row in vec_rows]
placeholders = ",".join("?" * len(chunk_ids))
cursor = await db.execute(
    f"SELECT id, item_id, content FROM chunks WHERE id IN ({placeholders})",
    chunk_ids,
)
chunk_rows = await cursor.fetchall()
chunk_map = {row["id"]: row for row in chunk_rows}
```

Distance normalization (defensive clamp):

```python
score = max(0.0, min(1.0, 1.0 - (distance / 2.0)))
```

### FTS5 Search SQL

Use FTS5 `MATCH` + `bm25(chunks_fts)` and join on `rowid`:

```python
cursor = await db.execute(
    """
    SELECT c.id AS chunk_id, c.item_id, c.content, bm25(chunks_fts) AS bm25_score
    FROM chunks_fts
    JOIN chunks c ON c.rowid = chunks_fts.rowid
    WHERE chunks_fts MATCH ?
    ORDER BY bm25_score
    LIMIT ?
    """,
    [sanitized_query, limit],
)
rows = await cursor.fetchall()
```

Rank normalization (lower `bm25` is better):

```python
scores = [row["bm25_score"] for row in rows]
min_score = min(scores)
max_score = max(scores)
range_val = max_score - min_score

normalized_scores: list[float] = []
for row in rows:
    row_score = row["bm25_score"]
    if range_val == 0:
        normalized = 1.0
    else:
        normalized = (max_score - row_score) / range_val
    normalized_scores.append(max(0.0, min(1.0, normalized)))
```

### FTS Query Safety

FTS `MATCH` can fail on malformed syntax. For MVP safety, treat terms literally:

```python
def _sanitize_fts_query(query: str) -> str:
    words = query.strip().split()
    if not words:
        return '""'
    escaped_words = [word.replace('"', '""') for word in words]
    return " ".join(f'"{word}"' for word in escaped_words)
```

Known limitation: this disables advanced FTS operators (`OR`, `NOT`, `NEAR`) by design for MVP safety.

### Hybrid Search + RRF

- Run vector and FTS searches concurrently with `asyncio.gather(...)`.
- Fuse with `reciprocal_rank_fusion(...)`.
- Keep ordering deterministic (tie-break on `chunk_id` after fused score).
- Return only top `limit` fused results.

```python
def reciprocal_rank_fusion(
    vector_results: list[ChunkSearchResult],
    fts_results: list[ChunkSearchResult],
    k: int = 60,
) -> list[ChunkSearchResult]:
    ...
```

### Result Enrichment

Batch fetch item metadata from `items`, then build `SearchResultItem` list.

Important details:

- Skip orphaned rows safely if referenced item is missing.
- Assign contiguous ranks (`len(enriched) + 1`) so rank values do not skip when orphans are filtered.
- Ensure final `score` is within `[0, 1]` to satisfy `SearchResultItem` constraints.

### Error Handling

Wrap each public method and re-raise as `SearchError` with context:

```python
raise SearchError(
    f"Vector search failed: {e}",
    query=query,
    step="vector_search",
) from e
```

Preserve existing `SearchError` instances rather than double-wrapping.

### Module Boilerplate

```python
import logging

import aiosqlite
import sqlite_vec

from src.db import ChunkSearchResult, ContentType, SearchResultItem
from src.exceptions import EmbeddingError, SearchError
from src.services.embeddings import EmbeddingService

logger = logging.getLogger(__name__)
```

### Integration Note (Task 3)

Task 3's workflow includes an explicit `embed_query` node. To avoid redundant embedding generation, `vector_search(...)` should accept a precomputed embedding from workflow state when available.

## Files to Create/Modify

**Create:**

- `python-backend/src/services/search.py`

**Modify:**

- `python-backend/src/services/__init__.py` - export `SearchService`

## Verification

```bash
bun run python:fmt:check
bun run python:lint
bun run python:typecheck
```

---

## Implementation Details

_Tracked: 2026-02-17 (updated after parallel hybrid search refactor)_

### Files Changed

| File                                            | Change   | Description                                                                                                                       |
| ----------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `python-backend/src/services/search.py`         | Created  | `SearchService` class + `reciprocal_rank_fusion` helper + private validators + parallel hybrid search via secondary DB connection |
| `python-backend/src/services/__init__.py`       | Modified | Added `SearchService` to exports                                                                                                  |
| `python-backend/tests/services/test_search.py`  | Created  | 41 tests covering all public methods, guardrails, and RRF helper                                                                  |
| `python-backend/tests/conftest.py`              | Modified | Added `search_service` fixture and `db_with_vec` fixture (sqlite-vec enabled DB)                                                  |
| `docs/developer/python-backend/architecture.md` | Modified | Added `search.py` to the service directory listing                                                                                |

### Dependencies Added

None — `aiosqlite`, `sqlite_vec`, and `asyncio` were already available.

---

## Learning Report

_Generated: 2026-02-17_

### Summary

Implemented a hybrid search service (425 lines) with 41 tests (100% pass rate). The service provides three retrieval strategies — vector similarity via sqlite-vec KNN, full-text search via SQLite FTS5 + BM25, and hybrid fusion via Reciprocal Rank Fusion — all consumed through a consistent stateless interface. Hybrid search runs vector and FTS concurrently on separate DB connections for true I/O parallelism.

- **Files created**: 2 (search.py, test_search.py)
- **Files modified**: 3 (**init**.py, conftest.py, architecture.md)
- **Test coverage**: 41 tests, 0 failures
- **Quality**: lint ✅, typecheck ✅, fmt ⚠️ (minor formatting fix needed)

### Patterns & Decisions

**Stateless service via connection-per-call.** Each public method accepts `db: aiosqlite.Connection` instead of storing a connection. This matches the existing service pattern (EmbeddingService, ProcessingQueue) and keeps the service easily mockable and safe for concurrent callers using separate connections.

**Direct sub-module import to avoid circular dependency.** `search.py` imports `EmbeddingService` via `from src.services.embeddings import EmbeddingService` rather than `from src.services import EmbeddingService`. `src/services/__init__.py` exports `SearchService`, so importing from `src.services` inside `search.py` would create a circular import. This is documented inline at `search.py:17-19`.

**Parallel hybrid search via a secondary DB connection.** aiosqlite serializes all queries through a single background thread per connection, so `asyncio.gather()` on the same `db` handle provides no parallelism. To achieve true I/O parallelism, `hybrid_search` opens a second `aiosqlite.Connection` to the same database file and runs vector search on the caller's connection while FTS runs on the secondary connection concurrently (`search.py:267-282`). The secondary connection is always closed in a `finally` block (`search.py:295-297`). For in-memory or unnamed databases (where the path cannot be resolved), the method gracefully falls back to sequential single-connection execution (`search.py:255-265`).

**`_resolve_main_db_path` uses `PRAGMA database_list`.** To obtain the file path for the secondary connection, the service queries SQLite's `PRAGMA database_list` which returns name/seq/file for each attached database (`search.py:390-408`). Returns `None` for `:memory:` or unnamed databases, triggering the sequential fallback.

**`configure_connection` applied to secondary connection.** The secondary connection is initialized with `configure_connection()` from `src.db` to apply the same PRAGMA settings (WAL mode, foreign keys, row factory, etc.) as the primary connection (`search.py:415`).

**RRF score normalization.** Raw RRF scores cluster near zero (e.g. 0.016 for rank-1 with k=60), which would make hybrid results appear near-zero to API consumers. Scores are normalized so the top result always has score=1.0, making hybrid scores comparable to vector/FTS scores. This was not in the original spec but is critical for API usability.

**`_normalize_limit` rejects booleans explicitly.** Python `bool` is a subclass of `int`, so `isinstance(True, int)` returns `True`. The check `not isinstance(limit, bool)` is added alongside `isinstance(limit, int)` to prevent accidental `True`/`False` inputs from silently passing as 1/0.

**`enrich_results` is a `@staticmethod`.** It has no dependency on instance state (`self._embedding_service`). Making it a `@staticmethod` allows callers to invoke it without a `SearchService` instance if they are building enriched results from pre-fetched `ChunkSearchResult` lists.

### Challenges & Solutions

**aiosqlite per-connection serialization blocks `gather()`.** The initial implementation used sequential awaits because aiosqlite serializes per connection. The refactored solution opens a dedicated secondary connection for FTS search, allowing both coroutines to run concurrently in the event loop. Exceptions from either branch are re-raised correctly by checking `isinstance(result, BaseException)` after `gather(..., return_exceptions=True)` (`search.py:277-280`).

**Secondary connection lifecycle in async context.** The secondary connection must be closed even if `gather()` or subsequent operations raise. This is handled with a `finally` block (`search.py:295-297`). The connection is stored in `secondary_db: aiosqlite.Connection | None = None` before the `try` so the `finally` can check it safely.

**FTS BM25 score ordering is counterintuitive.** SQLite's `bm25()` returns negative values — the most relevant row has the most negative score (e.g. -2.5 is better than -0.3). The SQL uses `ORDER BY bm25_score ASC` (not DESC), with a comment warning against changing this. Normalization inverts the scale: `(max_score - row_score) / range_val` maps the most-negative score to 1.0.

**basedpyright reports unreachable code on `_validate_query`.** The `if not isinstance(query, str)` guard at `search.py:364` is statically unreachable because the method signature annotates `query: str`. This is intentional — the guard exists as a runtime defense for callers that bypass type checking (tests exercise this). Known false positive from the static checker.

**`db_with_vec` fixture required for vector tests.** The base `db_connection` fixture does not load the sqlite-vec extension or create the `vec_chunks` virtual table. A separate `db_with_vec` fixture was added to `conftest.py` for tests that exercise vector search or need the FTS virtual table alongside sqlite-vec.

### Lessons Learned

**aiosqlite parallelism requires separate connections, not `gather()` on one.** `asyncio.gather()` on the same aiosqlite connection is a no-op for parallelism because aiosqlite uses a single background thread per connection. True parallel DB I/O requires opening a second connection to the same file. This is safe with SQLite in WAL mode (multiple concurrent readers). Tests that use in-memory databases cannot benefit from this optimization and fall back to sequential execution automatically.

**`return_exceptions=True` + explicit isinstance check is safer than bare `gather()`.** When gathering coroutines that should propagate exceptions, `return_exceptions=True` prevents one failing branch from silently cancelling the other. Checking `isinstance(result, BaseException)` and re-raising makes the intent explicit and avoids swallowing exceptions.

**Score normalization belongs in the service layer, not the API layer.** Normalizing RRF scores to [0,1] inside `reciprocal_rank_fusion()` ensures that all three search modes (vector, FTS, hybrid) return comparable scores. If normalization were deferred to the API response serializer, workflow callers consuming raw `ChunkSearchResult` lists would see raw scores and the inconsistency would be harder to discover.

**Separate DB fixtures for extension-dependent tests.** Tests that need sqlite-vec require a fixture that loads the extension before applying the schema. The two-fixture pattern (`db_connection` / `db_with_vec`) is clean and scales to future extension-dependent tests.

### Documentation Impact

- `docs/developer/python-backend/architecture.md` — the parallel hybrid search pattern (secondary connection + WAL) and the aiosqlite per-connection serialization caveat should be documented; the previous update only noted the serialization constraint without documenting the secondary-connection solution
- `docs/developer/python-backend/architecture.md` — `configure_connection` usage on secondary connections should be called out so future services know to apply it
- No new docs files needed; the existing architecture doc covers the service pattern adequately
