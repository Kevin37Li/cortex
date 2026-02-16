# Task: Write Search Backend Tests

## Summary

Write comprehensive tests for the search service, LangGraph workflow, and API endpoint. Tests should cover vector search, FTS search, hybrid RRF fusion, result enrichment, error cases, and the HTTP endpoint contract.

## Acceptance Criteria

- [ ] `python-backend/tests/services/test_search.py` created with tests for `SearchService`
- [ ] `python-backend/tests/workflows/test_search.py` created with tests for search workflow
- [ ] `python-backend/tests/api/test_search.py` created with tests for search API endpoint
- [ ] Vector search tests: returns results sorted by similarity, normalizes distance to [0, 1] score, handles empty index
- [ ] FTS search tests: returns results for matching terms, normalizes rank to [0, 1] score, handles no matches, handles special characters in query
- [ ] Hybrid search tests: combines vector and FTS results via RRF, deduplicates chunks appearing in both, handles one source returning empty
- [ ] RRF unit tests: correct score calculation, correct ordering, handles single-source input
- [ ] Result enrichment tests: adds item title and content_type, skips orphaned chunks (item deleted but chunk remains)
- [ ] Error handling tests: SearchError raised for empty query, graceful handling of embedding failures
- [ ] API endpoint tests: 200 with results, 200 with empty results, 422 for search errors, validates request body
- [ ] All tests pass: `uv run pytest tests/ -x`
- [ ] Test coverage for search code >= 85%

## Dependencies

- Task 1: Search models
- Task 2: SearchService
- Task 3: Search workflow
- Task 4: Search API endpoint
- Phase 2: Test fixtures pattern established in `tests/conftest.py`

## Technical Notes

### Test Setup

Search tests require seeded data: items with chunks, embeddings, and FTS entries. Create fixtures that:

1. Initialize a test database (use `tmp_path` for file-based SQLite - required by sqlite-vec)
2. Create test items
3. Create chunks for those items (triggers FTS sync)
4. Generate and store embeddings for those chunks

**Important**: sqlite-vec requires file-based databases, not `:memory:`. Use `tmp_path` fixture.

### Fixture Pattern

Follow the established fixture pattern from `tests/conftest.py`:

```python
import pytest
import aiosqlite
import sqlite_vec
from pathlib import Path

from src.db.database import init_database, _configure_connection
from src.config import settings


@pytest.fixture
async def search_db(tmp_path: Path):
    """Create a test database seeded with items, chunks, and embeddings."""
    db_path = tmp_path / "test_search.db"
    original_path = settings.db_path
    settings.db_path = db_path

    try:
        await init_database()
        async with aiosqlite.connect(db_path) as db:
            await _configure_connection(db)
            # Seed test data
            await _seed_test_data(db)
            await db.commit()
            yield db
    finally:
        settings.db_path = original_path


async def _seed_test_data(db: aiosqlite.Connection):
    """Seed items, chunks, and embeddings for search tests."""
    # Create items
    await db.execute(
        "INSERT INTO items (id, title, content, content_type, processing_status) VALUES (?, ?, ?, ?, ?)",
        ["item-1", "Python Programming Guide", "Learn Python...", "note", "completed"],
    )
    await db.execute(
        "INSERT INTO items (id, title, content, content_type, processing_status) VALUES (?, ?, ?, ?, ?)",
        ["item-2", "JavaScript Best Practices", "Modern JS...", "webpage", "completed"],
    )
    # Create chunks
    await db.execute(
        "INSERT INTO chunks (id, item_id, content, chunk_index, token_count) VALUES (?, ?, ?, ?, ?)",
        ["chunk-1a", "item-1", "Python is a versatile programming language used for web development, data science, and AI.", 0, 15],
    )
    await db.execute(
        "INSERT INTO chunks (id, item_id, content, chunk_index, token_count) VALUES (?, ?, ?, ?, ?)",
        ["chunk-1b", "item-1", "Python supports multiple programming paradigms including procedural, object-oriented, and functional.", 1, 12],
    )
    await db.execute(
        "INSERT INTO chunks (id, item_id, content, chunk_index, token_count) VALUES (?, ?, ?, ?, ?)",
        ["chunk-2a", "item-2", "JavaScript is the language of the web, running in browsers and on servers with Node.js.", 0, 16],
    )
    # Embeddings are inserted via the embedding service or mocked
```

