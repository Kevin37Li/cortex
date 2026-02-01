# Task: Implement Metadata Extraction Service

## Summary

Create a metadata extraction service that uses LLM chat to extract structured metadata from parsed content: a concise summary, key concepts/topics, and named entities (people, organizations, places). This is the "Extract" node in the processing workflow.

## Acceptance Criteria

- [x] `services/extraction.py` created with `MetadataExtractor` class
- [x] `async def extract(text: str, title: str | None = None) -> ExtractedMetadata` — Extracts metadata using LLM (async to await AIProvider.chat)
- [x] `ExtractedMetadata` Pydantic model with fields: `summary` (str, 2-3 sentences), `concepts` (list[str], key topics), `entities` (list[str], named entities)
- [x] Uses `AIProvider.chat()` with a structured prompt for extraction
- [x] Prompt instructs the LLM to return JSON for reliable parsing
- [x] Handles LLM response parsing failures gracefully (returns partial metadata, logs warning)
- [x] Handles provider unavailability: wraps `AIProviderError` into `MetadataExtractionError` using `raise ... from e` chaining
- [x] Works with both local (Ollama) and cloud (OpenAI) providers via the `AIProvider` interface
- [x] Includes logging with `logger = logging.getLogger(__name__)` matching existing service patterns
- [x] Truncates long texts to ~3000 tokens (~12,000 characters) to fit model context
- [x] Unit tests cover valid JSON parsing, partial/malformed JSON handling, and text truncation

## Dependencies

- Phase 1 complete: `AIProvider.chat()` interface, `OllamaProvider` implementation
- Task 1: `MetadataExtractionError` exception type
- Task 3: Content parsing provides the clean text input

## Technical Notes

- The LLM prompt should request JSON output for reliable parsing
- Use a system prompt that defines the extraction task clearly
- For MVP, a single LLM call extracts all three fields (summary, concepts, entities)
- If JSON parsing fails, attempt to extract what we can from the raw response
- This is a relatively expensive operation (full LLM inference) — should be called once per item, not per chunk
- Input is the full parsed text (not individual chunks)
- Truncate very long texts to fit model context (first ~3000 tokens, approximately 12,000 characters)
- Include standard logging: `logger.debug()` for operation start, `logger.warning()` for parsing failures
- Use `raise MetadataExtractionError(message, step="metadata_extraction") from e` when wrapping `AIProviderError` to preserve error chain

## ExtractedMetadata Model

Place in `python-backend/src/db/models.py` alongside other processing result models (ParsedContent, ChunkResult):

```python
from pydantic import BaseModel, Field

class ExtractedMetadata(BaseModel):
    """Metadata extracted from content via LLM."""
    summary: str = ""  # 2-3 sentence summary (default empty for partial results)
    concepts: list[str] = Field(default_factory=list)  # Key topics/concepts (3-7 items)
    entities: list[str] = Field(default_factory=list)  # Named entities: people, orgs, places (0-10 items)
```

## Extraction Prompt

```python
EXTRACTION_SYSTEM_PROMPT = """You are a knowledge extraction assistant. Given a piece of content, extract:
1. A concise summary (2-3 sentences)
2. Key concepts/topics (3-7 items)
3. Named entities: people, organizations, places (if any)

Respond ONLY with valid JSON in this exact format:
{
    "summary": "...",
    "concepts": ["concept1", "concept2", ...],
    "entities": ["entity1", "entity2", ...]
}"""

EXTRACTION_USER_PROMPT = """Extract metadata from the following content:
{title_section}
Content:
{text}"""

# Build prompt with optional title
def _build_user_prompt(self, text: str, title: str | None) -> str:
    title_section = f"\nTitle: {title}\n" if title else ""
    return EXTRACTION_USER_PROMPT.format(title_section=title_section, text=text)
```

## Text Truncation

