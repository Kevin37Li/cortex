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
// ✅ GOOD: Smart retry logic
const { data } = useQuery({
  queryKey: ['data'],
  queryFn: loadData,
  retry: (failureCount, error) => {
    // Don't retry client errors (4xx)
    if (error.message.includes('API error: 4')) return false
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
    pass

class ItemNotFoundError(CortexError):
    """Item does not exist."""
    pass

class ProcessingError(CortexError):
    """Error during content processing."""
    pass

class AIProviderError(CortexError):
    """Error from AI provider."""
    pass
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
        content={"error": "item_not_found", "message": str(exc)}
    )

@app.exception_handler(ProcessingError)
async def processing_error_handler(request: Request, exc: ProcessingError):
    return JSONResponse(
        status_code=500,
        content={"error": "processing_error", "message": str(exc)}
    )

@app.exception_handler(AIProviderError)
async def ai_provider_error_handler(request: Request, exc: AIProviderError):
    return JSONResponse(
        status_code=503,
        content={"error": "ai_provider_error", "message": str(exc)}
    )
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

## Quick Reference

| Scenario               | Rust Error Type | TypeScript Pattern   | Python Pattern          | User Feedback    |
| ---------------------- | --------------- | -------------------- | ----------------------- | ---------------- |
| Simple command         | `String`        | if/else + toast      | Raise exception         | Toast on error   |
| Multiple failure modes | Structured enum | Match on `.type`     | Custom exception types  | Context-specific |
| Data fetching          | Either          | `unwrapResult`       | Exception handler       | Query error UI   |
| Optional feature       | Either          | Graceful degradation | try/except with default | Silent fallback  |
| Critical operation     | Structured enum | Explicit + rollback  | Transaction rollback    | Toast + recovery |

See also: [tauri-commands.md](../core-systems/tauri-commands.md) for Result type patterns, [logging.md](../quality-tooling/logging.md) for logging best practices.