### Mocking Embeddings for Vector Search Tests

For unit tests, mock the `EmbeddingService` to return deterministic embeddings:

```python
from unittest.mock import AsyncMock, MagicMock
from src.db.database import EMBEDDING_DIMENSION

def make_test_embedding(seed: float) -> list[float]:
    """Create a deterministic test embedding vector."""
    import math
    # Create a normalized vector with predictable similarity properties
    vec = [math.sin(seed + i) for i in range(EMBEDDING_DIMENSION)]
    norm = math.sqrt(sum(x*x for x in vec))
    return [x / norm for x in vec]

@pytest.fixture
def mock_embedding_service():
    service = MagicMock()
    service.embed_query = AsyncMock(return_value=make_test_embedding(0.0))
    return service
```

For integration tests that need real vector search behavior, insert pre-computed embeddings directly into `vec_chunks`.

### RRF Unit Tests

Test RRF independently (it's a pure function):

```python
from src.services.search import reciprocal_rank_fusion

def test_rrf_combines_rankings():
    vector = [
        ChunkSearchResult(chunk_id="a", item_id="1", content="...", score=1.0),
        ChunkSearchResult(chunk_id="b", item_id="2", content="...", score=0.8),
    ]
    fts = [
        ChunkSearchResult(chunk_id="b", item_id="2", content="...", score=1.0),
        ChunkSearchResult(chunk_id="c", item_id="3", content="...", score=0.9),
    ]
    result = reciprocal_rank_fusion(vector, fts, k=60)

    # "b" appears in both lists, should rank highest
    assert result[0].chunk_id == "b"
    assert len(result) == 3  # a, b, c (deduplicated)

def test_rrf_single_source():
    """RRF works with only vector results (FTS empty)."""
    vector = [ChunkSearchResult(chunk_id="a", item_id="1", content="...", score=1.0)]
    result = reciprocal_rank_fusion(vector, [], k=60)
    assert len(result) == 1
    assert result[0].chunk_id == "a"

def test_rrf_empty_inputs():
    result = reciprocal_rank_fusion([], [], k=60)
    assert result == []
```

### API Endpoint Tests

Use `httpx.AsyncClient` with FastAPI's `TestClient` pattern:

```python
from httpx import ASGITransport, AsyncClient
from src.main import app

@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

async def test_search_returns_results(client, search_db):
    response = await client.post("/api/search/", json={
        "query": "python programming",
        "limit": 10,
        "search_type": "hybrid",
    })
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total" in data
    assert data["query"] == "python programming"

async def test_search_empty_results(client, search_db):
    response = await client.post("/api/search/", json={
        "query": "completely unrelated topic xyz",
    })
    assert response.status_code == 200
    assert response.json()["results"] == []

async def test_search_validates_request(client):
    response = await client.post("/api/search/", json={
        "query": "",  # Too short
    })
    assert response.status_code == 422
```

### Test Organization

```
tests/
  services/
    test_search.py        # SearchService unit tests
  workflows/
    test_search.py        # Search workflow integration tests
  api/
    test_search.py        # API endpoint tests
```

Create the `tests/workflows/` and `tests/api/` directories if they don't exist.

## Files to Create

- `python-backend/tests/services/test_search.py`
- `python-backend/tests/workflows/test_search.py`
- `python-backend/tests/api/test_search.py`

## Verification

```bash
cd python-backend
uv run pytest tests/ -x -v
uv run pytest tests/ --cov=src --cov-report=term-missing
```
