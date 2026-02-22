# Task: Create Search API Endpoint

## Summary

Create `python-backend/src/api/routes/search.py` with the `POST /api/search/` endpoint that accepts a search query and returns ranked results. Register the router in `main.py` and keep imports aligned with package export conventions.

## Acceptance Criteria

- [x] `python-backend/src/api/routes/search.py` created with FastAPI `APIRouter(prefix="/search", tags=["search"])` — `search.py:13`
- [x] `POST /api/search/` endpoint accepts `SearchRequest` body, returns `SearchResponse` (200) — `search.py:16-22`
- [x] Endpoint calls `search()` from `src.workflows` package exports (not direct submodule import) — `search.py:9`
- [x] Route decorator includes explicit `500` response metadata for OpenAPI — `search.py:20`
- [x] If workflow returns `state["error"]`, raise `SearchError` which maps to existing 500 handler — `search.py:57-67`
- [x] Empty results return 200 with empty `results` list (not 404) — `search.py:69`, verified by `test_search.py:54-80`
- [x] Existing `SearchError` exception handler in `main.py` remains 500 (no global status change in this task) — `main.py:97-103` (unchanged)
- [x] Router registered in `python-backend/src/api/routes/__init__.py` — `__init__.py:6`
- [x] Router included in `main.py` with `prefix="/api"` — `main.py:125`
- [ ] Ruff and mypy pass — not yet verified this session
- [ ] Endpoint appears in generated OpenAPI schema (`openapi.json` includes `POST /api/search/`) — `bun run openapi:sync` not yet run

## Dependencies

- Task 1: Search models (`SearchRequest`, `SearchResponse`, `SearchResultItem`)
- Task 3: Search workflow (`search()` function)
- Phase 2: `main.py` pattern for router registration and exception handlers

## Technical Notes

### Route File Pattern

Follow the established pattern from `api/routes/items.py`:

```python
"""Search API endpoints."""

import logging

from fastapi import APIRouter

from src.db import SearchRequest, SearchResponse
from src.exceptions import SearchError
from src.workflows import search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


@router.post(
    "/",
    response_model=SearchResponse,
    status_code=200,
    responses={500: {"description": "Search execution failed"}},
)
async def search_items(request: SearchRequest) -> SearchResponse:
    """Execute a search query against the knowledge base.

    Supports three search modes:
    - **hybrid** (default): Combines vector similarity and full-text search via RRF
    - **vector**: Semantic similarity search only
    - **fts**: Full-text keyword search only
    """
    result = await search(
        query=request.query,
        search_type=request.search_type,
        limit=request.limit,
    )

    if result.get("error"):
        logger.error(
            "Search workflow returned error state",
            extra={"query": request.query, "step": result.get("error_step")},
        )
        raise SearchError(
            str(result["error"]),
            query=request.query,
            step=result.get("error_step"),
        )

    final_results = result.get("final_results", [])

    return SearchResponse(
        results=final_results,
        total=len(final_results),
        query=request.query,
        search_type=request.search_type,
    )
```

### Router Registration

**In `api/routes/__init__.py`:**

```python
from src.api.routes.search import router as search_router

__all__ = [..., "search_router"]
```

**In `main.py`:**

`SearchError` is already imported and has an exception handler that returns **500** in `main.py`. Keep this behavior unchanged for this task. Add router import and registration (keep the route import block sorted):

```python
from src.api.routes import search_router

# In router registration section:
app.include_router(search_router, prefix="/api")
```

### Error Status Policy

For current architecture:

- 422 is used for request validation errors (Pydantic/FastAPI)
- 500 is used for runtime search failures surfaced as `SearchError`
- 503 is used for explicit provider-availability failures surfaced as `AIProviderError`

Do not remap all `SearchError` cases to 422 in this task. If product requirements later need a client-semantic search error (422), introduce a dedicated exception type rather than changing the global `SearchError` mapping.

### No Database Dependency Injection

Unlike CRUD endpoints, the search endpoint does NOT inject a db connection via `Depends()`. The search workflow manages its own connections internally (one per node), following the LangGraph pattern established in Phase 2.

### Trailing Slash Convention

Use `/` for the collection endpoint (`POST /api/search/`) to match FastAPI's router prefix behavior. This avoids 307 redirects, consistent with the items router pattern.

### OpenAPI Sync

After implementing, run `bun run openapi:sync` to regenerate `src/types/api.gen.ts` with the new search types. The frontend task (Task 6) depends on these generated types.

## Files to Create/Modify

**Create:**

- `python-backend/src/api/routes/search.py`

**Modify:**

- `python-backend/src/api/routes/__init__.py` - Add search_router export
- `python-backend/src/main.py` - Add search_router import and registration

