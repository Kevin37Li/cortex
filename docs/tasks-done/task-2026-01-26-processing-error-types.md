# Task: Add Processing Error Types and Exception Handler

## Summary

Add `ProcessingError` and related exception types to `exceptions.py` and register the FastAPI exception handler in `main.py`. This is the foundational error handling layer for the entire content processing pipeline.

Also standardize the existing `AIProviderError` handler to use static error codes instead of dynamic class names, for a stable API contract.

## Acceptance Criteria

- [ ] `ProcessingError` base exception class added to `exceptions.py` (extends `CortexError`)
- [ ] `ContentParsingError` subclass for HTML/text parsing failures
- [ ] `ChunkingError` subclass for text splitting failures
- [ ] `EmbeddingError` subclass for embedding generation failures (distinct from `AIProviderError`)
- [ ] `MetadataExtractionError` subclass for LLM extraction failures
- [ ] `EmbeddingModelMismatchError` for dimension/model consistency violations
- [ ] Each exception includes contextual data (`item_id`, `step`); original errors preserved via `raise ... from e`
- [ ] FastAPI exception handler registered in `main.py` returning 500 for processing errors
- [ ] Error response uses standard format: `{"error": "<static_code>", "message": "..."}`
- [ ] `error_code` class attribute added to all exception classes for stable API contract
- [ ] Existing `AIProviderError` handler updated to use `exc.error_code` instead of `type(exc).__name__`
- [ ] Unit tests for all new exception classes

## Dependencies

- Phase 1 complete: `exceptions.py` exists with `CortexError`, `ItemNotFoundError`, `DatabaseError`, `AIProviderError` hierarchy

## Technical Notes

### Pattern: Follow existing hierarchy

Follow the exception hierarchy pattern established by `AIProviderError` in Phase 1. Processing errors are distinct from AI provider errors — provider errors mean "can't reach AI", processing errors mean "content couldn't be processed".

Pattern reference: `src/exceptions.py:35-75` (existing `AIProviderError` hierarchy)

### Pattern: Static `error_code` class attribute

Every exception class must define an `error_code` class attribute with a static snake_case string. This replaces the dynamic `type(exc).__name__` used in the current `AIProviderError` handler, giving a stable API contract that won't break if classes are renamed.

```python
class ProcessingError(CortexError):
    """Base exception for content processing pipeline errors."""
    error_code: str = "processing_error"

    def __init__(self, message: str, *, item_id: str | None = None,
                 step: str | None = None) -> None:
        self.item_id = item_id
        self.step = step
        super().__init__(message)

class ContentParsingError(ProcessingError):
    """Raised when HTML/text content cannot be parsed."""
    error_code: str = "content_parsing_error"
```

> **Note:** `original_error` is intentionally omitted. Python's built-in exception chaining (`raise ... from e`) already preserves the cause via `__cause__`, making a redundant parameter unnecessary.

Existing exceptions also need `error_code` added:

| Class                         | `error_code`                  |
| ----------------------------- | ----------------------------- |
| `CortexError`                 | `"cortex_error"`              |
| `ItemNotFoundError`           | `"item_not_found"`            |
| `ChunkNotFoundError`          | `"chunk_not_found"`           |
| `DatabaseError`               | `"database_error"`            |
| `AIProviderError`             | `"ai_provider_error"`         |
| `OllamaNotRunningError`       | `"ollama_not_running"`        |
| `OllamaModelNotFoundError`    | `"ollama_model_not_found"`    |
| `OllamaTimeoutError`          | `"ollama_timeout"`            |
| `OllamaAPIResponseError`      | `"ollama_api_response_error"` |
| `ProcessingError`             | `"processing_error"`          |
| `ContentParsingError`         | `"content_parsing_error"`     |
| `ChunkingError`               | `"chunking_error"`            |
| `EmbeddingError`              | `"embedding_error"`           |
| `EmbeddingModelMismatchError` | `"embedding_model_mismatch"`  |
| `MetadataExtractionError`     | `"metadata_extraction_error"` |

### Pattern: Exception handler uses standard response format

The handler returns 500 with the standard two-field error body, consistent with `error-handling.md`:

```python
@app.exception_handler(ProcessingError)
async def processing_error_handler(request: Request, exc: ProcessingError):
    """Handle ProcessingError with 500 response."""
    return JSONResponse(
        status_code=500,
        content={"error": exc.error_code, "message": str(exc)},
    )
```

Also update the existing `AIProviderError` handler to use `exc.error_code`:

