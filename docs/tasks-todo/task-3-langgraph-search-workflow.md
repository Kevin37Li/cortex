# Task: Implement LangGraph Search Workflow

## Summary

Create `workflows/search.py` implementing the LangGraph search graph that orchestrates the search pipeline: embed query -> vector search -> FTS search -> fuse results -> enrich with item data -> return. This follows the established workflow pattern from `workflows/processing.py` and the Adaptive Search design in `docs/developer/ai/workflows.md`.

## Acceptance Criteria

- [ ] `python-backend/src/workflows/search.py` created with LangGraph `StateGraph` implementation
- [ ] `SearchState` TypedDict defined with fields: `query`, `search_type`, `limit`, `query_embedding`, `vector_results`, `fts_results`, `fused_results`, `final_results`, `error`, `error_step`
- [ ] Workflow nodes: `embed_query`, `vector_search`, `fts_search`, `fuse_results`, `enrich_results`, `handle_error`
- [ ] `embed_query` node generates query embedding via `EmbeddingService.embed_query()`
- [ ] `vector_search` node calls `SearchService.vector_search()`
- [ ] `fts_search` node calls `SearchService.fts_search()`
- [ ] `fuse_results` node calls `reciprocal_rank_fusion()` for hybrid, or passes through for single-mode search
- [ ] `enrich_results` node calls `SearchService.enrich_results()` to add item metadata
- [ ] `handle_error` node captures error details in state
- [ ] Conditional routing: all nodes route to `handle_error` when `state["error"]` is set (use `route_or_error` pattern from processing workflow)
- [ ] For `search_type="vector"`, skip `fts_search`; for `search_type="fts"`, skip `embed_query` and `vector_search`
- [ ] Compiled graph exposes `async def search(query: str, search_type: str, limit: int) -> SearchState`
- [ ] Node execution logging via `log_node_execution` decorator (reuse from processing workflow or extract shared utility)
- [ ] Workflow and `search()` function exported from `python-backend/src/workflows/__init__.py`
- [ ] Ruff and mypy pass

## Dependencies

- Task 1: Search models (`ChunkSearchResult`, `SearchResultItem`, `SearchError`)
- Task 2: `SearchService` with vector, FTS, hybrid, and enrich methods
- Phase 2: `EmbeddingService.embed_query()`, `OllamaProvider`, `db_connection()`
- Phase 2: `workflows/processing.py` for established patterns (`log_node_execution`, `route_or_error`)

## Technical Notes

### SearchState

```python
class SearchState(TypedDict, total=False):
    # Input
    query: str
    search_type: str  # "hybrid", "vector", "fts"
    limit: int

    # Intermediate
    query_embedding: list[float]
    vector_results: list[ChunkSearchResult]
    fts_results: list[ChunkSearchResult]
    fused_results: list[ChunkSearchResult]

    # Output
    final_results: list[SearchResultItem]

    # Error handling
    error: str | None
    error_step: str | None
```

### Graph Structure (MVP)

The MVP search workflow is a simplified version of the Adaptive Search from `docs/developer/ai/workflows.md`. It skips the Analyze, Decompose, and Expand nodes (those are explicitly out of scope per the MVP plan).

```
hybrid:  embed_query → vector_search → fts_search → fuse_results → enrich_results → END
vector:  embed_query → vector_search → fuse_results → enrich_results → END
fts:     fts_search → fuse_results → enrich_results → END
```

Use conditional edges to implement search-type routing:

```python
def route_after_entry(state: SearchState) -> str:
    """Route based on search_type."""
    search_type = state.get("search_type", "hybrid")
    if search_type == "fts":
        return "fts_search"
    return "embed_query"  # vector and hybrid both need embeddings

def route_after_vector(state: SearchState) -> str:
    """After vector search, decide if FTS is needed."""
    if state.get("error"):
        return "handle_error"
    search_type = state.get("search_type", "hybrid")
    if search_type == "hybrid":
        return "fts_search"
    return "fuse_results"  # vector-only skips FTS
```

### Node Implementations

Each node follows the established pattern from `processing.py`:

```python
@log_node_execution("embed_query")
async def embed_query_node(state: SearchState) -> dict:
    try:
        async with db_connection() as db:
            provider = OllamaProvider()
            embedding_service = EmbeddingService(provider=provider)
            embedding = await embedding_service.embed_query(state["query"], db)
        return {"query_embedding": embedding}
    except Exception as e:
        return {"error": str(e), "error_step": "embed_query"}
```

### Shared Utilities

The `log_node_execution` decorator and `route_or_error` factory are currently defined in `workflows/processing.py`. If they are general enough, consider extracting them to `workflows/utils.py`. Otherwise, redefine them locally in `search.py`. Prefer extraction to avoid duplication.

### Database Connection Pattern

Workflow nodes manage their own connections per `docs/developer/ai/workflows.md`:

```python
async with db_connection() as db:
    # All DB operations within this node
```

### Entry Point Function

```python
async def search(
    query: str,
    search_type: str = "hybrid",
    limit: int = 20,
) -> SearchState:
    """Execute search and return results.

    Args:
        query: The search query text
        search_type: "hybrid", "vector", or "fts"
        limit: Maximum number of results

    Returns:
        SearchState with final_results populated (or error set)
    """
    initial_state: SearchState = {
        "query": query,
        "search_type": search_type,
        "limit": limit,
    }
    result = await graph.ainvoke(initial_state)
    return result
```

### Error Handling

The `handle_error` node simply preserves the error in state. The API layer reads `state["error"]` to decide the HTTP response:

```python
@log_node_execution("handle_error")
async def handle_error_node(state: SearchState) -> dict:
    logger.error(
        f"Search failed at step '{state.get('error_step')}': {state.get('error')}",
        extra={"query": state.get("query")},
    )
    return {}  # Error is already in state
```

## Files to Create/Modify

**Create:**

- `python-backend/src/workflows/search.py`

**Possibly create (if extracting shared utils):**

- `python-backend/src/workflows/utils.py` - Shared `log_node_execution`, `route_or_error`

**Modify:**

- `python-backend/src/workflows/__init__.py` - Export `search`, `SearchState`
- `python-backend/src/workflows/processing.py` - If extracting utils, update imports

## Verification

```bash
cd python-backend
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/
```
