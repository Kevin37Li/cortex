# Task: Add Processing Error Types and Exception Handler

## Summary

Add `ProcessingError` and related exception types to `exceptions.py` and register the FastAPI exception handler in `main.py`. This is the foundational error handling layer for the entire content processing pipeline.

## Acceptance Criteria

- [ ] `ProcessingError` base exception class added to `exceptions.py` (extends `CortexError`)
- [ ] `ContentParsingError` subclass for HTML/text parsing failures
- [ ] `ChunkingError` subclass for text splitting failures
- [ ] `EmbeddingError` subclass for embedding generation failures (distinct from `AIProviderError`)
- [ ] `MetadataExtractionError` subclass for LLM extraction failures
- [ ] `EmbeddingModelMismatchError` for dimension/model consistency violations
- [ ] FastAPI exception handler registered in `main.py` returning 422 for processing errors
- [ ] Each exception includes contextual data (item_id, step name, original error)

## Dependencies

- Phase 1 complete: `exceptions.py` exists with `CortexError`, `ItemNotFoundError`, `DatabaseError`, `AIProviderError` hierarchy

## Technical Notes

- Follow the exception hierarchy pattern established by `AIProviderError` in Phase 1
- Processing errors are distinct from AI provider errors — provider errors mean "can't reach AI", processing errors mean "content couldn't be processed"
- Exception handler should return 422 (Unprocessable Entity) with structured error body: `{"error": "processing_error", "message": "...", "step": "...", "item_id": "..."}`
- Pattern reference: `src/exceptions.py:35-75` (existing `AIProviderError` hierarchy)

## Exception Hierarchy

```
CortexError
├── AIProviderError (existing)
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

- `python-backend/src/exceptions.py` — Add processing exception classes
- `python-backend/src/main.py` — Register `ProcessingError` exception handler

## Verification

```bash
cd python-backend
uv run pytest -v  # Existing tests still pass
uv run ruff check src/
uv run mypy src/
```
