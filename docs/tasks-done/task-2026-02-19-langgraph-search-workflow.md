# Task: Implement LangGraph Search Workflow

## Summary

Create `workflows/search.py` implementing the LangGraph search graph that orchestrates the search pipeline: embed query -> vector search -> FTS search -> fuse results -> enrich with item data -> return. This follows the established workflow pattern from `workflows/processing.py` and the Adaptive Search design in `docs/developer/ai/workflows.md`.

## Acceptance Criteria

- [x] `python-backend/src/workflows/utils.py` created with generic `log_node_execution` and `route_or_error` (extracted from `processing.py`) - Implemented in `utils.py:31-74`
- [x] `python-backend/src/workflows/processing.py` updated to import `log_node_execution` and `route_or_error` from `utils.py` - `processing.py:39`
- [x] `python-backend/src/workflows/search.py` created with LangGraph `StateGraph` implementation - `search.py:1-239`
- [x] `SearchState` TypedDict defined with fields: `query`, `search_type`, `limit`, `query_embedding`, `vector_results`, `fts_results`, `fused_results`, `final_results`, `error`, `error_step` - `search.py:18-37`
- [x] Workflow nodes: `embed_query`, `vector_search`, `fts_search`, `fuse_results`, `enrich_results`, `handle_error` - `search.py:54-141`
- [x] `embed_query` node generates query embedding via `EmbeddingService.embed_query()` - `search.py:54-63`
- [x] `vector_search` node calls `SearchService.vector_search()` with `query_embedding=state.get("query_embedding")` to avoid re-embedding - `search.py:66-80`
- [x] `fts_search` node calls `SearchService.fts_search()` - `search.py:83-96`
- [x] `fuse_results` node calls `reciprocal_rank_fusion()` for hybrid, or passes through the available result list for single-mode search, then caps results to `limit` - `search.py:99-117`
- [x] `enrich_results` node calls `SearchService.enrich_results()` to add item metadata - `search.py:120-131`
- [x] `handle_error` node logs failure context and leaves existing `error` / `error_step` unchanged in state - `search.py:134-141`
- [x] Conditional routing from `START` using `route_after_entry`; all nodes route to `handle_error` when `state["error"]` is set, including `enrich_results -> route_or_error(END)` - `search.py:177-215`
- [x] For `search_type="vector"`, skip `fts_search`; for `search_type="fts"`, skip `embed_query` and `vector_search` - `search.py:144-161`
- [x] `build_search_graph()` factory function returns a typed `CompiledStateGraph[SearchState, ...]` (matching the `processing.py` pattern) - `search.py:164-220`
- [x] Compiled graph exposes `async def search(query: str, search_type: SearchType, limit: int) -> SearchState` - `search.py:226-238`
- [x] Node execution logging via `log_node_execution` decorator imported from `workflows/utils.py` - `search.py:13,54,66,83,99,120,134`
- [x] All `builder.add_node()` calls use `cast(Any, node_func)` to satisfy mypy - `search.py:170-175`
- [x] `python-backend/src/workflows/__init__.py` exports search workflow symbols without `graph` name collision (for example: `processing_graph`, `search_graph`) - `__init__.py:1-20`
- [x] Ruff and mypy pass - Verified: all linting, formatting, and type checks pass

## Dependencies

- Task 1: Search models (`ChunkSearchResult`, `SearchResultItem`) — from `src.db`
- Task 2: `SearchService` with vector, FTS, and enrich methods — from `src.services`
- Phase 2: `EmbeddingService.embed_query()`, `OllamaProvider`, `db_connection()`
- Phase 2: `workflows/processing.py` for established patterns (`log_node_execution`, `route_or_error`)

Note: `SearchError` is in `src.exceptions`, not `src.db`. Use `from src.exceptions import SearchError` in `try/except` blocks if catching it explicitly.

## Technical Notes

### Imports

```python
from typing import Any, cast
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.db import ChunkSearchResult, SearchResultItem, SearchType, db_connection
from src.exceptions import SearchError
from src.providers import OllamaProvider
from src.services import EmbeddingService, SearchService
from src.services.search import reciprocal_rank_fusion  # not re-exported from src.services
from src.workflows.utils import log_node_execution, route_or_error
```

