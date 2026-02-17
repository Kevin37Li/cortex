# Error Handling

Patterns for consistent error handling across Rust and TypeScript.

## Error Propagation Flow

```
Rust Command (Result<T, E>) → tauri-specta → TypeScript discriminated union → TanStack Query/UI
```

Rust `Result<T, E>` types become TypeScript discriminated unions:

```typescript
type Result<T, E> = { status: 'ok'; data: T } | { status: 'error'; error: E }
```

## Rust Error Types

### Simple Commands

For commands with one failure mode, use `String` errors:

```rust
#[tauri::command]
#[specta::specta]
pub async fn simple_operation() -> Result<Data, String> {
    do_work().map_err(|e| format!("Operation failed: {e}"))
}
```

### Production Commands

For commands with multiple failure modes, use structured error enums:

```rust
#[derive(Debug, Clone, Serialize, Deserialize, Type)]
#[serde(tag = "type")]  // Creates TypeScript discriminated union
pub enum MyError {
    NotFound,
    ValidationError { message: String },
    IoError { message: String },
}

impl std::fmt::Display for MyError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            MyError::NotFound => write!(f, "Not found"),
            MyError::ValidationError { message } => write!(f, "{message}"),
            MyError::IoError { message } => write!(f, "IO error: {message}"),
        }
    }
}

#[tauri::command]
#[specta::specta]
pub async fn production_operation() -> Result<Data, MyError> {
    // ...
}
```

TypeScript receives:

```typescript
type MyError =
  | { type: 'NotFound' }
  | { type: 'ValidationError'; message: string }
  | { type: 'IoError'; message: string }
```

## TypeScript Error Handling

### Pattern 1: Explicit Handling (Event Handlers)

```typescript
// ✅ GOOD: Handle errors inline with user feedback
const handleSave = async () => {
  const result = await commands.saveData(data)
  if (result.status === 'error') {
    toast.error('Save failed', { description: result.error })
    return
  }
  toast.success('Saved!')
}
```

### Pattern 2: unwrapResult (TanStack Query)

```typescript
// ✅ GOOD: Let TanStack Query handle errors
const { data, error } = useQuery({
  queryKey: ['data'],
  queryFn: async () => unwrapResult(await commands.loadData()),
})
```

### Pattern 3: Graceful Degradation

```typescript
// ✅ GOOD: Fall back to defaults on error
const { data } = useQuery({
  queryKey: ['preferences'],
  queryFn: async () => {
    const result = await commands.loadPreferences()
    if (result.status === 'error') {
      logger.warn('Failed to load preferences, using defaults')
      return defaultPreferences
    }
    return result.data
  },
})
```

## User-Facing vs Technical Errors

### Rust: Log Technical Details, Return User Messages

```rust
// ✅ GOOD: Log technical details, return user-friendly message
pub async fn load_file(path: &str) -> Result<String, String> {
    log::debug!("Loading file: {path}");

    std::fs::read_to_string(path).map_err(|e| {
        log::error!("Failed to read file {path}: {e}");  // Technical log
        format!("Could not read file")                   // User message
    })
}
```

### TypeScript: Toast for Users, Logger for Debugging

```typescript
// ✅ GOOD: Separate user feedback from technical logging
const result = await commands.saveData(data)
if (result.status === 'error') {
  logger.error('Save failed', { error: result.error, data }) // Technical
  toast.error('Failed to save') // User-facing
}
```

## Retry Configuration

Configure TanStack Query retry behavior based on error type:

```typescript
import { ApiRequestError } from '@/lib/api-config'

// ✅ GOOD: Smart retry logic using structured error
const { data } = useQuery({
  queryKey: ['data'],
  queryFn: loadData,
  retry: (failureCount, error) => {
    // Don't retry client errors (4xx)
    if (
      error instanceof ApiRequestError &&
      error.status >= 400 &&
      error.status < 500
    )
      return false
    // Retry network/server errors up to 3 times
    return failureCount < 3
  },
})
```

