# Task: Define Search Pydantic Models and Error Types

## Summary

Add the Pydantic request/response models and exception types needed by the search system. This establishes the data contracts used by the search service, LangGraph workflow, API endpoint, and frontend.

## Acceptance Criteria

- [x] `SearchRequest` model added to `python-backend/src/db/models.py` with fields: `query` (str), `limit` (int, default 20, ge=1, le=100), `search_type` (Literal["hybrid", "vector", "fts"], default "hybrid"), and `model_config = {"extra": "forbid"}`
- [x] `SearchRequest` rejects blank/whitespace-only queries (after trim)
- [x] `SearchResultItem` model added with fields: `item_id` (str), `item_title` (str), `content_type` (ContentType), `chunk_id` (str), `chunk_content` (str), `score` (float, ge=0.0, le=1.0), `rank` (int, ge=1)
- [x] `SearchResponse` model added with fields: `results` (list[SearchResultItem]), `total` (int), `query` (str), `search_type` (SearchType)
- [x] `SearchError` exception added to `python-backend/src/exceptions.py` extending `CortexError` with `error_code = "search_error"` and keyword args `query: str | None`, `step: str | None`
- [x] `SearchType`, `SearchRequest`, `SearchResultItem`, `SearchResponse`, and `ChunkSearchResult` added to both the import block and `__all__` in `python-backend/src/db/__init__.py`
- [x] `SearchError` importable from `src.exceptions` and covered by exception tests
- [x] `SearchType` Literal type alias defined for reuse: `SearchType = Literal["hybrid", "vector", "fts"]`
- [x] `SearchError` added to parametrized error code test and basic instantiation/inheritance tests in `python-backend/tests/core/test_exceptions.py`
- [x] `python-backend/tests/db/test_search_models.py` added with validation tests for bounds, enum values, forbidden extra fields, and whitespace query rejection
- [x] Search request/response example in `docs/developer/python-backend/architecture.md` updated to match actual field names (`item_title`, `chunk_content`, `search_type`, no `took_ms`)
- [x] Python quality checks pass via bun scripts (`python:fmt:check`, `python:lint`, `python:typecheck`, `python:test`)

## Dependencies

- Phase 2 complete: `models.py` and `exceptions.py` exist with established patterns

## Technical Notes

### Model Placement

Add all search models in `python-backend/src/db/models.py` after the existing "Response models" section. Group them under a `# Search models` comment.

### SearchRequest

```python
SearchType = Literal["hybrid", "vector", "fts"]

class SearchRequest(BaseModel):
    """Request body for POST /api/search."""
    model_config = {"extra": "forbid"}

    query: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=20, ge=1, le=100)
    search_type: SearchType = "hybrid"
```

Add a validator to reject whitespace-only input:

```python
from pydantic import field_validator

@field_validator("query")
@classmethod
def validate_query_not_blank(cls, value: str) -> str:
    if not value.strip():
        raise ValueError("Query must not be blank")
    return value
```

### SearchResultItem

This model carries enough item info to render a result card in the frontend without a follow-up query:

```python
class SearchResultItem(BaseModel):
    """A single search result with item context."""
    item_id: str
    item_title: str
    content_type: ContentType
    chunk_id: str
    chunk_content: str  # The matching chunk text (serves as snippet)
    score: float = Field(ge=0.0, le=1.0)  # Normalized relevance score
    rank: int = Field(ge=1)  # 1-based position in results
```

### SearchResponse

```python
class SearchResponse(BaseModel):
    """Response body for POST /api/search."""
    results: list[SearchResultItem]
    total: int
    query: str
    search_type: SearchType
```

### SearchError

Follow the established pattern in `exceptions.py` (see `ProcessingError` at line 92):

```python
class SearchError(CortexError):
    """Raised when search operations fail."""
    error_code: str = "search_error"

    def __init__(
        self,
        message: str,
        *,
        query: str | None = None,
        step: str | None = None,
    ) -> None:
        self.query = query
        self.step = step
        super().__init__(message)
```

### Internal Search Result (for service layer)

Also define a lightweight internal model used between service methods before enrichment with item data:

```python
class ChunkSearchResult(BaseModel):
    """Internal: raw search hit before item enrichment."""
    chunk_id: str
    item_id: str
    content: str
    score: float
```

This is used by `SearchService` internally and converted to `SearchResultItem` when enriching with item title/content_type.

### Architecture Doc Note

