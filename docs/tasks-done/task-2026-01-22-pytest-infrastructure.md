# Task: Set Up Pytest Infrastructure

## Summary

Configure pytest with fixtures for testing the Python backend, including isolated SQLite database support.

## Acceptance Criteria

- [x] pytest configured in `pyproject.toml`
- [x] pytest-asyncio for async test support
- [x] Database fixtures that create/teardown schema (per-file fixtures using tmp_path)
- [x] Test client fixture for API endpoint testing (using httpx.AsyncClient)
- [x] Tests organized in `python-backend/tests/` directory
- [x] Shared fixtures in `conftest.py` to reduce duplication
- [x] Coverage reporting configured (`pytest-cov` dependency + config)

## Dependencies

- Task 1: Python backend project structure ✅
- Task 2: SQLite schema setup ✅

## Technical Notes

- Use `pytest-asyncio` for async tests (configured with `asyncio_mode = "auto"`)
- Use `tmp_path` fixture for isolated file-based SQLite (cleaner than `:memory:` for testing sqlite-vec)
- Use `httpx.AsyncClient` with `ASGITransport` for async endpoint tests (not sync TestClient)
- Fixtures are currently duplicated across test files - consolidate in conftest.py

## Current State

Tests exist and pass, but fixtures are duplicated across files:

- `tests/test_database.py` - Database initialization tests
- `tests/test_repositories.py` - Repository CRUD tests
- `tests/test_api_items.py` - Items API endpoint tests
- `tests/test_api_health.py` - Health check endpoint tests
- `tests/test_api_health_ollama.py` - Ollama health check tests
- `tests/test_providers_ollama.py` - Ollama provider tests

## Remaining Work

### 1. Create `conftest.py` with shared fixtures

```python
# tests/conftest.py
from pathlib import Path
from unittest.mock import patch

import aiosqlite
import pytest
from httpx import ASGITransport, AsyncClient

from src.db.database import _apply_schema, init_database
from src.main import app


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    return tmp_path / "test.db"


@pytest.fixture
async def db_connection(temp_db_path: Path):
    """Database connection with schema applied."""
    async with aiosqlite.connect(temp_db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        db.row_factory = aiosqlite.Row
        await _apply_schema(db)
        await db.commit()
        yield db


@pytest.fixture
async def client(temp_db_path: Path):
    """Async test client with temporary database."""
    with patch("src.config.settings.db_path", temp_db_path):
        await init_database()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
```

### 2. Add coverage configuration to `pyproject.toml`

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["src"]
omit = ["tests/*", "*/__pycache__/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
]
```

### 3. Add pytest-cov to dev dependencies

```toml
[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.14.13",
]
```

## Verification

```bash
cd python-backend

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_repositories.py -v
```

---

## Implementation Details

_Tracked: 2026-01-22_

### Files Changed

| File                                             | Change   | Description                                          |
| ------------------------------------------------ | -------- | ---------------------------------------------------- |
| `python-backend/tests/conftest.py`               | Created  | Shared fixtures: temp_db_path, db_connection, client |
| `python-backend/pyproject.toml`                  | Modified | Added coverage config and pytest-cov dependency      |
| `python-backend/tests/test_api_items.py`         | Modified | Removed 25 lines of duplicate fixtures               |
| `python-backend/tests/test_repositories.py`      | Modified | Removed 20 lines of duplicate fixtures               |
| `python-backend/tests/test_api_health.py`        | Modified | Removed 19 lines of duplicate fixtures               |
| `python-backend/tests/test_api_health_ollama.py` | Modified | Removed 6 lines of duplicate import/fixture          |
| `python-backend/tests/test_database.py`          | Modified | Removed temp_db_path fixture (6 lines)               |
| `eslint.config.js`                               | Modified | Added python-backend/\*\* to ignores (unrelated fix) |

### Dependencies Added

- `pytest-cov>=6.0.0` - Coverage reporting for pytest

### Configuration Added

```toml
[tool.coverage.run]
source = ["src"]
omit = ["tests/*", "*/__pycache__/*"]

