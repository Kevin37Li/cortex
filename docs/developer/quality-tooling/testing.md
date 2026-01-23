# Testing

Testing patterns for Rust and TypeScript, with focus on Tauri-specific mocking.

## Running Tests

```bash
bun run check:all      # All tests and checks
bun run test           # TypeScript tests (watch mode)
bun run test:run       # TypeScript tests (single run)
bun run rust:test      # Rust tests
```

## TypeScript Testing

Uses **Vitest** + **@testing-library/react**. Configuration in `vitest.config.ts`.

### Test File Location

Place tests next to the code they test:

```
src/components/ui/Button.tsx
src/components/ui/Button.test.tsx
```

### Mocking Tauri APIs (Critical)

Tauri commands must be mocked since tests run outside the Tauri environment. Mocks are configured in `src/test/setup.ts`:

```typescript
// src/test/setup.ts
import { vi } from 'vitest'

// Mock Tauri event APIs
vi.mock('@tauri-apps/api/event', () => ({
  listen: vi.fn().mockResolvedValue(() => {}),
}))

vi.mock('@tauri-apps/plugin-updater', () => ({
  check: vi.fn().mockResolvedValue(null),
}))

// Mock typed Tauri bindings (tauri-specta generated)
vi.mock('@/lib/tauri-bindings', () => ({
  commands: {
    greet: vi.fn().mockResolvedValue('Hello, test!'),
    loadPreferences: vi
      .fn()
      .mockResolvedValue({ status: 'ok', data: { theme: 'system' } }),
    savePreferences: vi.fn().mockResolvedValue({ status: 'ok', data: null }),
    sendNativeNotification: vi
      .fn()
      .mockResolvedValue({ status: 'ok', data: null }),
    saveEmergencyData: vi.fn().mockResolvedValue({ status: 'ok', data: null }),
    loadEmergencyData: vi.fn().mockResolvedValue({ status: 'ok', data: null }),
    cleanupOldRecoveryFiles: vi
      .fn()
      .mockResolvedValue({ status: 'ok', data: 0 }),
  },
}))
```

### Testing with Mocked Commands

```typescript
import { vi } from 'vitest'
import { commands } from '@/lib/tauri-bindings'

const mockCommands = vi.mocked(commands)

test('loads preferences', async () => {
  mockCommands.loadPreferences.mockResolvedValue({
    status: 'ok',
    data: { theme: 'dark' },
  })

  // Test code that calls loadPreferences
})
```

### Test Wrapper for Providers

Components using TanStack Query need a provider wrapper:

```typescript
// src/test/utils.ts
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactNode } from 'react'

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

export function TestProviders({ children }: { children: ReactNode }) {
  const queryClient = createTestQueryClient()
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}
```

Usage:

```typescript
import { render } from '@testing-library/react'
import { TestProviders } from '@/test/utils'

test('component with query', () => {
  render(
    <TestProviders>
      <MyComponent />
    </TestProviders>
  )
})
```

### Testing Zustand Stores

```typescript
import { renderHook, act } from '@testing-library/react'
import { useUIStore } from '@/store/ui-store'

test('toggles sidebar visibility', () => {
  const { result } = renderHook(() => useUIStore())

  expect(result.current.leftSidebarVisible).toBe(true)

  act(() => {
    result.current.setLeftSidebarVisible(false)
  })

  expect(result.current.leftSidebarVisible).toBe(false)
})
```

## Rust Testing

### Unit Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_preferences_default() {
        let prefs = AppPreferences::default();
        assert_eq!(prefs.theme, "system");
    }
}
```

### Async Tests

```rust
#[tokio::test]
async fn test_async_operation() {
    let result = some_async_fn().await;
    assert!(result.is_ok());
}
```

### File Operation Tests

Use `tempfile` for tests that need file system access:

```rust
use tempfile::TempDir;

