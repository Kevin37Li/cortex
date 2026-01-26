# Task: Implement Semantic Chunking Service

## Summary

Create a chunking service that splits parsed text content into semantic chunks suitable for embedding. Uses LangChain's `RecursiveCharacterTextSplitter` to respect document structure (paragraphs, sentences) while targeting 200-500 tokens per chunk with overlap for context continuity.

## Acceptance Criteria

- [ ] `services/chunking.py` created with `ChunkingService` class
- [ ] `chunk_text(text: str) -> list[ChunkResult]` — Splits text into semantic chunks
- [ ] `ChunkResult` model with fields: `content` (chunk text), `chunk_index` (0-based position), `token_count` (estimated)
- [ ] Targets 200-500 tokens per chunk (configurable via settings)
- [ ] 50-token overlap between consecutive chunks (configurable via settings)
- [ ] Respects document structure: splits at `\n\n` > `\n` > `. ` > ` ` hierarchy
- [ ] Short content (< 200 tokens) returns a single chunk
- [ ] Empty content returns empty list
- [ ] Token counting uses a fast approximation (word count × 1.3) — exact tokenization not needed at MVP

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

## ChunkResult Model

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
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.config import settings

class ChunkingService:
    def __init__(self) -> None:
        # Approximate: 1 token ≈ 4 characters
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size * 4,  # Convert tokens to chars
            chunk_overlap=settings.chunk_overlap * 4,
            separators=["\n\n", "\n", ". ", " "],
            length_function=len,
        )

    def chunk_text(self, text: str) -> list[ChunkResult]:
        if not text or not text.strip():
            return []

        chunks = self._splitter.split_text(text)
        return [
            ChunkResult(
                content=chunk,
                chunk_index=i,
                token_count=self._estimate_tokens(chunk),
            )
            for i, chunk in enumerate(chunks)
        ]

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Approximate token count (word count × 1.3)."""
        return int(len(text.split()) * 1.3)
```

## Files to Create/Modify

**Create:**

- `python-backend/src/services/chunking.py` — Chunking service

**Modify:**

- `python-backend/pyproject.toml` — Add `langchain-text-splitters`

## Verification

```bash
cd python-backend
uv sync
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
