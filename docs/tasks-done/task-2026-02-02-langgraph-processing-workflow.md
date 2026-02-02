# Task: Implement LangGraph Content Processing Workflow

## Summary

Create the main content processing workflow using LangGraph that orchestrates the full pipeline: classify content type → parse → chunk → extract metadata → validate → persist (chunks + embeddings + metadata) → complete. This is the core AI pipeline that transforms raw saved content into searchable, connected knowledge.

## Acceptance Criteria

- [x] `workflows/processing.py` created with LangGraph `StateGraph` implementation
- [x] `ProcessingState` TypedDict with all workflow state fields (using `total=False` for optional fields)
- [x] Workflow nodes: `classify`, `parse`, `chunk`, `extract_metadata`, `validate`, `persist`, `complete`, `handle_error`
- [x] Conditional edge: `validate` routes to `persist` (if valid) or back to `chunk` retry (if invalid, max 3 retries)
- [x] `classify` node fetches item via `ItemRepository.get()`, sets `processing_status` via `update_status()`, determines content type
- [x] `parse` node calls `ContentParser` for HTML/text extraction, updates `title` from parsed content if available
- [x] `chunk` node calls `ChunkingService` for semantic splitting
- [x] `extract_metadata` node calls `MetadataExtractor` for summary/concepts/entities
- [x] `validate` node checks that chunks were created and metadata was extracted
- [x] `persist` node persists chunks via `ChunkRepository.create_many()`, then embeddings via `EmbeddingService.embed_chunks()`, then metadata to item
- [x] `complete` node updates item `processing_status` to `'completed'` via `update_status()`
- [x] `handle_error` node sets item `processing_status` to `'failed'` and merges error into item metadata
- [x] All nodes wrapped with try/except that sets `state["error"]` and routes to `handle_error` on failure
- [x] Node execution logging via `log_node_execution` decorator for observability
- [x] Compiled graph exposes `async def process_item(item_id: str) -> ProcessingState`

## Dependencies

- Task 1: Processing error types
- Task 3: Content parsing service (`ContentParser`)
- Task 4: Semantic chunking service (`ChunkingService`)
- Task 5: Embedding management service (`EmbeddingService`)
- Task 6: Metadata extraction service (`MetadataExtractor`)
- Phase 1: `ItemRepository`, `ChunkRepository`, `AIProvider`

## Technical Notes

- Per `docs/developer/ai/workflows.md`: follow the Content Processing workflow design
- Use `langgraph` package — **must be added to `pyproject.toml`**
- The workflow receives an `item_id`, fetches the item from DB, processes it, and updates the DB
- Item `processing_status` transitions: `pending` → `processing` → `completed` or `failed`
- On validation failure, retry up to 3 times (increment `retry_count` in state)
- **Note**: The "Connect" step (connection discovery) is out of scope for this task; will be Phase 3

### Content Type Values

Use the values defined in the database schema (`python-backend/src/db/schema.sql:9`):

- `webpage` — HTML content from URLs
- `note` — Plain text notes
- `file` — Uploaded files

**Do not use** `html`, `text` — these will cause parsing issues.

### Database Connection Pattern

Refactor to use a single context manager as the base, eliminating the redundant generator wrapper.

**1. Modify `python-backend/src/db/database.py`:**

```python
from contextlib import asynccontextmanager

async def _configure_connection(db: aiosqlite.Connection) -> None:
    """Shared connection setup (PRAGMA, extensions, row factory)."""
    await db.execute("PRAGMA foreign_keys = ON")
    await _load_sqlite_vec(db)
    db.row_factory = aiosqlite.Row


@asynccontextmanager
async def db_connection() -> AsyncIterator[aiosqlite.Connection]:
    """Context manager for database connections.

    Use directly for LangGraph nodes, scripts, background tasks.
    For FastAPI routes, use get_db_connection() from api.deps.
    """
    async with aiosqlite.connect(settings.db_path) as db:
        await _configure_connection(db)
        yield db


# DELETE get_connection() - it's now redundant
```

**2. Modify `python-backend/src/api/deps.py`:**

```python
from ..db.database import db_connection

async def get_db_connection() -> AsyncIterator[aiosqlite.Connection]:
    """Async generator for FastAPI Depends()."""
    async with db_connection() as db:
        yield db
```

