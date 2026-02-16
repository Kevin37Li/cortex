# Task: Define Search Pydantic Models and Error Types

## Summary

Add the Pydantic request/response models and exception types needed by the search system. This establishes the data contracts used by the search service, LangGraph workflow, API endpoint, and frontend.

## Acceptance Criteria

- [ ] `SearchRequest` model added to `python-backend/src/db/models.py` with fields: `query` (str), `limit` (int, default 20, ge=1, le=100), `search_type` (Literal["hybrid", "vector", "fts"], default "hybrid")
- [ ] `SearchResultItem` model added with fields: `item_id` (str), `item_title` (str), `content_type` (ContentType), `chunk_id` (str), `chunk_content` (str), `score` (float, ge=0.0, le=1.0), `rank` (int, ge=1)
- [ ] `SearchResponse` model added with fields: `results` (list[SearchResultItem]), `total` (int), `query` (str), `search_type` (str)
- [ ] `SearchError` exception added to `python-backend/src/exceptions.py` extending `CortexError` with `error_code = "search_error"` and keyword args `query: str | None`, `step: str | None`
- [ ] All new models exported from `python-backend/src/db/__init__.py`
- [ ] `SearchError` exported from `python-backend/src/exceptions.py`
- [ ] `SearchType` Literal type alias defined for reuse: `SearchType = Literal["hybrid", "vector", "fts"]`
- [ ] Ruff and mypy pass: `uv run ruff check src/` and `uv run mypy src/`

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
    query: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=20, ge=1, le=100)
    search_type: SearchType = "hybrid"
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

## Files to Modify

- `python-backend/src/db/models.py` - Add SearchRequest, SearchResultItem, SearchResponse, ChunkSearchResult, SearchType
- `python-backend/src/db/__init__.py` - Export new models
- `python-backend/src/exceptions.py` - Add SearchError

## Verification

```bash
cd python-backend
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/
uv run pytest tests/ -x
```