> **Why `from src.services.search import reciprocal_rank_fusion` directly?** `reciprocal_rank_fusion` is a module-level function in `services/search.py` and is not re-exported from `src/services/__init__.py`. `SearchService` and `EmbeddingService` can come from `from src.services import ...`.

> **Why not use `SearchService.hybrid_search()`?** `hybrid_search()` exists and internally parallelizes vector and FTS searches via separate DB connections. The multi-node workflow is used instead to enable per-step error routing and LangGraph state visibility. This trades some performance for observability, which is acceptable for the MVP.

### SearchState

```python
class SearchState(TypedDict, total=False):
    # Input
    query: str
    search_type: SearchType
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

### Shared Utilities (`workflows/utils.py`) — **Required**

`log_node_execution` and `route_or_error` in `processing.py` are typed to `ProcessingState`. Reusing them with `SearchState` would cause mypy errors. They must be extracted to `workflows/utils.py` with a generic state type so both workflows can import them.

```python
# workflows/utils.py
from typing import Any, TypeVar
from collections.abc import Awaitable, Callable

StateT = TypeVar("StateT")
NodeFunc = Callable[[Any], Awaitable[dict]]

def log_node_execution(node_name: str) -> Callable[[NodeFunc], NodeFunc]:
    ...

def route_or_error(next_node: str) -> Callable[[Any], str]:
    ...
```

Update `processing.py` to import from `utils.py` after extraction.

### Graph Structure (MVP)

The MVP search workflow is a simplified version of the Adaptive Search from `docs/developer/ai/workflows.md`. It skips the Analyze, Decompose, and Expand nodes (those are explicitly out of scope per the MVP plan).

```
hybrid:  embed_query → vector_search → fts_search → fuse_results → enrich_results → END
vector:  embed_query → vector_search → fuse_results → enrich_results → END
fts:     fts_search → fuse_results → enrich_results → END
```

### Routing Functions

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

### Graph Builder

```python
def build_search_graph() -> CompiledStateGraph[SearchState, None, SearchState, SearchState]:
    builder = StateGraph(SearchState)

    builder.add_node("embed_query", cast(Any, embed_query_node))
    builder.add_node("vector_search", cast(Any, vector_search_node))
    builder.add_node("fts_search", cast(Any, fts_search_node))
    builder.add_node("fuse_results", cast(Any, fuse_results_node))
    builder.add_node("enrich_results", cast(Any, enrich_results_node))
    builder.add_node("handle_error", cast(Any, handle_error_node))

    # Entry: branch from START based on search_type
    builder.add_conditional_edges(
        START,
        route_after_entry,
        {"embed_query": "embed_query", "fts_search": "fts_search"},
    )

    builder.add_conditional_edges(
        "embed_query",
        route_or_error("vector_search"),
        {"vector_search": "vector_search", "handle_error": "handle_error"},
    )
    builder.add_conditional_edges(
        "vector_search",
        route_after_vector,
        {
            "fts_search": "fts_search",
            "fuse_results": "fuse_results",
            "handle_error": "handle_error",
        },
    )
    builder.add_conditional_edges(
        "fts_search",
        route_or_error("fuse_results"),
        {"fuse_results": "fuse_results", "handle_error": "handle_error"},
    )
    builder.add_conditional_edges(
        "fuse_results",
        route_or_error("enrich_results"),
        {"enrich_results": "enrich_results", "handle_error": "handle_error"},
    )
    builder.add_conditional_edges(
        "enrich_results",
        route_or_error(END),
        {END: END, "handle_error": "handle_error"},
    )
    builder.add_edge("handle_error", END)

    return cast(
        CompiledStateGraph[SearchState, None, SearchState, SearchState],
        builder.compile(),
    )

graph = build_search_graph()
```

> **`cast(Any, ...)`**: LangGraph's `add_node` type signature does not align with typed `TypedDict` state. `cast(Any, node_func)` silences the mypy error — this is the same approach used throughout `processing.py`.

### Node Implementations

Each node follows the established pattern from `processing.py`. All use `cast(Any, ...)` in `add_node` and return `dict`.

**`embed_query_node`**

```python
@log_node_execution("embed_query")
async def embed_query_node(state: SearchState) -> dict:
    try:
        async with db_connection() as db:
            provider = OllamaProvider()
            embedding_service = EmbeddingService(provider=provider)
            # db is passed for model-consistency validation, not for data retrieval
            embedding = await embedding_service.embed_query(state["query"], db)
        return {"query_embedding": embedding}
    except Exception as e:
        return {"error": str(e), "error_step": "embed_query"}
