# Task: Set Up Pytest Infrastructure

## Summary

Configure pytest with fixtures for testing the Python backend, including in-memory SQLite database support.

## Acceptance Criteria

- [ ] pytest configured in `pyproject.toml`
- [ ] pytest-asyncio for async test support
- [ ] In-memory SQLite fixture for fast, isolated tests
- [ ] Database fixtures that create/teardown schema
- [ ] Test client fixture for API endpoint testing
- [ ] Coverage reporting configured
- [ ] Tests organized in `python-backend/tests/` directory

## Dependencies

- Task 1: Python backend project structure
- Task 2: SQLite schema setup

## Technical Notes

- Use `pytest-asyncio` for async tests
- In-memory SQLite: `sqlite:///:memory:`
- FastAPI TestClient for endpoint tests
- Fixtures should be reusable across test files

## Fixture Design

```python
# conftest.py

@pytest.fixture
async def db():
    """In-memory database with schema initialized."""
    async with aiosqlite.connect(":memory:") as conn:
        await init_schema(conn)
        yield conn

@pytest.fixture
def client(db):
    """Test client with database dependency override."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
async def item_repo(db):
    """ItemRepository with test database."""
    return ItemRepository(db)
```

## Files to Create

```
python-backend/
├── pyproject.toml        # Add pytest config
└── tests/
    ├── __init__.py
    ├── conftest.py       # Shared fixtures
    ├── test_health.py    # Example test
    └── unit/
        └── __init__.py
```

## pyproject.toml additions

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["src"]
omit = ["tests/*"]
```

## Verification

```bash
cd python-backend

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing

# Should see test discovery and execution
```
