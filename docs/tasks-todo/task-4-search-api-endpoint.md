# Task: Create Search API Endpoint

## Summary

Create `api/routes/search.py` with the `POST /api/search` endpoint that accepts a search query and returns ranked results. Register the router in `main.py` and add a `SearchError` exception handler.

## Acceptance Criteria

- [ ] `python-backend/src/api/routes/search.py` created with FastAPI `APIRouter(prefix="/search", tags=["search"])`
- [ ] `POST /api/search/` endpoint accepts `SearchRequest` body, returns `SearchResponse` (200)
- [ ] Endpoint calls `workflows.search.search()` to execute the search
- [ ] If workflow returns `state["error"]`, raise `SearchError` which maps to 422
- [ ] Empty results return 200 with empty `results` list (not 404)
- [ ] `SearchError` exception handler registered in `main.py` returning 422 with `{"error": error_code, "message": str(exc)}`
- [ ] Router registered in `python-backend/src/api/routes/__init__.py`
- [ ] Router included in `main.py` with `prefix="/api"`
- [ ] Ruff and mypy pass
- [ ] Endpoint returns correct OpenAPI schema (visible at `/docs`)

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
from src.workflows.search import search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/", response_model=SearchResponse, status_code=200)
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
        raise SearchError(
            f"Search failed: {result['error']}",
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

```python
from src.api.routes import search_router

# In exception handlers section:
@app.exception_handler(SearchError)
async def search_error_handler(request: Request, exc: SearchError):
    """Handle SearchError with 422 response."""
    return JSONResponse(
        status_code=422,
        content={"error": exc.error_code, "message": str(exc)},
    )

# In router registration section:
app.include_router(search_router, prefix="/api")
```

### Why 422 for SearchError

422 (Unprocessable Entity) is appropriate because the request format is valid but the search operation couldn't be completed (e.g., embedding generation failed, malformed FTS query). This distinguishes from:

- 400: malformed request body (handled by Pydantic validation)
- 500: unexpected server error
- 503: AI provider unavailable (handled by existing `AIProviderError` handler)

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
- `python-backend/src/main.py` - Add SearchError import, exception handler, router registration

## Verification

```bash
cd python-backend
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/

# Start server and verify endpoint appears in OpenAPI docs
uv run uvicorn src.main:app --reload
# Visit http://127.0.0.1:8742/docs and check POST /api/search/

# From project root, regenerate frontend types
bun run openapi:sync
```