```

**`vector_search_node`**

```python
@log_node_execution("vector_search")
async def vector_search_node(state: SearchState) -> dict:
    try:
        async with db_connection() as db:
            provider = OllamaProvider()
            embedding_service = EmbeddingService(provider=provider)
            search_service = SearchService(embedding_service=embedding_service)
            results = await search_service.vector_search(
                state["query"],
                db,
                limit=state.get("limit", 20),
                query_embedding=state.get("query_embedding"),  # reuse pre-computed embedding
            )
        return {"vector_results": results}
    except Exception as e:
        return {"error": str(e), "error_step": "vector_search"}
```

**`fts_search_node`**

```python
@log_node_execution("fts_search")
async def fts_search_node(state: SearchState) -> dict:
    try:
        async with db_connection() as db:
            provider = OllamaProvider()
            embedding_service = EmbeddingService(provider=provider)
            search_service = SearchService(embedding_service=embedding_service)
            results = await search_service.fts_search(
                state["query"], db, limit=state.get("limit", 20)
            )
        return {"fts_results": results}
    except Exception as e:
        return {"error": str(e), "error_step": "fts_search"}
```

**`fuse_results_node`**

```python
@log_node_execution("fuse_results")
async def fuse_results_node(state: SearchState) -> dict:
    try:
        limit = state.get("limit", 20)
        search_type = state.get("search_type", "hybrid")
        vector_results = state.get("vector_results", [])
        fts_results = state.get("fts_results", [])

        if search_type == "hybrid":
            fused = reciprocal_rank_fusion(vector_results, fts_results)[:limit]
        elif search_type == "vector":
            fused = vector_results[:limit]
        else:  # fts
            fused = fts_results[:limit]

        return {"fused_results": fused}
    except Exception as e:
        return {"error": str(e), "error_step": "fuse_results"}
```

**`enrich_results_node`**

```python
@log_node_execution("enrich_results")
async def enrich_results_node(state: SearchState) -> dict:
    try:
        async with db_connection() as db:
            results = await SearchService.enrich_results(
                state.get("fused_results", []),
                db,
            )
        return {"final_results": results}
    except Exception as e:
        return {"error": str(e), "error_step": "enrich_results"}
```

**`handle_error_node`**

```python
@log_node_execution("handle_error")
async def handle_error_node(state: SearchState) -> dict:
    logger.error(
        f"Search failed at step '{state.get('error_step')}': {state.get('error')}",
        extra={"query": state.get("query")},
    )
    return {}  # Error is already in state
```

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
    search_type: SearchType = "hybrid",
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
    return cast(SearchState, result)
```

## Files to Create/Modify

**Create:**

- `python-backend/src/workflows/utils.py` — Generic `log_node_execution` and `route_or_error` (extracted from `processing.py`) — **required for mypy compliance**
- `python-backend/src/workflows/search.py`

**Modify:**

- `python-backend/src/workflows/__init__.py` — Export `search`, `SearchState`, and avoid `graph` export-name collisions (for example `processing_graph`, `search_graph`)
- `python-backend/src/workflows/processing.py` — Update imports to use `workflows/utils.py` after extraction

## Verification

```bash
bun run python:lint
bun run python:fmt:check
bun run python:typecheck
```

---

## Implementation Details

_Tracked: 2026-02-19_

### Files Changed

| File                                            | Change   | Description                                                                                                                                                      |
| ----------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `python-backend/src/workflows/utils.py`         | Created  | Generic `log_node_execution` decorator and `route_or_error` router extracted from processing.py, parameterized with `Mapping[str, Any]` for cross-workflow reuse |
| `python-backend/src/workflows/search.py`        | Created  | LangGraph `StateGraph` search workflow with 6 nodes (embed_query, vector_search, fts_search, fuse_results, enrich_results, handle_error) and conditional routing |
| `python-backend/src/workflows/processing.py`    | Modified | Removed inline `log_node_execution` and `route_or_error`, replaced with imports from `workflows/utils.py`                                                        |
| `python-backend/src/workflows/__init__.py`      | Modified | Added `SearchState`, `search`, `search_graph` exports; renamed `graph` imports to `processing_graph`/`search_graph` to avoid collision                           |
| `python-backend/tests/workflows/test_search.py` | Created  | 17 tests covering routing helpers, fuse_results logic, integration flows (hybrid/vector/fts), error routing, and import smoke test                               |