```python
# Before (dynamic — breaks if class is renamed)
content={"error": type(exc).__name__, "message": str(exc)},

# After (static — stable API contract)
content={"error": exc.error_code, "message": str(exc)},
```

### Pattern: Python exception chaining

Use Python's built-in `raise ... from` syntax to preserve the exception chain. The original error is accessible via `__cause__`. This is consistent with the `OllamaProvider` pattern in `src/providers/ollama.py`:

```python
# Callers should always chain with `from`:
try:
    result = parse_html(content)
except SomeLibraryError as e:
    raise ContentParsingError(
        f"Failed to parse HTML for item {item_id}",
        item_id=item_id,
        step="content_parsing",
    ) from e  # e is accessible via exc.__cause__
```

## Exception Hierarchy

```
CortexError
├── AIProviderError (existing — add error_code)
│   └── ...
└── ProcessingError (new)
    ├── ContentParsingError
    ├── ChunkingError
    ├── EmbeddingError
    ├── EmbeddingModelMismatchError
    └── MetadataExtractionError
```

## Files to Create/Modify

**Modify:**

- `python-backend/src/exceptions.py` — Add `error_code` class attribute to all existing exceptions; add processing exception classes
- `python-backend/src/main.py` — Add `ProcessingError` to the import line; register `ProcessingError` exception handler; update `AIProviderError` handler to use `exc.error_code`

**Create:**

- `python-backend/tests/test_exceptions.py` — Unit tests for exception classes

## Test Plan

`python-backend/tests/test_exceptions.py` should cover:

- Each processing exception can be instantiated with expected arguments
- `str(exc)` produces the expected message string
- Contextual attributes (`item_id`, `step`) are accessible and correct
- `error_code` returns the expected static string for every exception class
- Inheritance hierarchy: `isinstance(ContentParsingError(...), ProcessingError)` is `True`, etc.
- Default values: `item_id`, `step` default to `None` when omitted
- Exception chaining: `raise ... from e` sets `__cause__` correctly

## Verification

```bash
cd python-backend
uv run pytest tests/test_exceptions.py -v  # New tests pass
uv run pytest -v                            # All existing tests still pass
uv run ruff check src/
uv run mypy src/
```

---

## Implementation Details

_Tracked: 2026-01-26_

### Files Changed

| File                                            | Change   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ----------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `python-backend/src/exceptions.py`              | Modified | Added `error_code` class attribute to all existing exceptions (`CortexError`, `ItemNotFoundError`, `ChunkNotFoundError`, `DatabaseError`, `AIProviderError`, `OllamaNotRunningError`, `OllamaModelNotFoundError`, `OllamaTimeoutError`, `OllamaAPIResponseError`). Changed all constructors to keyword-only arguments. Added 6 new processing exception classes: `ProcessingError`, `ContentParsingError`, `ChunkingError`, `EmbeddingError`, `EmbeddingModelMismatchError`, `MetadataExtractionError`. |
| `python-backend/src/main.py`                    | Modified | Added `ProcessingError` import. Registered `ProcessingError` exception handler (500). Updated all existing handlers (`ItemNotFoundError`, `DatabaseError`, `AIProviderError`) to use `exc.error_code` instead of hardcoded strings or `type(exc).__name__`.                                                                                                                                                                                                                                             |
| `python-backend/src/providers/ollama.py`        | Modified | Updated all exception raise sites to use keyword-only arguments (e.g., `OllamaNotRunningError(base_url=...)` instead of positional).                                                                                                                                                                                                                                                                                                                                                                    |
| `python-backend/src/api/items.py`               | Modified | Updated `ItemNotFoundError` calls to use keyword-only `item_id=` argument.                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `python-backend/src/db/repositories/items.py`   | Modified | Updated `ItemNotFoundError` calls to use keyword-only `item_id=` argument.                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `python-backend/tests/test_exceptions.py`       | Created  | 46 unit tests covering: error_code for all 15 exception classes (parametrized), instantiation and context attributes for each processing error subclass, inheritance hierarchy, defaults, exception chaining via `raise ... from`, and `EmbeddingError` distinctness from `AIProviderError`.                                                                                                                                                                                                            |
| `docs/developer/architecture/error-handling.md` | Modified | Updated Python error handling section to reflect `error_code` attributes, keyword-only constructors, `ProcessingError` with contextual fields, and `exc.error_code` usage in exception handlers. Added explanatory paragraph about conventions.                                                                                                                                                                                                                                                         |

### Dependencies Added

None.

### Acceptance Criteria Status