Default retry settings in `query-client.ts`:

| Query Type | Retries | Rationale                            |
| ---------- | ------- | ------------------------------------ |
| Queries    | 1       | Transient failures may recover       |
| Mutations  | 1       | Avoid duplicate writes on slow saves |

## Global Error Toasts

Avoid per-query error toasts (causes duplicates). Use global handling:

```typescript
// ✅ GOOD: Centralized in query-client.ts
const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      if (query.meta?.errorToast !== false) {
        toast.error('Something went wrong')
      }
    },
  }),
})

// Opt out for specific queries
useQuery({
  queryKey: ['optional-feature'],
  queryFn: loadOptional,
  meta: { errorToast: false },
})
```

## React Error Boundaries

Error boundaries catch render errors, not async errors:

| Caught by Error Boundary    | NOT Caught                          |
| --------------------------- | ----------------------------------- |
| Errors during render        | Errors in event handlers            |
| Errors in lifecycle methods | Async code (promises)               |
| Errors in constructors      | Errors in the error boundary itself |

For async Tauri command errors, use explicit handling or `unwrapResult` with TanStack Query.

## Rollback Pattern

For multi-step operations, rollback on failure:

```typescript
// ✅ GOOD: Rollback on failure
const handleChange = async (newValue: string) => {
  const oldValue = currentValue

  // Step 1: Update backend
  const result = await commands.updateValue(newValue)
  if (result.status === 'error') {
    toast.error('Update failed')
    return
  }

  // Step 2: Persist
  try {
    await savePreferences.mutateAsync({ ...prefs, value: newValue })
  } catch {
    // Rollback step 1
    await commands.updateValue(oldValue)
    toast.error('Save failed, changes reverted')
  }
}
```

## Python Error Handling

### Custom Exceptions

Define a hierarchy of exceptions for the Python backend:

```python
# src/exceptions.py
class CortexError(Exception):
    """Base exception for Cortex backend."""
    error_code: str = "cortex_error"

class ItemNotFoundError(CortexError):
    """Item does not exist. Used by repository update() methods."""
    error_code: str = "item_not_found"

    def __init__(self, *, item_id: str) -> None:
        self.item_id = item_id
        super().__init__(f"Item not found: {item_id}")

class ChunkNotFoundError(CortexError):
    """Chunk does not exist."""
    error_code: str = "chunk_not_found"

    def __init__(self, *, chunk_id: str) -> None:
        self.chunk_id = chunk_id
        super().__init__(f"Chunk not found: {chunk_id}")

class DatabaseError(CortexError):
    """Database operation failed (e.g., post-operation validation)."""
    error_code: str = "database_error"

class ProcessingError(CortexError):
    """Error during content processing pipeline."""
    error_code: str = "processing_error"

    def __init__(self, message: str, *, item_id: str | None = None, step: str | None = None) -> None:
        self.item_id = item_id
        self.step = step
        super().__init__(message)

class SearchError(CortexError):
    """Search operation failed (not part of content processing pipeline)."""
    error_code: str = "search_error"

    def __init__(self, message: str, *, query: str | None = None, step: str | None = None) -> None:
        self.query = query
        self.step = step
        super().__init__(message)

class AIProviderError(CortexError):
    """Base exception for AI provider errors."""
    error_code: str = "ai_provider_error"

class OllamaNotRunningError(AIProviderError):
    """Ollama server is not accessible."""
    error_code: str = "ollama_not_running"

    def __init__(self, *, base_url: str) -> None:
        self.base_url = base_url
        super().__init__(f"Ollama not running at {base_url}")

class OllamaModelNotFoundError(AIProviderError):
    """Requested model not available in Ollama."""
    error_code: str = "ollama_model_not_found"

    def __init__(self, *, model: str) -> None:
        self.model = model
        super().__init__(f"Model not found: {model}. Run: ollama pull {model}")

class OllamaTimeoutError(AIProviderError):
    """Ollama operation timed out."""
    error_code: str = "ollama_timeout"

    def __init__(self, *, operation: str, timeout: float) -> None:
        self.operation = operation
        self.timeout = timeout
        super().__init__(f"Ollama {operation} timed out after {timeout}s")

class OllamaAPIResponseError(AIProviderError):
    """Ollama API returned malformed response."""
    error_code: str = "ollama_api_response_error"

    def __init__(self, *, operation: str, model: str, response_data: dict | None) -> None:
        self.operation = operation
        self.model = model
        self.response_data = response_data
        super().__init__(f"Ollama {operation} returned malformed response for model '{model}': {response_data}")

class ContentParsingError(ProcessingError):
    """HTML/text content cannot be parsed."""
    error_code: str = "content_parsing_error"

class ChunkingError(ProcessingError):
    """Text splitting/chunking failed."""
    error_code: str = "chunking_error"

class EmbeddingError(ProcessingError):
    """Embedding generation failed during processing (distinct from AIProviderError)."""
    error_code: str = "embedding_error"

class EmbeddingModelMismatchError(ProcessingError):
    """Embedding dimensions or model are inconsistent."""
    error_code: str = "embedding_model_mismatch"

class MetadataExtractionError(ProcessingError):
    """LLM-based metadata extraction failed."""
    error_code: str = "metadata_extraction_error"
```