### Dependencies Added

None — all dependencies (`langgraph`, service layer, DB models) were already present from Tasks 1-2 and Phase 2.

---

## Learning Report

_Generated: 2026-02-19_

### Summary

Implemented the LangGraph search workflow (`workflows/search.py`) that orchestrates the full search pipeline: query embedding, vector search, full-text search, result fusion via reciprocal rank fusion, and result enrichment with item metadata. The workflow supports three search modes (hybrid, vector, FTS) with conditional routing that skips unnecessary nodes per mode. Also extracted shared workflow utilities (`log_node_execution`, `route_or_error`) into `workflows/utils.py` for cross-workflow reuse.

- **Files changed:** 5 (2 created, 2 modified, 1 test file created)
- **Tests:** 17 (7 routing unit tests, 3 fuse_results unit tests, 6 integration tests, 1 import smoke test)
- **All quality gates pass:** ruff lint, ruff format, mypy

### Patterns & Decisions

1. **Followed `processing.py` patterns exactly:** Node structure (`@log_node_execution` decorator, try/except returning error dict), `cast(Any, ...)` for `add_node` mypy compliance, `build_*_graph()` factory function, module-level `graph = build_*_graph()` compilation, and top-level `async def search()` entry point all mirror the established processing workflow.

2. **Generic utility extraction (`utils.py`):** The original `log_node_execution` and `route_or_error` were typed to `ProcessingState`. These were generalized to accept `Mapping[str, Any]` and a `NodeFuncT` TypeVar, enabling both `ProcessingState` and `SearchState` to use them without mypy errors. The `_build_log_context` helper extracts common log fields (`item_id`, `query`) from any state mapping.

3. **Service factory helpers (`_create_embedding_service`, `_create_search_service`):** Small private helpers reduce repeated `OllamaProvider()` + `EmbeddingService(provider=...)` boilerplate across nodes. This is a minor deviation from the task spec (which showed inline construction) but keeps nodes focused on their core logic.

4. **`route_after_entry` includes error check:** The spec's `route_after_entry` didn't check for errors, but the implementation adds an error guard for robustness — if somehow the initial state has an error, it routes directly to `handle_error`.

5. **Graph export naming:** Used `from ... import graph as processing_graph` / `search_graph` aliasing pattern in `__init__.py` to avoid name collisions while keeping module-level `graph` variables unchanged in each workflow file.

### Challenges & Solutions

1. **TypeVar for generic node decorator:** The `log_node_execution` decorator needed to preserve the exact callable signature of the wrapped function. Used `NodeFuncT = TypeVar("NodeFuncT", bound=Callable[[Any], Awaitable[Any]])` with `cast(NodeFuncT, wrapper)` to satisfy mypy while maintaining flexibility.

2. **State typing with `Mapping` vs `TypedDict`:** LangGraph passes state as a dict-like object at runtime. Using `Mapping[str, Any]` for the router and log utilities avoids coupling them to a specific TypedDict, while the node functions themselves use the concrete `SearchState` type for IDE support.

3. **`enrich_results` as static method call:** The spec showed `SearchService.enrich_results()` as a direct static/classmethod call (no instance needed). The implementation follows this exactly — no `SearchService` instance is created for enrichment.

### Lessons Learned

1. **Task specs with full code snippets accelerate implementation significantly.** The detailed node implementations, routing functions, and graph builder in the task spec meant minimal design decisions during coding — the task was primarily translation and minor polish.

2. **Cross-workflow utility extraction should happen early.** Extracting `log_node_execution` and `route_or_error` before building the search workflow prevented duplicating ProcessingState-coupled code. Future workflows will benefit from this shared foundation.

3. **Comprehensive test organization works well with the three-tier approach:** Routing unit tests (fast, no mocking), node-level unit tests (mock dependencies), and integration tests (mock services, run full graph) provide good coverage at different abstraction levels.

### Documentation Impact

- `docs/developer/ai/workflows.md` — May need an update to document the search workflow graph structure alongside the existing processing workflow documentation.
- The shared `workflows/utils.py` module is a new pattern worth documenting for future workflow authors.