```python
MAX_EXTRACTION_CHARS = 12000  # ~3000 tokens at 4 chars/token

def _truncate_text(self, text: str) -> str:
    """Truncate text to fit model context window."""
    if len(text) <= MAX_EXTRACTION_CHARS:
        return text
    return text[:MAX_EXTRACTION_CHARS] + "..."
```

## Files to Create/Modify

**Create:**

- `python-backend/src/services/extraction.py` — Metadata extraction service
- `python-backend/tests/services/test_extraction.py` — Unit tests for extraction service

**Modify:**

- `python-backend/src/db/models.py` — Add `ExtractedMetadata` model
- `python-backend/src/services/__init__.py` — Export `MetadataExtractor` class

## Unit Tests

Create `python-backend/tests/services/test_extraction.py` with tests using MockAIProvider:

```python
import pytest
from src.services import MetadataExtractor
from src.db.models import ExtractedMetadata

class MockAIProvider:
    """Mock provider for testing extraction service."""
    def __init__(self, response: str):
        self.response = response

    async def chat(self, prompt: str, system: str | None = None) -> str:
        return self.response

@pytest.mark.asyncio
async def test_extract_valid_json():
    """Test extraction with valid JSON response."""
    mock_response = '{"summary": "Test summary.", "concepts": ["AI"], "entities": ["OpenAI"]}'
    provider = MockAIProvider(mock_response)
    extractor = MetadataExtractor(provider)
    result = await extractor.extract("Test content")
    assert result.summary == "Test summary."
    assert result.concepts == ["AI"]

@pytest.mark.asyncio
async def test_extract_partial_json():
    """Test graceful handling of malformed JSON."""
    provider = MockAIProvider("Invalid JSON response")
    extractor = MetadataExtractor(provider)
    result = await extractor.extract("Test content")
    # Should return empty defaults, not raise
    assert isinstance(result, ExtractedMetadata)

@pytest.mark.asyncio
async def test_truncate_long_text():
    """Test text truncation for long inputs."""
    provider = MockAIProvider('{"summary": "", "concepts": [], "entities": []}')
    extractor = MetadataExtractor(provider)
    long_text = "x" * 20000
    result = await extractor.extract(long_text)
    # Should complete without error (text was truncated)
    assert isinstance(result, ExtractedMetadata)
```

## Verification

```bash
cd python-backend
uv run ruff check src/
uv run mypy src/

# Manual test (requires Ollama running with llama3.2):
uv run python -c "
import asyncio
from src.services import MetadataExtractor
from src.providers import OllamaProvider

async def test():
    provider = OllamaProvider()
    extractor = MetadataExtractor(provider)
    result = await extractor.extract(
        'Machine learning is a subset of artificial intelligence. It enables computers to learn from data without being explicitly programmed. Deep learning, a type of ML, uses neural networks with many layers.',
        title='Introduction to ML'
    )
    print(f'Summary: {result.summary}')
    print(f'Concepts: {result.concepts}')
    print(f'Entities: {result.entities}')

asyncio.run(test())
"
```

---

## Implementation Details

_Tracked: 2026-02-01_

### Files Changed

| File                                               | Change   | Description                                         |
| -------------------------------------------------- | -------- | --------------------------------------------------- |
| `python-backend/src/services/extraction.py`        | Created  | MetadataExtractor class with LLM-based extraction   |
| `python-backend/tests/services/test_extraction.py` | Created  | Comprehensive unit tests (328 lines, 18 test cases) |
| `python-backend/src/db/models.py`                  | Modified | Added ExtractedMetadata Pydantic model              |
| `python-backend/src/services/__init__.py`          | Modified | Exported MetadataExtractor class                    |

### Dependencies Added

- None (uses existing AIProvider interface and exceptions)

### Acceptance Criteria Status

