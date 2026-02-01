# Task: Implement Embedding Management Service

## Summary

Create an embedding management service that generates vector embeddings for text chunks, stores them in sqlite-vec, enforces model consistency (preventing mixed embeddings from different models), and tracks embedding metadata. This service bridges the AI provider layer and the database layer.

## Acceptance Criteria

- [ ] `services/embeddings.py` created with `EmbeddingService` class
- [ ] `embed_chunks(chunks: list[Chunk]) -> None` — Generates embeddings for chunks (already persisted with IDs), stores in `vec_chunks`
- [ ] `embed_query(query: str) -> list[float]` — Generates embedding for a search query
- [ ] Batch embedding: processes chunks in configurable batch sizes (default 32)
- [ ] Stores embeddings in `vec_chunks` virtual table using `sqlite_vec.serialize_float32()` for serialization
- [ ] Model consistency check: reads current embedding model from DB metadata, raises `EmbeddingModelMismatchError` if a different model is configured
- [ ] Dimension validation: validates embedding dimensions match `EMBEDDING_DIMENSION` (768); raises `EmbeddingModelMismatchError` if dimensions differ
- [ ] Tracks embedding model name via `app_metadata` table
- [ ] Handles provider errors gracefully: wraps `AIProviderError` into `EmbeddingError` with context (using `from e` to preserve original)
- [ ] Uses `logging.getLogger(__name__)` for operation logging (DEBUG level for operations, ERROR for failures)
- [ ] Unit tests in `tests/services/test_embeddings.py` with mocked `AIProvider`

## Dependencies

- Phase 1 complete: `AIProvider.embed()`, `AIProvider.embed_batch()`, `OllamaProvider`, `ChunkRepository`, sqlite-vec table
- Task 1: `EmbeddingError`, `EmbeddingModelMismatchError` exception types (already exist in `exceptions.py`)
- Task 4: `ChunkResult` model from chunking service, `Chunk` model from `db/models.py`

## Workflow Integration

**Important ordering:** Chunks must be created in the database BEFORE embedding:

1. Chunking service produces `list[ChunkResult]` (no IDs yet)
2. `ChunkRepository.create_many()` persists chunks, returns `list[Chunk]` (with IDs)
3. `EmbeddingService.embed_chunks(chunks)` generates and stores embeddings using chunk IDs

This ordering is handled by the LangGraph workflow in Task 7.

## Technical Notes

- Per `docs/developer/ai/embeddings.md`: never mix embeddings from different models in the same database
- `nomic-embed-text` produces 768-dim vectors; `text-embedding-3-small` produces 1536-dim vectors
- The `vec_chunks` table is created programmatically in `database.py` with `FLOAT[768]` — dimension must match model
- Batch size of 32 is a good default; Ollama processes sequentially but OpenAI supports true batching
- Use the `AIProvider` interface (injected via constructor), not `OllamaProvider` directly
- **sqlite_vec serialization:** Import `sqlite_vec` and use `sqlite_vec.serialize_float32(embedding)` before INSERT into `vec_chunks`
- For batch vec_chunks insertion: iterate and insert each chunk_id/embedding pair, then commit once

## AIProvider Injection

Inject `AIProvider` via constructor. Add dependency factory in `deps.py`:

```python
# In deps.py
async def get_ai_provider() -> AIProvider:
    """Get the configured AI provider."""
    # For MVP, return OllamaProvider; later can switch based on settings
    return get_ollama_provider()

async def get_embedding_service(
    provider: AIProvider = Depends(get_ai_provider),
) -> EmbeddingService:
    """Get embedding service with injected provider."""
    return EmbeddingService(provider=provider)
```

## Embedding Model Tracking

Use a simple `AppMetadataRepository` for consistency with the repository pattern:

```python
# In db/repositories/app_metadata.py
class AppMetadataRepository:
    """Repository for app-wide metadata key-value storage."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        """Initialize with a database connection."""
        self.db = db

    async def get(self, key: str) -> str | None:
        cursor = await self.db.execute(
            "SELECT value FROM app_metadata WHERE key = ?", [key]
        )
        row = await cursor.fetchone()
        return row["value"] if row else None

    async def set(self, key: str, value: str) -> None:
        # Note: Does not commit - caller controls transaction
        await self.db.execute(
            "INSERT OR REPLACE INTO app_metadata (key, value) VALUES (?, ?)",
            [key, value],
        )
```