**3. Update any other usages of `get_connection()`** to use either:

- `db_connection()` directly (for non-FastAPI code)
- `get_db_connection()` via Depends (for FastAPI routes)

Usage:

- **FastAPI routes**: `Depends(get_db_connection)`
- **Workflow nodes**: `async with db_connection() as db: ...`

### AIProvider Instantiation

`EmbeddingService` and `MetadataExtractor` both require an `AIProvider` instance (`python-backend/src/services/embeddings.py:35`, `python-backend/src/services/extraction.py:41`).

Create the provider in `classify` node and store in state:

```python
from src.providers import OllamaProvider

async def classify_node(state: ProcessingState) -> dict:
    provider = OllamaProvider()  # Or use settings to select provider
    # ... rest of classify logic
    return {"ai_provider": provider, ...}
```

### Status Updates

Use `ItemRepository.update_status()` for processing status changes (`python-backend/src/db/repositories/items.py:226`), **not** `update()`:

```python
await item_repo.update_status(state["item_id"], "processing")
```

### Persistence Strategy (Critical)

**Persist AFTER validation passes** to avoid duplicate data on retries:

1. `chunk` → produces `chunk_results` (in-memory)
2. `extract_metadata` → produces `metadata` (in-memory)
3. `validate` → checks both exist and are valid
4. `persist` → only if validation passes:
   - Persist chunks via `ChunkRepository.create_many()`
   - Store embeddings via `EmbeddingService.embed_chunks()`
   - Merge metadata into item via `ItemRepository.update()` (merge, don't replace)

This prevents orphaned chunks/embeddings when retries occur.

### Error Handling

Every node should catch exceptions and route to `handle_error`:

```python
@log_node_execution("parse")
async def parse_node(state: ProcessingState) -> dict:
    try:
        parser = ContentParser()
        result = parser.parse(state["raw_content"], state["content_type"])
        return {"parsed_text": result.text, "title": result.title or state["title"]}
    except Exception as e:
        return {"error": str(e), "error_step": "parse"}
```

Add conditional edge from each node to `handle_error` when `state["error"]` is set.

`handle_error` node should:

1. Log the full exception with technical details
2. Update item `processing_status` to `'failed'` via `update_status()`
3. **Merge** error into item's `metadata` (don't overwrite existing metadata):
   ```python
   existing_metadata = item.metadata or {}
   existing_metadata["processing_error"] = state["error"]
   existing_metadata["error_step"] = state.get("error_step")
   await item_repo.update(item_id, ItemUpdate(metadata=existing_metadata))
   ```

### Observability

Implement node execution logging per `docs/developer/ai/workflows.md`:

```python
def log_node_execution(node_name: str):
    def decorator(func):
        async def wrapper(state: ProcessingState) -> dict:
            logger.info(f"Starting node: {node_name}", extra={"item_id": state["item_id"]})
            try:
                result = await func(state)
                logger.info(f"Completed node: {node_name}", extra={"item_id": state["item_id"]})
                return result
            except Exception as e:
                logger.error(f"Failed node: {node_name}", extra={"item_id": state["item_id"], "error": str(e)})
                raise
        return wrapper
    return decorator
```

## ProcessingState

```python
from typing import TypedDict, NotRequired
from src.db.models import Chunk, ExtractedMetadata, ChunkResult
from src.providers import AIProvider

class ProcessingState(TypedDict, total=False):
    # Required - set at entry
    item_id: str

    # Set by classify
    raw_content: str
    content_type: str  # 'webpage', 'note', 'file' (match schema values!)
    title: str
    source_url: str | None
    ai_provider: AIProvider

    # Set by parse
    parsed_text: str

    # Set by chunk
    chunk_results: list[ChunkResult]  # In-memory before persistence

    # Set by extract_metadata
    metadata: ExtractedMetadata

    # Set by persist
    chunks: list[Chunk]  # After persistence, with IDs
    embeddings_stored: bool

    # Control flow
    validation_passed: bool
    retry_count: int
    error: str | None
    error_step: str | None
```

**Note:** Using `total=False` allows fields to be absent until their node runs.

## Graph Structure