#[test]
fn test_file_operations() {
    let temp_dir = TempDir::new().unwrap();
    let file_path = temp_dir.path().join("test.json");

    // Test write
    std::fs::write(&file_path, "{}").unwrap();

    // Test read
    let content = std::fs::read_to_string(&file_path).unwrap();
    assert_eq!(content, "{}");
}
```

## Adding New Command Mocks

When adding new Tauri commands, update `src/test/setup.ts`:

```typescript
vi.mock('@/lib/tauri-bindings', () => ({
  commands: {
    // ... existing mocks
    myNewCommand: vi.fn().mockResolvedValue({ status: 'ok', data: null }),
  },
}))
```

## Python Testing

Uses **pytest** with **pytest-asyncio** for async tests. Configuration in `pyproject.toml`.

### Test File Location

Place tests in the `tests/` directory with `test_` prefix:

```
python-backend/
├── src/
│   ├── api/
│   │   └── items.py
│   └── workflows/
│       └── processing.py
└── tests/
    ├── test_api_items.py       # API endpoint tests
    ├── test_repositories.py    # Repository tests
    ├── test_workflows.py       # Workflow tests
    └── conftest.py             # Shared fixtures
```

### Test Setup

Shared fixtures are defined in `tests/conftest.py`. There are two main fixtures for different test levels:

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
    """Database connection with schema applied.

    Use for repository and database-level tests that need direct DB access.
    """
    async with aiosqlite.connect(temp_db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        db.row_factory = aiosqlite.Row
        await _apply_schema(db)
        await db.commit()
        yield db


@pytest.fixture
async def client(temp_db_path: Path):
    """Async test client with temporary database.

    Use for API endpoint tests that make HTTP requests.
    """
    with patch("src.config.settings.db_path", temp_db_path):
        await init_database()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
```

**Fixture hierarchy:**

- `temp_db_path` - Base fixture creating a temporary database path
- `db_connection` - Direct database connection for repository tests (uses `_apply_schema`)
- `client` - HTTP client for API tests (uses `init_database` which calls `_apply_schema`)

**Important:** Use file-based SQLite with `tmp_path`, not `:memory:`. The sqlite-vec extension requires file-based databases for its vector index operations.

This pattern:

- Uses `tmp_path` fixture for isolated file-based test databases
- Patches `settings.db_path` to redirect database operations
- Uses `ASGITransport` for proper async ASGI app testing
- Applies the real schema from `schema.sql` for each test

### Example Tests

```python
# tests/test_api_items.py

class TestCreateItem:
    """Test POST /api/items/ endpoint."""

    async def test_create_item_success(self, client: AsyncClient):
        """Test creating an item returns 201 and the item data."""
        response = await client.post(
            "/api/items/",
            json={
                "title": "Test Item",
                "content": "Test content",
                "content_type": "note",
            },
        )

        assert response.status_code == 201  # Created
        data = response.json()
        assert data["title"] == "Test Item"
        assert data["processing_status"] == "pending"
        assert "id" in data

    async def test_create_item_validation_error(self, client: AsyncClient):
        """Test creating an item with missing fields returns 422."""
        response = await client.post(
            "/api/items/",
            json={"title": "Test Item"},  # missing content and content_type
        )
        assert response.status_code == 422


class TestGetItem:
    """Test GET /api/items/{id} endpoint."""

    async def test_get_item_not_found(self, client: AsyncClient):
        """Test getting a non-existent item returns 404."""
        response = await client.get("/api/items/nonexistent-id")

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "item_not_found"
```

### Running Python Tests

```bash
# Run all Python tests
cd python-backend && pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api_items.py

# Run with verbose output
pytest -v
```

## Best Practices

| Do                                    | Don't                         |
| ------------------------------------- | ----------------------------- |
| Mock Tauri commands in setup.ts       | Call real Tauri APIs in tests |
| Use `vi.mocked()` for type-safe mocks | Use untyped mock assertions   |
| Test user-visible behavior            | Test implementation details   |
| Use `tempfile` for Rust file tests    | Write to real file system     |
| Use file-based SQLite with `tmp_path` | Connect to real database      |
| Use `pytest.fixture` for test setup   | Duplicate setup in each test  |
