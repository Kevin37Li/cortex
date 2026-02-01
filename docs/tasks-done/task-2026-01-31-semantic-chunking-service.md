# Task: Implement Semantic Chunking Service

## Summary

Create a chunking service that splits parsed text content into semantic chunks suitable for embedding. Uses LangChain's `RecursiveCharacterTextSplitter` to respect document structure (paragraphs, sentences) while targeting 200-500 tokens per chunk with overlap for context continuity.

## Acceptance Criteria

- [ ] `ChunkResult` model added to `src/db/models.py` (not in service file)
- [ ] `services/chunking.py` created with `ChunkingService` class
- [ ] `chunk_text(text: str) -> list[ChunkResult]` — Splits text into semantic chunks
- [ ] `ChunkResult` model with fields: `content` (chunk text), `chunk_index` (0-based position), `token_count` (estimated)
- [ ] Targets 200-500 tokens per chunk (configurable via settings)
- [ ] 50-token overlap between consecutive chunks (configurable via settings)
- [ ] Respects document structure: splits at `\n\n` > `\n` > `. ` > ` ` hierarchy
- [ ] Short content (< 200 tokens) returns a single chunk
- [ ] Empty content returns empty list
- [ ] Token counting uses a fast approximation (word count × 1.3) — exact tokenization not needed at MVP
- [ ] Error handling with `ChunkingError` for splitter failures
- [ ] Logging for debug/error cases
- [ ] Service exported from `services/__init__.py`
- [ ] Unit tests in `tests/services/test_chunking.py`

## Dependencies

- Phase 1 complete: Python backend project structure, `config.py` with `chunk_size` and `chunk_overlap` settings
- Task 3 (Content Parsing): Provides the clean text to chunk (but chunking service is independently testable)

## Technical Notes

- Use `langchain-text-splitters` package for `RecursiveCharacterTextSplitter`
- Add dependency to `pyproject.toml`: `langchain-text-splitters`
- Settings already exist in `config.py`: `chunk_size: int = 500`, `chunk_overlap: int = 50`
- The splitter uses character count but we configure it to approximate tokens
- This is the "Chunk" node in the LangGraph processing workflow
- Per `docs/developer/ai/embeddings.md`: target 200-500 tokens, 50-token overlap, semantic boundaries
- `ChunkingError` already exists in `src/exceptions.py` — use it for error handling

### Token Approximation (MVP)

The approximation `word_count * 1.3` is an MVP simplification. Actual tokenizer behavior varies by model. This may need refinement based on real-world usage, but is acceptable for initial implementation.

## ChunkResult Model

Add to `src/db/models.py`:

```python
class ChunkResult(BaseModel):
    """A single chunk produced by the chunking service."""
    content: str
    chunk_index: int
    token_count: int
```

## Implementation Pattern

```python
# services/chunking.py
import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import settings
from src.db.models import ChunkResult
from src.exceptions import ChunkingError

logger = logging.getLogger(__name__)


class ChunkingService:
    """Service for splitting text into semantic chunks suitable for embedding.

    Uses RecursiveCharacterTextSplitter to respect document structure while
    targeting configurable chunk sizes with overlap for context continuity.
    """

    def __init__(self) -> None:
        """Initialize the chunking service with configured splitter."""
        # Approximate: 1 token ≈ 4 characters
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size * 4,  # Convert tokens to chars
            chunk_overlap=settings.chunk_overlap * 4,
            separators=["\n\n", "\n", ". ", " "],
            length_function=len,
        )

    def chunk_text(self, text: str) -> list[ChunkResult]:
        """Split text into semantic chunks.

        Args:
            text: The text content to split into chunks.

        Returns:
            List of ChunkResult objects. Empty list if input is empty/whitespace.

        Raises:
            ChunkingError: If the text splitter fails unexpectedly.
        """
        if not text or not text.strip():
            return []

        try:
            chunks = self._splitter.split_text(text)
            logger.debug(f"Split text into {len(chunks)} chunks")

            return [
                ChunkResult(
                    content=chunk,
                    chunk_index=i,
                    token_count=self._estimate_tokens(chunk),
                )
                for i, chunk in enumerate(chunks)
            ]
        except Exception as e:
            logger.exception("Failed to chunk text")
            raise ChunkingError(
                message="Failed to split text into chunks",
                details={"error": str(e), "text_length": len(text)},
            ) from e

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Approximate token count using word count heuristic.

        Note: This is an MVP approximation (word_count * 1.3). Actual tokenizer
        behavior varies by model and may need refinement based on usage.

        Args:
            text: The text to estimate token count for.

        Returns:
            Estimated token count.
        """
        return int(len(text.split()) * 1.3)
```

## Files to Create/Modify

**Create:**