```python
from langgraph.graph import StateGraph, END

builder = StateGraph(ProcessingState)

# Add nodes
builder.add_node("classify", classify_node)
builder.add_node("parse", parse_node)
builder.add_node("chunk", chunk_node)
builder.add_node("extract_metadata", extract_metadata_node)
builder.add_node("validate", validate_node)
builder.add_node("persist", persist_node)  # Chunks + embeddings + metadata
builder.add_node("complete", complete_node)
builder.add_node("handle_error", handle_error_node)

# Add edges with error routing
builder.set_entry_point("classify")

def route_or_error(next_node: str):
    """Route to next node or handle_error if error is set."""
    def router(state: ProcessingState) -> str:
        if state.get("error"):
            return "handle_error"
        return next_node
    return router

builder.add_conditional_edges("classify", route_or_error("parse"), {"parse": "parse", "handle_error": "handle_error"})
builder.add_conditional_edges("parse", route_or_error("chunk"), {"chunk": "chunk", "handle_error": "handle_error"})
builder.add_conditional_edges("chunk", route_or_error("extract_metadata"), {"extract_metadata": "extract_metadata", "handle_error": "handle_error"})
builder.add_conditional_edges("extract_metadata", route_or_error("validate"), {"validate": "validate", "handle_error": "handle_error"})

# Validate routes to persist, retry, or fail
def route_after_validation(state: ProcessingState) -> str:
    if state.get("error"):
        return "handle_error"
    if state.get("validation_passed"):
        return "persist"
    if state.get("retry_count", 0) < 3:
        return "retry"
    return "handle_error"

builder.add_conditional_edges(
    "validate",
    route_after_validation,
    {"persist": "persist", "retry": "chunk", "handle_error": "handle_error"}
)

builder.add_conditional_edges("persist", route_or_error("complete"), {"complete": "complete", "handle_error": "handle_error"})
builder.add_edge("complete", END)
builder.add_edge("handle_error", END)

graph = builder.compile()
```

## Node Implementation Notes

### `classify` node

- Fetch item from DB via `ItemRepository.get(item_id)` (not `get_by_id`)
- Update item `processing_status` to `'processing'` via `update_status()`
- Create `AIProvider` instance (e.g., `OllamaProvider()`)
- Determine content type from item data (should already be set on item)

### `parse` node

- Call `ContentParser.parse()` which routes based on content type
- Update `state["title"]` from `ParsedContent.title` if extracted title is better

### `chunk` node

- Call `ChunkingService.chunk_text()` with parsed text
- Store results in `chunk_results` (not persisted yet)

### `extract_metadata` node

- Call `MetadataExtractor.extract()` with `state["ai_provider"]`
- Store results in `metadata` (not persisted yet)

### `validate` node

- Check `chunk_results` is non-empty
- Check `metadata` has required fields (summary, concepts)
- Set `validation_passed` accordingly
- Increment `retry_count` if validation fails

### `persist` node

- Convert `ChunkResult` list to `ChunkCreate` models
- Call `ChunkRepository.create_many()` to persist chunks
- Call `EmbeddingService.embed_chunks(db, chunks)` with persisted chunks
- Merge extracted metadata into item's existing metadata
- Update item via `ItemRepository.update()`

### `complete` node

- Update item `processing_status` to `'completed'` via `update_status()`

### `handle_error` node

- Update item `processing_status` to `'failed'` via `update_status()`
- Merge error info into item metadata (preserve existing metadata)

## Files to Create/Modify

**Create:**

- `python-backend/src/workflows/__init__.py` — Module init
- `python-backend/src/workflows/processing.py` — LangGraph processing workflow

**Modify:**

- `python-backend/pyproject.toml` — Add `langgraph` dependency

## Verification

```bash
cd python-backend
uv sync
uv run ruff check src/
uv run mypy src/

# Integration test (requires Ollama running):
uv run python -c "
import asyncio
from src.workflows.processing import process_item

async def test():
    # Assumes an item exists in the database
    result = await process_item('test-item-id')
    print(f'Status: {result.get(\"error\") or \"success\"}')
    print(f'Chunks: {len(result.get(\"chunks\", []))}')
    print(f'Embeddings stored: {result.get(\"embeddings_stored\", False)}')

asyncio.run(test())
"
```

## Future Considerations (Phase 3+)

- **Connection Discovery**: The "Connect" step from `docs/developer/ai/workflows.md:36` is deferred to Phase 3
- **Checkpointing**: For bulk import scenarios, consider adding LangGraph checkpointing to resume failed workflows