- [x] `services/extraction.py` created with `MetadataExtractor` class - Implemented in `extraction.py:34`
- [x] `async def extract(text: str, title: str | None = None) -> ExtractedMetadata` - Implemented in `extraction.py:49`
- [x] `ExtractedMetadata` Pydantic model with fields - Implemented in `models.py:29-36`
- [x] Uses `AIProvider.chat()` with a structured prompt - Implemented in `extraction.py:76-79`
- [x] Prompt instructs LLM to return JSON - Implemented in `extraction.py:16-26`
- [x] Handles LLM response parsing failures gracefully - Implemented in `extraction.py:118-159`
- [x] Handles provider unavailability with error chaining - Implemented in `extraction.py:80-84`
- [x] Works with both local and cloud providers - Uses AIProvider interface
- [x] Includes logging with `logger = logging.getLogger(__name__)` - Implemented in `extraction.py:11`
- [x] Truncates long texts to ~12,000 characters - Implemented in `extraction.py:89-103`
- [x] Unit tests cover valid JSON parsing, partial/malformed JSON, and truncation - All 18 tests in `test_extraction.py`

---

## Learning Report

_Generated: 2026-02-01_

### Summary

Implemented a metadata extraction service that uses LLM chat to extract structured metadata (summary, concepts, entities) from content. The implementation follows the established service pattern in the codebase and includes comprehensive error handling for LLM response parsing. Total: 4 files changed, ~540 lines added, 18 test cases.

### Patterns & Decisions

**1. Robust JSON Extraction Strategy**
The implementation uses a three-tier approach to extract JSON from LLM responses:

1. `json.JSONDecoder.raw_decode()` for responses starting with `{` - handles braces inside string literals correctly
2. Regex for markdown code blocks (`json ... `) - handles LLMs that wrap output in code blocks
3. Simple regex fallback for any `{...}` pattern - catches remaining cases

This was chosen because LLMs are unpredictable in their output format, even with explicit JSON instructions.

**2. Defensive Type Validation**
Rather than trusting the LLM to return correct types, the implementation validates every field:

- `summary` must be a string, otherwise defaults to `""`
- `concepts`/`entities` must be lists, with non-string items filtered out
- Non-object JSON (arrays) returns empty defaults rather than crashing

**3. Empty Content Short-Circuit**
Empty or whitespace-only content returns empty metadata immediately without calling the LLM, avoiding unnecessary API calls and potential errors.

**4. Error Chaining Pattern**
Followed the established `raise ... from e` pattern to wrap `AIProviderError` into `MetadataExtractionError`, preserving the error chain for debugging while providing domain-specific errors to callers.

### Challenges & Solutions

**1. JSON Extraction with Braces in String Values**
Initial simple regex `\{.*?\}` would fail on JSON like `{"summary": "Uses {config} syntax"}`. Solved by using `json.JSONDecoder.raw_decode()` first, which properly parses JSON strings before falling back to regex patterns.

**2. Mock Provider Interface Compatibility**
The `AIProvider` protocol requires all methods (`embed`, `embed_batch`, `chat`, `stream_chat`). Created a `MockAIProvider` class that implements all methods but only uses `chat` for testing, keeping tests focused while satisfying the interface.

**3. Test Organization**
Organized 18 test cases into 7 logical test classes (TestExtractValidJson, TestExtractPartialJson, TestTextTruncation, TestEmptyContent, TestProviderErrors, TestSystemPrompt) for better discoverability and maintenance.

### Lessons Learned

**What Worked Well:**

- The task spec provided excellent examples for prompts and truncation logic, reducing implementation guesswork
- Following established service patterns (ContentParser, ChunkingService) made the structure predictable
- Writing tests class-by-class helped ensure comprehensive coverage of edge cases

**Recommendations for Future Tasks:**

- When dealing with LLM output parsing, always plan for multiple fallback strategies
- Consider adding structured output support (if provider supports it) in future iterations to reduce parsing complexity
- The MockAIProvider pattern could be extracted to a shared test fixture

### Documentation Impact

- **No existing docs need updates** - the implementation follows all documented patterns
- **New pattern worth documenting**: The three-tier JSON extraction strategy could be added to AI provider documentation if other services need similar LLM response parsing
- **Helpful documentation**: The service patterns in `docs/developer/python-backend/architecture.md` were well-aligned with implementation needs