Then in `EmbeddingService`, check model consistency before embedding and record
the model only after successful embedding (atomically with the commit):

```python
EMBEDDING_MODEL_KEY = "embedding_model"

async def _check_model_consistency(
    self, metadata_repo: AppMetadataRepository
) -> bool:
    """Check configured model matches DB. Returns True if model needs recording."""
    stored_model = await metadata_repo.get(EMBEDDING_MODEL_KEY)
    if stored_model is None:
        return True  # First use - record after successful embedding
    elif stored_model != self._model_name:
        raise EmbeddingModelMismatchError(
            f"Database uses '{stored_model}' but '{self._model_name}' is configured. "
            "Cannot mix embeddings from different models."
        )
    return False

# In embed_chunks, after storing all embeddings but before commit:
if should_record_model:
    await metadata_repo.set(EMBEDDING_MODEL_KEY, self._model_name)
await db.commit()  # Atomic: embeddings + model recording
```

This requires adding an `app_metadata` table to `schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS app_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

## Files to Create/Modify

**Create:**

- `python-backend/src/services/embeddings.py` — Embedding management service
- `python-backend/src/db/repositories/app_metadata.py` — Simple key-value metadata repository
- `python-backend/tests/services/test_embeddings.py` — Unit tests with mocked provider

**Modify:**

- `python-backend/src/db/schema.sql` — Add `app_metadata` table
- `python-backend/src/api/deps.py` — Add `get_ai_provider()` and `get_embedding_service()` dependencies
- `python-backend/src/db/repositories/__init__.py` — Export `AppMetadataRepository`

## Verification

```bash
cd python-backend
uv run pytest tests/services/test_embeddings.py -v  # New tests pass
uv run pytest -v  # All tests still pass
uv run ruff check src/
uv run mypy src/
```

---

## Implementation Details

_Tracked: 2026-02-01_

### Files Changed

| File | Change | Description |
|------|--------|-------------|
| `python-backend/src/services/embeddings.py` | Created | EmbeddingService class with `embed_chunks()` and `embed_query()` methods |
| `python-backend/src/db/repositories/app_metadata.py` | Created | AppMetadataRepository for key-value metadata storage |
| `python-backend/tests/services/test_embeddings.py` | Created | 20 unit tests covering all acceptance criteria |
| `python-backend/src/db/schema.sql` | Modified | Added `app_metadata` table for embedding model tracking |
| `python-backend/src/api/deps.py` | Modified | Added `get_ai_provider()` and `get_embedding_service()` dependency factories |
| `python-backend/src/db/repositories/__init__.py` | Modified | Exported `AppMetadataRepository` |
| `python-backend/src/services/__init__.py` | Modified | Exported `EmbeddingService` |

### Dependencies Added

None - all required dependencies were already present from Phase 1.

### Acceptance Criteria Status

- [x] `services/embeddings.py` created with `EmbeddingService` class — `embeddings.py:25`
- [x] `embed_chunks(chunks: list[Chunk]) -> None` — Generates embeddings for chunks, stores in `vec_chunks` — `embeddings.py:52-129`
- [x] `embed_query(query: str) -> list[float]` — Generates embedding for a search query — `embeddings.py:131-179`
- [x] Batch embedding: processes chunks in configurable batch sizes (default 32) — `embeddings.py:82-103`
- [x] Stores embeddings in `vec_chunks` virtual table using `sqlite_vec.serialize_float32()` — `embeddings.py:99`
- [x] Model consistency check: reads current embedding model from DB metadata, raises `EmbeddingModelMismatchError` — `embeddings.py:181-213`
- [x] Dimension validation: validates embedding dimensions match `EMBEDDING_DIMENSION` (768) — `embeddings.py:215-229`
- [x] Tracks embedding model name via `app_metadata` table — `embeddings.py:107-109`, `schema.sql:57-60`
- [x] Handles provider errors gracefully: wraps `AIProviderError` into `EmbeddingError` with `from e` — `embeddings.py:114-121`, `embeddings.py:166-171`
- [x] Uses `logging.getLogger(__name__)` for operation logging — `embeddings.py:19`, used throughout
- [x] Unit tests in `tests/services/test_embeddings.py` with mocked `AIProvider` — 20 tests, all passing

---

## Learning Report

_Generated: 2026-02-01_

### Summary

Implemented a complete embedding management service that bridges the AI provider layer and database layer. The service handles vector embedding generation, storage in sqlite-vec, and enforces strict model consistency to prevent mixing embeddings from different models.

**Key metrics:**
- 3 new files created, 4 files modified
- 230 lines of production code in `EmbeddingService`
- 432 lines of test code with 20 unit tests
- All 164 project tests pass

### Patterns & Decisions

1. **Database connection as method parameter (not constructor)**
   - The `EmbeddingService` receives the database connection via method parameters (`embed_chunks(db, chunks)`) rather than constructor injection
   - This allows the same service instance to work with different connections and supports transaction management by the caller
   - The service creates its own `AppMetadataRepository` instance internally with the passed connection

2. **Deferred model recording pattern**
   - Model name is checked before embedding but recorded only after successful storage
   - This ensures atomicity: if embedding fails, we don't record a model that wasn't actually used
   - The `_check_model_consistency()` method returns a boolean flag indicating if the model should be recorded on success

3. **Batch-then-iterate storage**
   - Embeddings are generated in batches via `embed_batch()` for efficiency
   - But stored one-by-one in a loop with a single commit at the end
   - This is necessary because sqlite-vec doesn't support bulk inserts to virtual tables

4. **Optional model consistency check for queries**
   - `embed_query()` accepts an optional `db` parameter
   - When provided, performs model consistency check to ensure search uses same model as stored embeddings
   - When omitted, skips the check (useful for standalone embedding generation)

5. **Exception chaining with `from e`**
   - All `AIProviderError` exceptions are wrapped in `EmbeddingError` using `from e` to preserve the original traceback
   - This follows the existing pattern in `exceptions.py` and aids debugging

### Challenges & Solutions

1. **Transaction rollback on partial failure**
   - Challenge: If embedding fails mid-batch, partial inserts would remain in vec_chunks
   - Solution: Wrap the entire operation in try/except with explicit `await db.rollback()` on error before re-raising

2. **Testing sqlite-vec virtual tables**
   - Challenge: Tests needed a real sqlite-vec table, not a mock
   - Solution: Created `db_with_vec` fixture that loads the sqlite-vec extension and creates the `vec_chunks` virtual table with the correct schema
   - The fixture uses `_apply_schema()` to get all regular tables, then manually creates the vec_chunks table

3. **AsyncIterator return type for FastAPI dependencies**
   - Challenge: Initial implementation used `async def get_ai_provider() -> AIProvider` but FastAPI Depends with generators requires AsyncIterator
   - Solution: Changed all dependency functions to use `AsyncIterator[T]` return type with `yield` for consistency with existing patterns

### Lessons Learned

1. **Task spec quality matters**
   - The task spec provided excellent code snippets that could be adapted directly
   - Having the `_check_model_consistency()` pattern pre-specified saved significant design time
   - The "Workflow Integration" section clarified the service's role in the larger pipeline

2. **sqlite-vec serialization is mandatory**
   - Must use `sqlite_vec.serialize_float32()` before INSERT
   - Cannot insert raw Python lists into FLOAT[] columns
   - The docs/developer/ai/embeddings.md referenced this but the task spec made it explicit

3. **Test fixtures can be complex**
   - Real database tests with sqlite-vec require significant fixture setup
   - The `db_with_vec` fixture demonstrates how to properly initialize the extension and tables

### Documentation Impact

1. **`docs/developer/ai/embeddings.md`** - May need update to reference the new `EmbeddingService` and its usage patterns

2. **`docs/developer/python-backend/architecture.md`** - Could document the service layer's dependency injection pattern (passing db to methods vs constructor)

3. **New pattern documentation candidate**: The "deferred recording" pattern (check before, record after) could be documented as a best practice for atomic metadata tracking