---

## Implementation Details

_Tracked: 2026-02-02_

### Files Changed

| File                                                 | Change   | Description                                                                                 |
| ---------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------- |
| `python-backend/src/workflows/processing.py`         | Created  | LangGraph StateGraph workflow with all 8 nodes, conditional routing, validation retry loop  |
| `python-backend/src/workflows/__init__.py`           | Modified | Export `ProcessingState`, `graph`, and `process_item`                                       |
| `python-backend/pyproject.toml`                      | Modified | Added `langgraph>=0.2.0` dependency                                                         |
| `python-backend/src/db/database.py`                  | Modified | Refactored to `db_connection()` context manager pattern per task spec                       |
| `python-backend/src/api/deps.py`                     | Modified | Updated to use `db_connection()`, added singleton repo getters                              |
| `python-backend/src/db/repositories/base.py`         | Modified | Made stateless - db connection passed via method params, removed `__init__`                 |
| `python-backend/src/db/repositories/items.py`        | Modified | Stateless pattern, all methods take `db` param, no auto-commit                              |
| `python-backend/src/db/repositories/chunks.py`       | Modified | Stateless pattern, all methods take `db` param, no auto-commit                              |
| `python-backend/src/db/repositories/app_metadata.py` | Modified | Stateless pattern, all methods take `db` param                                              |
| `python-backend/src/db/repositories/__init__.py`     | Modified | Export module-level singleton instances (`item_repo`, `chunk_repo`, `metadata_repo`)        |
| `python-backend/src/services/embeddings.py`          | Modified | Uses singleton `metadata_repo`, removed auto-commit/rollback (caller controls transactions) |
| `python-backend/src/api/items.py`                    | Modified | Updated to use new db/repo pattern, explicit commits at route level                         |
| `python-backend/src/db/__init__.py`                  | Modified | Export `db_connection`                                                                      |
| `python-backend/tests/test_repositories.py`          | Modified | Updated to stateless repo pattern with explicit db params                                   |
| `python-backend/tests/services/test_embeddings.py`   | Modified | Updated for stateless repo pattern                                                          |
| `python-backend/uv.lock`                             | Modified | Lock file updated with langgraph and its dependencies                                       |

### Dependencies Added

- `langgraph>=0.2.0` - LangGraph for state machine workflow orchestration

### Acceptance Criteria Status

- [x] `workflows/processing.py` created with LangGraph `StateGraph` implementation - `processing.py:363-421`
- [x] `ProcessingState` TypedDict with all workflow state fields (using `total=False`) - `processing.py:36-69`
- [x] Workflow nodes: `classify`, `parse`, `chunk`, `extract_metadata`, `validate`, `persist`, `complete`, `handle_error` - `processing.py:99-331`
- [x] Conditional edge: `validate` routes to `persist` (if valid) or back to `chunk` retry (if invalid, max 3 retries) - `processing.py:345-360`, `403-407`
- [x] `classify` node fetches item via `ItemRepository.get()`, sets `processing_status` via `update_status()`, determines content type - `processing.py:99-129`
- [x] `parse` node calls `ContentParser` for HTML/text extraction, updates `title` from parsed content - `processing.py:132-144`
- [x] `chunk` node calls `ChunkingService` for semantic splitting - `processing.py:147-156`
- [x] `extract_metadata` node calls `MetadataExtractor` for summary/concepts/entities - `processing.py:159-173`
- [x] `validate` node checks that chunks were created and metadata was extracted - `processing.py:176-221`
- [x] `persist` node persists chunks via `ChunkRepository.create_many()`, then embeddings, then metadata to item - `processing.py:224-279`
- [x] `complete` node updates item `processing_status` to `'completed'` via `update_status()` - `processing.py:282-295`
- [x] `handle_error` node sets item `processing_status` to `'failed'` and merges error into item metadata - `processing.py:298-331`
- [x] All nodes wrapped with try/except that sets `state["error"]` and routes to `handle_error` - Each node has try/except block
- [x] Node execution logging via `log_node_execution` decorator - `processing.py:72-96`
- [x] Compiled graph exposes `async def process_item(item_id: str) -> ProcessingState` - `processing.py:428-441`

---

## Learning Report

_Generated: 2026-02-02_

### Summary