All constructors use **keyword-only arguments** for structured fields (the `*` in the signature), with human-readable message strings as the only positional parameter where applicable. Each class defines a static `error_code` used in API responses. Processing error subclasses inherit `ProcessingError`'s constructor and only override `error_code`. Original exceptions are preserved via Python's `raise ... from e` chaining pattern rather than a redundant `original_error` parameter.

The hierarchy allows granular exception handling:

```python
try:
    embedding = await provider.embed(text)
except OllamaNotRunningError:
    # Connection failed - show "start Ollama" message
except OllamaModelNotFoundError as e:
    # Offer to pull model: ollama pull {e.model}
except OllamaTimeoutError:
    # Request timed out - model may be loading
except AIProviderError:
    # Catch-all for other provider errors
```

### FastAPI Exception Handlers

Register exception handlers for consistent API responses:

```python
# src/main.py
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(ItemNotFoundError)
async def item_not_found_handler(request: Request, exc: ItemNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": exc.error_code, "message": str(exc)}
    )

@app.exception_handler(ProcessingError)
async def processing_error_handler(request: Request, exc: ProcessingError):
    return JSONResponse(
        status_code=500,
        content={"error": exc.error_code, "message": str(exc)}
    )

@app.exception_handler(AIProviderError)
async def ai_provider_error_handler(request: Request, exc: AIProviderError):
    return JSONResponse(
        status_code=503,
        content={"error": exc.error_code, "message": str(exc)}
    )

@app.exception_handler(SearchError)
async def search_error_handler(request: Request, exc: SearchError):
    return JSONResponse(
        status_code=500,
        content={"error": exc.error_code, "message": str(exc)}
    )

@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    # Hide internal database details from API response
    return JSONResponse(
        status_code=500,
        content={"error": exc.error_code, "message": "Internal database error"}
    )
```

### External Service Error Pattern

For external services (Ollama, cloud APIs), use a two-tier approach:

1. **Availability check** - Returns `bool`, never raises, used for health checks
2. **Operations** - Raise specific exceptions, used for actual work

```python
# ✅ GOOD: is_available() for health checks - never raises
async def is_available(self) -> bool:
    try:
        response = await client.get(f"{self.base_url}/api/tags")
        return response.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False

# ✅ GOOD: Operations raise specific exceptions
async def embed(self, text: str) -> list[float]:
    try:
        response = await client.post(...)
    except httpx.ConnectError:
        raise OllamaNotRunningError(base_url=self.base_url)
    except httpx.TimeoutException:
        raise OllamaTimeoutError(operation="embed", timeout=self.embed_timeout)
```