As part of this task, align the search API example in `docs/developer/python-backend/architecture.md` with the actual contracts (`item_title`, `chunk_content`, `total`, `query`, `search_type`). The `took_ms` field is omitted for MVP and can be added later as `took_ms: int | None = None`.

### What This Task Does NOT Cover

- FastAPI exception handler registration for `SearchError` — covered by Task 4 (search API endpoint)
- `openapi:sync` — not needed until the endpoint references these models (Task 4)
- Search service/workflow/endpoint integration tests — covered by Task 5

## Files to Modify

- `python-backend/src/db/models.py` - Add SearchType, SearchRequest, SearchResultItem, SearchResponse, ChunkSearchResult
- `python-backend/src/db/__init__.py` - Add SearchType, SearchRequest, SearchResultItem, SearchResponse, ChunkSearchResult to import block and `__all__`
- `python-backend/src/exceptions.py` - Add SearchError
- `python-backend/tests/core/test_exceptions.py` - Add SearchError to parametrized error code test + instantiation/inheritance tests
- `python-backend/tests/db/test_search_models.py` - Add model validation tests for SearchRequest/SearchResultItem/SearchResponse/ChunkSearchResult
- `docs/developer/python-backend/architecture.md` - Update search request/response example fields to match the new models

## Verification

```bash
bun run python:fmt:check
bun run python:lint
bun run python:typecheck
bun run python:test -- tests/core/test_exceptions.py tests/db/test_search_models.py -x
```

---

## Implementation Details

_Tracked: 2026-02-17_

### Files Changed

| File                                                      | Change   | Description                                                                                         |
| --------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------- |
| `python-backend/src/db/models.py`                         | Modified | Added `SearchType`, `SearchRequest`, `SearchResultItem`, `SearchResponse`, and `ChunkSearchResult`. |
| `python-backend/src/db/__init__.py`                       | Modified | Exported search models/types through package imports and `__all__`.                                 |
| `python-backend/src/exceptions.py`                        | Modified | Added `SearchError` with `query` and `step` context fields.                                         |
| `python-backend/tests/core/test_exceptions.py`            | Modified | Extended error-code coverage and added `SearchError` behavior/inheritance tests.                    |
| `python-backend/tests/db/test_search_models.py`           | Created  | Added validation coverage for search request/response models and internal chunk result model.       |
| `docs/developer/python-backend/architecture.md`           | Modified | Aligned search request/response docs with implemented model field names.                            |
| `docs/developer/architecture/error-handling.md`           | Modified | Updated Python exception guidance with `SearchError` and contextual fields.                         |
| `docs/tasks-todo/task-1-search-models-and-error-types.md` | Modified | Marked acceptance criteria complete and recorded task completion notes.                             |

### Dependencies Added

- None.

### Verification Run

- `bun run python:fmt:check` (pass)
- `bun run python:lint` (pass)
- `bun run python:typecheck` (pass)
- `bun run python:test -- tests/core/test_exceptions.py tests/db/test_search_models.py -x` (pass, 80 tests)

---

## Learning Report

_Generated: 2026-02-17_

### Summary

Implemented the search model contract and search-specific exception layer with strict validation and explicit test coverage, then aligned backend developer documentation to the final API shape.

### Patterns and Decisions

- Defined a reusable `SearchType` literal alias and reused it across request/response models to keep contract consistency.
- Used `model_config = {"extra": "forbid"}` on `SearchRequest` to reject unknown fields early.
- Normalized query input with a `mode="before"` validator so trimming occurs before `Field` constraints, preserving max-length correctness on padded input.
- Kept `ChunkSearchResult.score` intentionally unbounded for raw backend relevance scores and tested normalization responsibility at the enrichment boundary.
- Followed existing exception hierarchy conventions by introducing `SearchError` as a `CortexError` subtype with optional context metadata.

### Challenges and Solutions

- Challenge: Whitespace-only queries can pass naive `min_length` checks.
- Solution: Added explicit trim-and-reject validation plus tests for blank, whitespace-only, and padded max-length inputs.

- Challenge: Search examples in docs drifted from implemented field names.
- Solution: Updated request/response examples to use `item_title`, `chunk_content`, and `search_type`, and removed unimplemented `took_ms`.

### Lessons Learned

- Input normalization must happen before validation constraints when user input may contain padding.
- Internal service contracts (`ChunkSearchResult`) should document intentional differences from external API contracts.
- Task-local docs updates are most reliable when tied directly to executable tests and current model definitions.