Implemented the core LangGraph content processing workflow that orchestrates the full AI pipeline: classify → parse → chunk → extract_metadata → validate → persist → complete. This required a significant architectural refactor of the repository layer to support proper transaction boundaries, making repositories stateless with explicit database connection parameters.

**Key metrics:**

- 1 file created (442 lines): `processing.py`
- 14 files modified across database, API, and test layers
- 1 new dependency: `langgraph>=0.2.0`
- All 15 acceptance criteria met

### Patterns & Decisions

**1. Stateless Repository Pattern**

The implementation required refactoring all repositories from stateful (connection in `__init__`) to stateless (connection passed per method). This enables:

- LangGraph nodes to manage their own connections via `async with db_connection()`
- FastAPI routes to continue using dependency injection
- Proper transaction boundaries where the caller controls when to commit

```python
# Before: Stateful - repository owns the connection
repo = ItemRepository(db_connection)
await repo.create(data)

# After: Stateless - caller owns the connection
item_repo = ItemRepository()  # Singleton
await item_repo.create(db, data)  # db passed explicitly
await db.commit()  # Caller controls transaction
```

**2. Module-Level Singleton Repositories**

Created singleton instances (`item_repo`, `chunk_repo`, `metadata_repo`) exported from `repositories/__init__.py`. This allows both workflow nodes and FastAPI routes to share the same stateless instances.

**3. Single Atomic Commit in Persist Node**

The `persist` node performs three database operations (create chunks, store embeddings, update item metadata) but commits only once at the end. This ensures all-or-nothing semantics - if any step fails, no partial data is persisted.

**4. Validation Retry Loop**

The validate node increments `retry_count` on failure and routes back to `chunk` for retry (up to 3 times). The error is only set when max retries are exceeded, preventing premature routing to `handle_error`.

**5. Error Routing Pattern**

Used a `route_or_error()` factory function to create conditional edges that check for `state["error"]`. This keeps the graph definition DRY while ensuring every node can route to `handle_error`.

### Challenges & Solutions

**1. Transaction Boundary Management**

**Challenge:** The original repository pattern auto-committed after each operation, which doesn't work for workflows needing atomic multi-step transactions.

**Solution:** Removed all `await db.commit()` calls from repository methods and documented that callers are responsible for committing. This required updating all API routes to explicitly commit after successful operations.

**2. Embedding Service Rollback Handling**

**Challenge:** The `EmbeddingService.embed_chunks()` method was calling `db.rollback()` on errors, which would conflict with the caller's transaction management.

**Solution:** Removed rollback calls from the service. The service no longer manages transactions - if an error occurs, it raises an exception and the caller decides how to handle the transaction (rollback or let the context manager handle cleanup).

**3. FastAPI Dependency Injection Compatibility**

**Challenge:** Needed to maintain FastAPI's dependency injection pattern while supporting the new stateless repo approach.

**Solution:** Created `get_item_repo()` and `get_chunk_repo()` dependency functions that return the singleton instances. Routes inject both the db connection and the repo, then pass db to repo methods.

### Lessons Learned

**1. Plan Repository Architecture Early**

The task spec correctly identified the need for a db connection refactor. Having this documented upfront made the implementation straightforward, even though it touched many files.

**2. Stateless Services Scale Better**

The stateless pattern with explicit connection passing is more flexible than connection-in-constructor. It naturally supports:

- Multiple connections (e.g., read replicas)
- Connection pooling
- Workflow engines that manage their own connections

**3. LangGraph State Updates Are Merges**

LangGraph automatically merges node return values into state (not replaces). This is why nodes can return partial updates like `{"parsed_text": result.text}` without losing other state fields.

### Documentation Impact

**Potentially outdated docs:**

- `docs/developer/python-backend/architecture.md` - Repository pattern section should be updated to reflect stateless approach
- Any examples showing `ItemRepository(db)` constructor pattern need updating

**New patterns to document:**

- Stateless repository pattern with explicit db parameter
- Module-level singleton repo instances
- LangGraph workflow node patterns (error handling, logging decorator)
- Transaction boundary management (caller commits, not service/repo)

**Documentation that was helpful:**

- Task spec's "Database Connection Pattern" section was excellent - followed almost verbatim
- `docs/developer/ai/workflows.md` guided the node structure and logging pattern