This enables graceful degradation in health checks:

```python
# Health endpoint shows "degraded" when Ollama down but DB up
if all_healthy:
    overall_status = "healthy"
elif any_healthy:
    overall_status = "degraded"
else:
    overall_status = "unhealthy"
```

### Error Response Format

Python API errors follow a consistent JSON structure:

```json
{
  "error": "error_type_snake_case",
  "message": "Human-readable error description"
}
```

### Logging vs User Messages

```python
# ✅ GOOD: Log technical details, return user-friendly message
async def process_item(item_id: str) -> Item:
    try:
        result = await ai_provider.extract(content)
    except Exception as e:
        logger.error(f"AI extraction failed for {item_id}: {e}", exc_info=True)
        raise ProcessingError("Failed to process content")
```

## HTTP API Error Handling (Frontend)

Frontend service hooks use `apiFetch()` from `src/lib/api-config.ts` to call the Python backend. This helper provides structured error parsing for all HTTP responses.

### Error Parsing Flow

```
Python exception → FastAPI handler → JSON response → apiFetch() → ApiRequestError thrown → TanStack Query
```

### ApiRequestError

`apiFetch()` throws `ApiRequestError` (defined in `src/lib/api-config.ts`) for all non-ok HTTP responses. This structured error extends `Error` with metadata from the response:

| Field     | Type             | Description                                              |
| --------- | ---------------- | -------------------------------------------------------- |
| `message` | `string`         | Human-readable error (extracted from response body)      |
| `status`  | `number`         | HTTP status code (e.g., 404, 422, 500)                   |
| `path`    | `string`         | Request path (e.g., `/api/items/abc-123`)                |
| `code`    | `string \| null` | Backend error code (e.g., `"item_not_found"`) if present |

The error message is extracted from three response formats:

1. **Structured errors** (`{ error, message }`): Uses `message` string, sets `code` from `error`
2. **FastAPI validation errors** (`{ detail: [{ msg, loc, type }] }`): Joins all `msg` values with `; `
3. **Non-JSON errors**: Falls back to `"API request failed ({status})"`

### Using ApiRequestError in Components

Components can use `ApiRequestError` for fine-grained error handling (e.g., distinguishing 404 from generic errors):

```typescript
import { ApiRequestError } from '@/lib/api-config'

// ✅ GOOD: Check error type and status for specific UI
if (
  error instanceof ApiRequestError &&
  error.status === 404 &&
  error.code === 'item_not_found'
) {
  // Show "not found" UI instead of generic error
}
```

See `src/components/items/ItemDetail.tsx` for a working example.

### Error Propagation in Service Hooks

Service hooks log errors via `@/lib/logger` and let them propagate to TanStack Query. No toast notifications in service hooks -- UI components handle user-facing error display.

```typescript
// src/services/items.ts
onError: error => {
  logger.error('Failed to create item', { error })
  // Error propagates to TanStack Query's error state
}
```

### Network Errors

When `fetch()` itself rejects (server unreachable), `apiFetch()` throws a plain `Error` with message `"Network request failed"` (not `ApiRequestError`). This is distinct from HTTP error responses.

## Quick Reference

| Scenario               | Rust Error Type | TypeScript Pattern   | Python Pattern          | User Feedback    |
| ---------------------- | --------------- | -------------------- | ----------------------- | ---------------- |
| Simple command         | `String`        | if/else + toast      | Raise exception         | Toast on error   |
| Multiple failure modes | Structured enum | Match on `.type`     | Custom exception types  | Context-specific |
| Data fetching          | Either          | `unwrapResult`       | Exception handler       | Query error UI   |
| Optional feature       | Either          | Graceful degradation | try/except with default | Silent fallback  |
| Critical operation     | Structured enum | Explicit + rollback  | Transaction rollback    | Toast + recovery |

See also: [tauri-commands.md](../core-systems/tauri-commands.md) for Result type patterns, [logging.md](../quality-tooling/logging.md) for logging best practices.