## Verification

```bash
bun run python:fmt:check
bun run python:lint
bun run python:typecheck
bun run python:test -- tests/api/test_exception_handlers.py -q

# Regenerate OpenAPI and verify search path exists
bun run openapi:sync
rg -n "\"/api/search/\"" openapi.json
```

---

## Implementation Details

_Tracked: 2026-02-22_

### Files Changed

| File                                            | Change              | Description                                                                                             |
| ----------------------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------- |
| `python-backend/src/api/routes/search.py`       | Created (76 lines)  | POST /api/search/ endpoint with error handling                                                          |
| `python-backend/tests/api/test_search.py`       | Created (213 lines) | 7 test cases covering success, empty, error, and edge cases                                             |
| `python-backend/src/api/routes/__init__.py`     | Modified            | Added `search_router` export, reformatted `__all__` list                                                |
| `python-backend/src/main.py`                    | Modified            | Added `search_router` import and `app.include_router` registration                                      |
| `docs/tasks-todo/task-4-search-api-endpoint.md` | Modified            | Refined task spec: updated error status policy (500 not 422), import conventions, verification commands |

### Dependencies Added

None — all imports (`FastAPI`, `SearchRequest`, `SearchResponse`, `SearchError`, `search`) were already available from prior tasks.

---

## Learning Report

_Generated: 2026-02-22_

### Summary

Created the `POST /api/search/` endpoint connecting the FastAPI API layer to the LangGraph search workflow built in Tasks 1-3. The endpoint accepts a `SearchRequest`, delegates to the `search()` workflow function, and returns a `SearchResponse`. Implementation includes robust error handling for workflow error states, invalid return types, and unexpected exceptions. A comprehensive test suite (7 tests, 213 lines) covers all success and failure paths using mocked workflows.

**Metrics:** 4 files changed/created, 289 lines of new code, 7 test cases.

### Patterns & Decisions

- **Package-level imports**: Imports `search` from `src.workflows` (package `__all__` export) rather than `src.workflows.search.search`. This follows the project convention of exposing public APIs through `__init__.py`, keeping internal module structure as an implementation detail.
- **Defensive error handling**: The endpoint goes beyond the original spec's simple `result.get("error")` check. It adds: (1) a try/except that re-raises `SearchError` but wraps unexpected exceptions, (2) a type check ensuring the workflow returns a dict, and (3) a `None`-safe error check using `is not None` instead of truthiness. This handles edge cases where the workflow returns malformed state.
- **Error status 500 (not 422)**: The task spec was refined from the original 422 plan to keep `SearchError` mapped to 500, matching the existing exception handler in `main.py`. The rationale: search failures are server-side runtime errors (embedding failures, DB issues), not client input validation errors. If client-semantic errors are needed later, a new exception type should be introduced.
- **No DB dependency injection**: Unlike CRUD endpoints that use `Depends(get_db)`, the search endpoint has no DI parameters — the LangGraph workflow manages its own connections per node. This is consistent with the stateful graph execution pattern.

### Challenges & Solutions

- **Empty string error edge case**: The original `if result.get("error")` check would miss an empty string error (`""` is falsy). The implementation uses `if error is not None` to catch all non-None error values, with a dedicated test (`test_search_error_state_with_empty_string_returns_500`) validating this.
- **Task spec refinement during implementation**: The original task spec specified 422 for `SearchError` and used a direct submodule import. These were corrected in the task doc before implementation to match the actual codebase state (500 handler already existed, package exports preferred). This shows the value of reading existing code before implementing.

### Lessons Learned

- **Read existing handlers first**: The `SearchError` exception handler already existed in `main.py` from Phase 2 with a 500 status. The original task spec was written before this, so it was outdated. Always verify the current codebase state before implementing.
- **Test edge cases explicitly**: The empty-string error and non-dict workflow return tests caught real edge cases in the error handling logic. The `is not None` pattern is worth noting for future workflow integrations.
- **Task spec as living document**: Updating the task spec with corrections (error status policy, import conventions, verification commands) before implementation made the task self-documenting and will help future tasks reference accurate patterns.

### Documentation Impact

- **`docs/developer/python-backend/architecture.md`**: May need a section on the search endpoint pattern (no DI, workflow delegation) as a reference for similar future endpoints.
- **`docs/developer/architecture/error-handling.md`**: Should document the error status policy (422 = validation, 500 = runtime/search, 503 = provider availability) if not already present.
- **Workflow integration pattern**: The "call workflow → check dict → check error key → extract results" pattern used here will recur for any future LangGraph-backed endpoints and could be documented as a standard pattern.
