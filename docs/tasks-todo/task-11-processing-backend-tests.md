# Task: Write Tests for Processing Pipeline

## Summary

Create comprehensive test coverage for the Phase 2 backend: content parsing, semantic chunking, embedding service, metadata extraction, the LangGraph processing workflow, and the processing queue. Tests should cover both success paths and error handling.

## Acceptance Criteria

- [ ] `tests/test_services_parsing.py` — Tests for `ContentParser` (HTML parsing, plain text, malformed HTML, empty input)
- [ ] `tests/test_services_chunking.py` — Tests for `ChunkingService` (short text, long text, empty text, chunk overlap verification)
- [ ] `tests/test_services_embeddings.py` — Tests for `EmbeddingService` (batch embedding, model consistency check, provider error wrapping)
- [ ] `tests/test_services_extraction.py` — Tests for `MetadataExtractor` (valid extraction, JSON parse failure fallback, provider error handling)
- [ ] `tests/test_workflows_processing.py` — Tests for the LangGraph processing workflow (happy path, retry on validation failure, max retries exceeded)
- [ ] `tests/test_api_processing.py` — Tests for processing API endpoints (queue status, retry)
- [ ] All tests use mocked AI providers (no real Ollama/OpenAI calls)
- [ ] Coverage > 80% for new modules
- [ ] All existing tests continue to pass

## Dependencies

- Tasks 1-10: All Phase 2 backend tasks complete
- Phase 1: Test infrastructure (`conftest.py`, fixtures, async test pattern)

## Technical Notes

- Follow the test patterns from Phase 1: `test_repositories.py`, `test_api_items.py`
- Mock `AIProvider` for all tests — create a `MockProvider` that returns deterministic embeddings and chat responses
- For HTML parsing tests, use small HTML snippets (not full web pages)
- For workflow tests, mock all services to test orchestration logic
- Use `pytest.fixture` for shared setup (MockProvider, database connections)
- Per `docs/developer/quality-tooling/testing.md`: test both success and error paths

## Mock Provider Pattern

```python
class MockAIProvider(AIProvider):
    """Mock provider for testing."""

    async def embed(self, text: str) -> list[float]:
        return [0.1] * 768  # Deterministic 768-dim vector

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 768 for _ in texts]

    async def chat(self, messages: list[dict], system: str | None = None) -> str:
        return json.dumps({
            "summary": "Test summary",
            "concepts": ["concept1", "concept2"],
            "entities": ["entity1"],
        })

    async def stream_chat(self, messages, system=None):
        yield "Test response"
```

## Test Outline

```python
# test_services_parsing.py
class TestContentParser:
    def test_parse_html_extracts_article(self): ...
    def test_parse_html_strips_scripts_and_styles(self): ...
    def test_parse_html_extracts_title(self): ...
    def test_parse_html_handles_malformed(self): ...
    def test_parse_text_passthrough(self): ...
    def test_parse_empty_content(self): ...
    def test_parse_dispatches_by_content_type(self): ...

# test_services_chunking.py
class TestChunkingService:
    def test_short_text_single_chunk(self): ...
    def test_long_text_multiple_chunks(self): ...
    def test_empty_text_no_chunks(self): ...
    def test_chunk_overlap(self): ...
    def test_respects_paragraph_boundaries(self): ...
    def test_token_estimation(self): ...

# test_services_embeddings.py
class TestEmbeddingService:
    async def test_embed_chunks_stores_vectors(self): ...
    async def test_embed_query_returns_vector(self): ...
    async def test_model_mismatch_raises(self): ...
    async def test_provider_error_wrapped(self): ...
    async def test_batch_processing(self): ...

# test_services_extraction.py
class TestMetadataExtractor:
    async def test_extract_valid_json(self): ...
    async def test_extract_invalid_json_fallback(self): ...
    async def test_extract_provider_error(self): ...
    async def test_extract_with_title(self): ...

# test_workflows_processing.py
class TestProcessingWorkflow:
    async def test_happy_path(self): ...
    async def test_retry_on_validation_failure(self): ...
    async def test_max_retries_exceeded(self): ...
    async def test_error_sets_failed_status(self): ...

# test_api_processing.py
class TestProcessingEndpoints:
    async def test_get_queue_status(self): ...
    async def test_retry_all_failed(self): ...
    async def test_retry_specific_item(self): ...
```

## Files to Create

- `python-backend/tests/test_services_parsing.py`
- `python-backend/tests/test_services_chunking.py`
- `python-backend/tests/test_services_embeddings.py`
- `python-backend/tests/test_services_extraction.py`
- `python-backend/tests/test_workflows_processing.py`
- `python-backend/tests/test_api_processing.py`
- `python-backend/tests/conftest.py` — Add `MockAIProvider` fixture (modify existing)

## Verification

```bash
cd python-backend
uv run pytest -v
uv run pytest --cov=src --cov-report=term-missing
uv run pytest --cov=src --cov-fail-under=80
```
