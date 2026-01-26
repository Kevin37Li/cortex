# Task: Implement Embedding Management Service

## Summary

Create an embedding management service that generates vector embeddings for text chunks, stores them in sqlite-vec, enforces model consistency (preventing mixed embeddings from different models), and tracks embedding metadata. This service bridges the AI provider layer and the database layer.

## Acceptance Criteria

- [ ] `services/embeddings.py` created with `EmbeddingService` class
- [ ] `embed_chunks(item_id: str, chunks: list[ChunkResult]) -> list[str]` — Generates embeddings for chunks, stores in DB, returns chunk IDs
- [ ] `embed_query(query: str) -> list[float]` — Generates embedding for a search query
- [ ] Batch embedding: processes chunks in configurable batch sizes (default 32)
- [ ] Stores embeddings in `vec_chunks` virtual table via `ChunkRepository`
- [ ] Creates `chunks` table entries via `ChunkRepository.create_many()`
- [ ] Model consistency check: reads current embedding model from DB metadata, raises `EmbeddingModelMismatchError` if a different model is configured
- [ ] Tracks embedding model name in chunk metadata (stored in chunks table or a dedicated metadata row)
- [ ] Handles provider errors gracefully: wraps `AIProviderError` into `EmbeddingError` with item context

## Dependencies

- Phase 1 complete: `AIProvider.embed()`, `AIProvider.embed_batch()`, `OllamaProvider`, `ChunkRepository`, sqlite-vec table
- Task 1: `EmbeddingError`, `EmbeddingModelMismatchError` exception types
- Task 4: `ChunkResult` model from chunking service

## Technical Notes

- Per `docs/developer/ai/embeddings.md`: never mix embeddings from different models in the same database
- `nomic-embed-text` produces 768-dim vectors; `text-embedding-3-small` produces 1536-dim vectors
- The `vec_chunks` table is created programmatically in `database.py` with `FLOAT[768]` — dimension must match model
- Batch size of 32 is a good default; Ollama processes sequentially but OpenAI supports true batching
- Use the `AIProvider` interface (injected), not `OllamaProvider` directly
- The existing `ChunkRepository.create_many()` handles chunk table inserts; this service adds the vec_chunks inserts

## Embedding Model Tracking

```python
# Store in a settings/metadata table or in each chunk's metadata
# Simplest approach for MVP: store in app settings
async def _get_active_embedding_model(self, db: Connection) -> str | None:
    """Get the embedding model currently used in the database."""
    row = await db.execute_fetchone(
        "SELECT value FROM app_metadata WHERE key = 'embedding_model'"
    )
    return row["value"] if row else None

async def _set_active_embedding_model(self, db: Connection, model: str) -> None:
    """Record the embedding model used in the database."""
    await db.execute(
        "INSERT OR REPLACE INTO app_metadata (key, value) VALUES ('embedding_model', ?)",
        [model],
    )
```

Note: This may require adding an `app_metadata` table to `schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS app_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

## Files to Create/Modify

**Create:**

- `python-backend/src/services/embeddings.py` — Embedding management service

**Modify:**

- `python-backend/src/db/schema.sql` — Add `app_metadata` table (if using metadata approach)
- `python-backend/src/api/deps.py` — Add `get_embedding_service()` dependency if needed

## Verification

```bash
cd python-backend
uv run pytest -v  # Existing tests still pass
uv run ruff check src/
uv run mypy src/
```