- `python-backend/src/services/chunking.py` — Chunking service
- `python-backend/tests/services/test_chunking.py` — Unit tests

**Modify:**

- `python-backend/pyproject.toml` — Add `langchain-text-splitters`
- `python-backend/src/db/models.py` — Add `ChunkResult` model
- `python-backend/src/services/__init__.py` — Export `ChunkingService`

## Unit Tests

Create `tests/services/test_chunking.py` with test cases:

```python
import pytest

from src.db.models import ChunkResult
from src.exceptions import ChunkingError
from src.services.chunking import ChunkingService


class TestChunkingService:
    """Tests for ChunkingService."""

    @pytest.fixture
    def service(self) -> ChunkingService:
        """Create a ChunkingService instance."""
        return ChunkingService()

    def test_empty_input_returns_empty_list(self, service: ChunkingService) -> None:
        """Empty or whitespace input should return empty list."""
        assert service.chunk_text("") == []
        assert service.chunk_text("   ") == []
        assert service.chunk_text("\n\n") == []

    def test_short_content_returns_single_chunk(self, service: ChunkingService) -> None:
        """Short content below chunk size returns single chunk."""
        chunks = service.chunk_text("Hello world.")
        assert len(chunks) == 1
        assert chunks[0].content == "Hello world."
        assert chunks[0].chunk_index == 0
        assert chunks[0].token_count > 0

    def test_long_content_produces_multiple_chunks(self, service: ChunkingService) -> None:
        """Long content is split into multiple chunks with sequential indices."""
        long_text = ("This is a paragraph about AI. " * 50 + "\n\n") * 5
        chunks = service.chunk_text(long_text)

        assert len(chunks) > 1
        # Verify indices are sequential
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_chunks_have_reasonable_token_counts(self, service: ChunkingService) -> None:
        """Chunks should have token counts within expected range."""
        long_text = ("This is a test sentence. " * 100 + "\n\n") * 3
        chunks = service.chunk_text(long_text)

        for chunk in chunks:
            assert chunk.token_count > 0
            # Token count should be reasonable (not exceeding 2x target)
            assert chunk.token_count < 1000

    def test_respects_paragraph_separators(self, service: ChunkingService) -> None:
        """Chunks should preferentially split at paragraph boundaries."""
        text = "First paragraph content.\n\nSecond paragraph content."
        chunks = service.chunk_text(text)

        # Short enough to be one chunk, but demonstrates separator handling
        assert len(chunks) >= 1
        assert chunks[0].content  # Has content

    def test_chunk_result_fields(self, service: ChunkingService) -> None:
        """ChunkResult should have all required fields."""
        chunks = service.chunk_text("Test content for chunking.")

        chunk = chunks[0]
        assert isinstance(chunk, ChunkResult)
        assert isinstance(chunk.content, str)
        assert isinstance(chunk.chunk_index, int)
        assert isinstance(chunk.token_count, int)
```

## Verification

```bash
cd python-backend
uv sync
uv run pytest tests/services/test_chunking.py -v

# Manual verification
uv run python -c "
from src.services.chunking import ChunkingService
svc = ChunkingService()

# Short text → single chunk
chunks = svc.chunk_text('Hello world.')
print(f'Short: {len(chunks)} chunk(s)')

# Long text → multiple chunks
long_text = ('This is a paragraph about AI. ' * 50 + '\n\n') * 5
chunks = svc.chunk_text(long_text)
print(f'Long: {len(chunks)} chunks')
for c in chunks[:3]:
    print(f'  [{c.chunk_index}] {c.token_count} tokens, {len(c.content)} chars')
"
```

---

## Implementation Details

_Tracked: 2026-01-31_

### Files Changed

| File                                             | Change   | Description                                                                                 |
| ------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------- |
| `python-backend/src/services/chunking.py`        | Created  | ChunkingService with `chunk_text()` method using LangChain's RecursiveCharacterTextSplitter |
| `python-backend/src/db/models.py`                | Modified | Added `ChunkResult` model with `content`, `chunk_index`, `token_count` fields               |
| `python-backend/src/services/__init__.py`        | Modified | Exported `ChunkingService` alongside existing `ContentParser`                               |
| `python-backend/pyproject.toml`                  | Modified | Added `langchain-text-splitters>=0.3.0` dependency                                          |
| `python-backend/uv.lock`                         | Modified | Updated lockfile with new dependency                                                        |
| `python-backend/tests/services/__init__.py`      | Created  | Package init for tests/services directory                                                   |
| `python-backend/tests/services/test_chunking.py` | Created  | 9 comprehensive unit tests for ChunkingService                                              |

### Dependencies Added

- `langchain-text-splitters>=0.3.0` - Provides `RecursiveCharacterTextSplitter` for semantic text chunking