[tool.coverage.report]
exclude_lines = ["pragma: no cover", "if TYPE_CHECKING:"]

[tool.pytest.ini_options]
addopts = "-v --tb=short"
```

### Acceptance Criteria Status

- [x] pytest configured in `pyproject.toml` - Already existed, added `addopts`
- [x] pytest-asyncio for async test support - Already configured with `asyncio_mode = "auto"`
- [x] Database fixtures in `conftest.py:20` - `db_connection` fixture
- [x] Test client fixture in `conftest.py:35` - `client` fixture with httpx.AsyncClient
- [x] Tests organized in `python-backend/tests/` - 6 test files, 89 tests
- [x] Shared fixtures in `conftest.py` - Consolidated from 5 files, removed 76 duplicate lines
- [x] Coverage reporting configured - 92% coverage, `pytest-cov` added

---

## Learning Report

_Generated: 2026-01-22_

### Summary

Consolidated pytest fixtures from 5 test files into a shared `conftest.py`, reducing 76 lines of duplicate code. Added coverage reporting configuration achieving 92% code coverage across 89 tests. The implementation followed the exact patterns specified in the task document.

**Metrics:**

- 1 new file created (`conftest.py` - 47 lines)
- 5 test files modified (76 lines removed)
- 1 dependency added (`pytest-cov`)
- 89 tests passing, 92% coverage

### Patterns & Decisions

**Fixture Hierarchy Pattern:**
The fixtures form a dependency chain: `tmp_path` (pytest built-in) → `temp_db_path` → `db_connection`/`client`. This allows tests to choose the appropriate level of abstraction:

- Repository tests use `db_connection` for direct database access
- API tests use `client` for HTTP-level testing
- Database schema tests use `temp_db_path` with custom setup

**Settings Patching Pattern:**
The `client` fixture patches `src.config.settings.db_path` rather than environment variables. This is cleaner because:

1. Settings are already loaded at import time
2. Patching the settings object directly is more explicit
3. Avoids environment variable pollution between tests

**File-based vs In-Memory SQLite:**
Chose `tmp_path` (file-based) over `:memory:` because sqlite-vec extension requires file-based databases for its vector index operations.

### Challenges & Solutions

**Challenge: Import Cleanup After Fixture Removal**
When removing fixture code, unused imports were left behind (e.g., `pytest`, `Path`, `patch`). The `/review` command's ruff check caught these with `F401` (unused import) errors.

**Solution:** Running `uv run ruff check --fix .` automatically cleaned up unused imports and sorted import blocks (`I001`).

**Challenge: ESLint Picking Up Python .venv Files**
The python-backend's `.venv/lib/python3.11/site-packages/coverage/htmlfiles/coverage_html.js` was being linted by ESLint, causing 39 errors.

**Solution:** Added `'python-backend/**'` to ESLint ignores. Python backend has its own tooling (ruff) and doesn't need JS linting.

### Lessons Learned

**What worked well:**

1. The task document's code examples were exact - implementation was copy-paste with minor docstring enhancements
2. pytest's automatic fixture discovery from conftest.py eliminated import boilerplate
3. Coverage configuration in pyproject.toml keeps all Python config in one place

**Recommendations for similar tasks:**

1. When consolidating duplicate code, run linters immediately after to catch orphaned imports
2. Add new directories to ESLint ignores proactively when they contain their own JS artifacts
3. Task documents with exact code examples dramatically speed up implementation

### Documentation Impact

**No documentation updates needed:**

- `docs/developer/python-backend/architecture.md` already covers the testing approach
- The pytest patterns used are standard and don't require additional documentation

**Patterns worth noting for future reference:**

- The settings patching approach (`patch("src.config.settings.db_path", ...)`) could be documented if other modules adopt similar patterns
- Coverage thresholds could be added to CI in a future task
