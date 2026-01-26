# Task: Implement Metadata Extraction Service

## Summary

Create a metadata extraction service that uses LLM chat to extract structured metadata from parsed content: a concise summary, key concepts/topics, and named entities (people, organizations, places). This is the "Extract" node in the processing workflow.

## Acceptance Criteria

- [ ] `services/extraction.py` created with `MetadataExtractor` class
- [ ] `extract(text: str, title: str | None = None) -> ExtractedMetadata` — Extracts metadata using LLM
- [ ] `ExtractedMetadata` Pydantic model with fields: `summary` (str, 2-3 sentences), `concepts` (list[str], key topics), `entities` (list[str], named entities)
- [ ] Uses `AIProvider.chat()` with a structured prompt for extraction
- [ ] Prompt instructs the LLM to return JSON for reliable parsing
- [ ] Handles LLM response parsing failures gracefully (returns partial metadata, logs warning)
- [ ] Handles provider unavailability: wraps `AIProviderError` into `MetadataExtractionError`
- [ ] Works with both local (Ollama) and cloud (OpenAI) providers via the `AIProvider` interface

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
- Truncate very long texts to fit model context (first ~3000 tokens)

## ExtractedMetadata Model

```python
class ExtractedMetadata(BaseModel):
    """Metadata extracted from content via LLM."""
    summary: str  # 2-3 sentence summary
    concepts: list[str]  # Key topics/concepts (3-7 items)
    entities: list[str]  # Named entities: people, orgs, places (0-10 items)
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

Title: {title}

Content:
{text}"""
```

## Files to Create/Modify

**Create:**

- `python-backend/src/services/extraction.py` — Metadata extraction service

## Verification

```bash
cd python-backend
uv run ruff check src/
uv run mypy src/

# Manual test (requires Ollama running with llama3.2):
uv run python -c "
import asyncio
from src.services.extraction import MetadataExtractor
from src.providers.ollama import OllamaProvider

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
