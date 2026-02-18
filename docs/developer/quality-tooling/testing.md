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
  unwrapResult: vi.fn((result: { status: string; data?: unknown }) => {
    if (result.status === 'ok') return result.data
    throw result
  }),
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

### Custom Render with All Providers

`src/test/test-utils.tsx` exports a custom `render` function that wraps components in all required providers (`QueryClientProvider`, `I18nextProvider`, `MockThemeProvider`, and `RouterProvider`). Use this instead of the raw `@testing-library/react` render:

```typescript
import { render, screen, waitFor } from '@/test/test-utils'

test('component with query, routing, and i18n', () => {
  render(<MyComponent />, { initialPath: '/items' })
})
```

This means components using `useTranslation()`, `useTheme()`, TanStack Query hooks, or TanStack Router navigation all work without extra setup.

### Testing with Router

The test utils create a memory-based router with `createMemoryHistory` to control routing state without hash-based URLs. The test router defines an explicit set of routes (currently `/`, `/items`, `/items/$id`, `/conversations`, and a catch-all `$`). When a new route is needed for test assertions (e.g., verifying `<Link>` navigation via `toHaveAttribute('href', ...)`), add the route to the `routeTree` in `src/test/test-utils.tsx`.

```typescript
render(<MyComponent />, { initialPath: '/items' })

// Assert typed navigation
const link = screen.getByRole('link', { name: /Item Title/i })
expect(link).toHaveAttribute('href', '/items/item-1')
```

### Mocking Service Hooks

To mock TanStack Query service hooks while preserving type exports, use `vi.importActual`:

```typescript
vi.mock('@/services/items', async () => {
  const actual = await vi.importActual('@/services/items')
  return { ...actual, useItems: vi.fn() }
})

const { useItems } = await import('@/services/items')
const useItemsMock = vi.mocked(useItems)

test('renders items', () => {
  useItemsMock.mockReturnValue(/* query result */)
  render(<ItemList />)
})
```

This preserves type exports (`Item`, `ContentType`, etc.) while mocking the hook.

### Testing Zustand Stores

Stores can be tested directly via `getState()` without rendering -- this is faster and clearer when the store has no rendering dependencies:

```typescript
import { useProcessingStore } from '@/store/processing-store'

beforeEach(() => useProcessingStore.getState().reset())

test('setUpdate adds entry', () => {
  useProcessingStore.getState().setUpdate(mockUpdate)
  const state = useProcessingStore.getState()
  expect(state.processingByItemId['item-1']).toEqual(mockUpdate)
})
```

See `src/store/processing-store.test.ts` for a full example.

Alternatively, use `renderHook` when you need to test reactive behavior or selectors:

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

Place tests in the `tests/` directory organized by domain with `test_` prefix:

```
python-backend/
├── src/
│   ├── api/
│   │   ├── dependencies.py         # Dependency injection helpers
│   │   ├── routes/
│   │   │   ├── health.py           # Health check endpoint
│   │   │   ├── items.py            # CRUD for items
│   │   │   ├── processing.py       # Processing queue endpoints
│   │   │   └── ws.py               # WebSocket endpoints
│   │   └── websocket/
│   │       └── manager.py          # ProcessingConnectionManager
│   ├── services/
│   │   └── processing.py
│   └── workflows/
│       └── processing.py
└── tests/
    ├── api/                         # API endpoint tests
    │   ├── test_health.py
    │   ├── test_health_ollama.py
    │   ├── test_items.py
    │   ├── test_processing.py
    │   └── test_ws_processing.py
    ├── core/                        # Exception hierarchy tests
    │   └── test_exceptions.py
    ├── db/                          # Database and repository tests
    │   ├── test_database.py
    │   └── test_repositories.py
    ├── providers/                   # AI provider tests
    │   └── test_ollama.py
    ├── services/                    # Service-level tests
    │   ├── test_embeddings.py
    │   ├── test_parsing.py
    │   └── test_search.py
    ├── workflows/                   # Workflow integration tests
    │   └── test_processing.py
    └── conftest.py                  # Shared fixtures
```

### Test Setup

Shared fixtures are defined in `tests/conftest.py`, grouped by domain:

```python
# tests/conftest.py — key fixtures (simplified)

# Database fixtures
temp_db_path       # Temporary database path via tmp_path
db_connection      # Direct DB connection with schema applied
db_with_vec        # DB connection with sqlite-vec extension loaded
mock_settings      # Patched settings with temporary db_path

# HTTP/client fixtures
client             # AsyncClient with temporary DB and mock processing queue

# Provider fixtures
ollama_provider    # Real OllamaProvider instance (for provider unit tests)
mock_ollama_provider  # MagicMock(spec=OllamaProvider) for health endpoint tests
mock_provider      # MockAIProvider with deterministic embeddings

# Service fixtures
embedding_service  # EmbeddingService with mock provider
search_service     # SearchService with mock EmbeddingService

# Test data fixtures
sample_chunks      # List of sample Chunk objects for tests
```

`MockAIProvider(AIProvider)` is defined in `tests/fakes/providers.py` as a deterministic provider that records calls and supports configurable failure via `should_fail=True`.

**Fixture hierarchy:**

- `temp_db_path` - Base fixture creating a temporary database path
- `db_connection` - Direct database connection for repository tests (uses `_apply_schema`)
- `db_with_vec` - Database connection with sqlite-vec for embedding tests
- `client` - HTTP client for API tests (uses `init_database` which calls `_apply_schema`)

**Mock processing queue:** Since the `client` fixture bypasses FastAPI's lifespan (no real startup/shutdown), it sets a mock `ProcessingQueue` on `app.state`. This satisfies `get_processing_queue()` in routes like `create_item` without actually running workers. Use `AsyncMock(spec=ProcessingQueue)` to get type-checked mock methods.

**Important:** Use file-based SQLite with `tmp_path`, not `:memory:`. The sqlite-vec extension requires file-based databases for its vector index operations.

This pattern:

- Uses `tmp_path` fixture for isolated file-based test databases
- Patches `settings.db_path` to redirect database operations
- Uses `ASGITransport` for proper async ASGI app testing
- Applies the real schema from `schema.sql` for each test

### Example Tests

```python
# tests/api/test_items.py

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
pytest tests/api/test_items.py

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