### Acceptance Criteria Status

- [x] `ChunkResult` model added to `src/db/models.py` (not in service file) — `models.py:21-26`
- [x] `services/chunking.py` created with `ChunkingService` class — `chunking.py:14-77`
- [x] `chunk_text(text: str) -> list[ChunkResult]` — Splits text into semantic chunks — `chunking.py:31-62`
- [x] `ChunkResult` model with fields: `content`, `chunk_index`, `token_count` — `models.py:21-26`
- [x] Targets 200-500 tokens per chunk (configurable via settings) — `chunking.py:24-25` uses `settings.chunk_size`
- [x] 50-token overlap between consecutive chunks (configurable via settings) — `chunking.py:26` uses `settings.chunk_overlap`
- [x] Respects document structure: splits at `\n\n` > `\n` > `. ` > ` ` hierarchy — `chunking.py:27`
- [x] Short content (< 200 tokens) returns a single chunk — tested in `test_chunking.py:22-28`
- [x] Empty content returns empty list — `chunking.py:43-44`, tested in `test_chunking.py:16-20`
- [x] Token counting uses a fast approximation (word count × 1.3) — `chunking.py:64-77`
- [x] Error handling with `ChunkingError` for splitter failures — `chunking.py:58-62`
- [x] Logging for debug/error cases — `chunking.py:48, 59`
- [x] Service exported from `services/__init__.py` — `__init__.py:3,6`
- [x] Unit tests in `tests/services/test_chunking.py` — 9 tests, all passing

---

## Learning Report

_Generated: 2026-01-31_

### Summary

Implemented a semantic chunking service for the Python backend that splits text content into embeddable chunks using LangChain's `RecursiveCharacterTextSplitter`. The service is designed to work as the "Chunk" node in the LangGraph processing workflow, taking parsed content and producing chunks suitable for embedding generation.

**Key metrics:**

- 2 files created (service + tests)
- 4 files modified (models, exports, dependencies, lockfile)
- 78 lines of production code
- 116 lines of test code (9 tests)
- 100% of acceptance criteria met

### Patterns & Decisions

1. **Token-to-Character Conversion**: The task spec provided an implementation pattern using `chunk_size * 4` to convert target token counts to character counts (assuming ~4 chars/token). This heuristic was adopted directly as specified.

2. **Separator Hierarchy**: Used the standard `["\n\n", "\n", ". ", " "]` hierarchy from the spec, which prioritizes semantic boundaries (paragraphs → lines → sentences → words).

3. **MVP Token Estimation**: Implemented `word_count * 1.3` approximation as specified. The docstring explicitly notes this is an MVP simplification that may need refinement based on actual model tokenizers.

4. **Error Handling Simplification**: The task spec showed `ChunkingError` with a `details` parameter, but the actual `ChunkingError` class (in `src/exceptions.py`) uses keyword-only constructors without a `details` parameter. The implementation was adjusted to use only the `message` parameter, incorporating error context directly in the message string.

5. **Model Placement**: `ChunkResult` was correctly placed in `src/db/models.py` as specified, following the pattern of keeping all Pydantic models centralized rather than in service files.

### Challenges & Solutions

1. **ChunkingError Constructor**: The spec example used `details={"error": str(e), "text_length": len(text)}`, but the actual exception class doesn't support this. Solution: Included the error message directly in the `message` parameter as `f"Failed to split text into chunks: {e}"`.

2. **Test Coverage Beyond Spec**: The provided test cases in the spec covered basic functionality but didn't test the token estimation formula or overlap behavior. Added 3 additional tests:
   - `test_token_estimation_uses_word_count_heuristic` - Verifies the `word_count * 1.3` formula
   - `test_handles_only_whitespace_between_words` - Edge case for text without structural separators
   - `test_chunk_overlap_preserves_context` - Validates that overlap configuration works

### Lessons Learned

1. **Spec Accuracy**: Task specs may reference API signatures that don't match the actual codebase. Always verify exception classes and model constructors against the real implementation before coding.

2. **Test Beyond Spec**: The spec's test examples were a starting point, not a complete test suite. Adding tests for edge cases and specific algorithm behavior (like the token estimation formula) provides better confidence.

3. **LangChain Ecosystem**: The `langchain-text-splitters` package is a focused sub-package of LangChain containing just the text splitting utilities, keeping the dependency footprint small.

### Documentation Impact

1. **Existing Docs Updated**: None needed - the chunking patterns are already documented in `docs/developer/ai/embeddings.md`.

2. **New Patterns**: The token-to-character conversion heuristic (`tokens * 4 = chars`) could be documented as a standard approximation for future services.

3. **Documentation Gaps**: The `src/exceptions.py` error classes should have their constructors documented somewhere accessible, as the task spec's example was incorrect.