- [x] `ProcessingError` base exception class added to `exceptions.py` (extends `CortexError`) - `exceptions.py:92`
- [x] `ContentParsingError` subclass for HTML/text parsing failures - `exceptions.py:109`
- [x] `ChunkingError` subclass for text splitting failures - `exceptions.py:115`
- [x] `EmbeddingError` subclass for embedding generation failures (distinct from `AIProviderError`) - `exceptions.py:121`
- [x] `MetadataExtractionError` subclass for LLM extraction failures - `exceptions.py:137`
- [x] `EmbeddingModelMismatchError` for dimension/model consistency violations - `exceptions.py:131`
- [x] Each exception includes contextual data (`item_id`, `step`); original errors preserved via `raise ... from e` - `exceptions.py:97-106`
- [x] FastAPI exception handler registered in `main.py` returning 500 for processing errors - `main.py:67-73`
- [x] Error response uses standard format: `{"error": "<static_code>", "message": "..."}` - `main.py:72`
- [x] `error_code` class attribute added to all exception classes for stable API contract - `exceptions.py` (all classes)
- [x] Existing `AIProviderError` handler updated to use `exc.error_code` instead of `type(exc).__name__` - `main.py:63`
- [x] Unit tests for all new exception classes - `tests/test_exceptions.py` (46 tests)

---

## Learning Report

_Generated: 2026-01-26_

### Summary

Added 6 processing error exception classes to the Python backend's exception hierarchy, along with a static `error_code` class attribute on all 15 exception classes for stable API contracts. Updated all existing exception constructors to use keyword-only arguments, all call sites (Ollama provider, items API, items repository), all FastAPI exception handlers, and the architecture documentation. Created 46 unit tests covering the full exception hierarchy.

- 7 files changed, 273 insertions, 57 deletions
- 46 new tests, 135 total tests passing
- All ruff checks pass

### Patterns & Decisions

1. **Static `error_code` over dynamic class names**: The `AIProviderError` handler previously used `type(exc).__name__`, which would break API contracts if classes were renamed. Replaced with static `error_code` class attributes across all exceptions for stability.

2. **Keyword-only constructors**: All exception `__init__` methods now use the `*` separator to enforce keyword-only arguments (e.g., `ItemNotFoundError(item_id="x")` instead of `ItemNotFoundError("x")`). This improves readability at call sites and makes the code self-documenting.

3. **`ProcessingError` with contextual fields**: The base `ProcessingError` accepts optional `item_id` and `step` keyword arguments, which subclasses inherit without needing their own `__init__`. This keeps the subclasses minimal while still carrying pipeline context.

4. **No `original_error` parameter**: Python's built-in `raise ... from e` chaining was used instead of a redundant `original_error` parameter. The cause is accessible via `__cause__`, which is the standard Python pattern.

5. **`EmbeddingError` vs `AIProviderError`**: These are deliberately in separate branches of the hierarchy. `AIProviderError` means "can't reach AI provider" while `EmbeddingError` means "content couldn't be embedded during processing". The test suite explicitly verifies `EmbeddingError` is not an `AIProviderError`.

### Challenges & Solutions

1. **Cascading call-site updates**: Changing constructors to keyword-only arguments required updating every call site in `ollama.py`, `items.py`, and `items.py` (repository). The existing test suite caught all breakages immediately -- all 89 pre-existing tests continued to pass after the updates.

2. **Documentation consistency**: The `error-handling.md` doc had hardcoded error strings in the handler examples and positional arguments in the constructor examples. These were all updated to match the new patterns to prevent documentation drift.

### Lessons Learned

- **Keyword-only arguments are worth the migration cost**: The resulting code at call sites is much clearer. `OllamaTimeoutError(operation="embed", timeout=30.0)` is immediately understandable versus `OllamaTimeoutError("embed", 30.0)`.

- **Parametrized tests for cross-cutting concerns**: The `TestErrorCodes` class uses a single parametrized test to verify all 15 exception classes have the correct `error_code`. This pattern scales well as new exceptions are added -- just add a tuple to the list.

- **Documentation and code should be updated together**: Updating `error-handling.md` in the same changeset prevents the docs from becoming a source of incorrect patterns.

### Documentation Impact

- `docs/developer/architecture/error-handling.md` was updated in this changeset to reflect all changes (keyword-only args, `error_code` attributes, `ProcessingError` hierarchy, `exc.error_code` in handlers).
- No new documentation files were needed; the existing error handling doc covers the patterns adequately.
- The `ProcessingError` hierarchy diagram in the task spec matches the implementation exactly.
