# Task: Implement LangGraph Content Processing Workflow

## Summary

Create the main content processing workflow using LangGraph that orchestrates the full pipeline: classify content type → parse → chunk → embed → extract metadata → validate → store results. This is the core AI pipeline that transforms raw saved content into searchable, connected knowledge.

## Acceptance Criteria

- [ ] `workflows/processing.py` created with LangGraph `StateGraph` implementation
- [ ] `ProcessingState` TypedDict with all workflow state fields
- [ ] Workflow nodes: `classify`, `parse`, `chunk`, `embed`, `extract_metadata`, `validate`, `store`
- [ ] Conditional edge: `validate` routes to `store` (if valid) or back to retry (if invalid, max 3 retries)
- [ ] `classify` node determines content type from item data
- [ ] `parse` node calls `ContentParser` for HTML/text extraction
- [ ] `chunk` node calls `ChunkingService` for semantic splitting
- [ ] `embed` node calls `EmbeddingService` for vector generation
- [ ] `extract_metadata` node calls `MetadataExtractor` for summary/concepts/entities
- [ ] `validate` node checks that chunks were created and metadata was extracted
- [ ] `store` node persists chunks, embeddings, and metadata to database, updates item `processing_status`
- [ ] Error handling: on unrecoverable failure, sets item `processing_status` to `'failed'` and stores error message
- [ ] Compiled graph exposes `async def process_item(item_id: str) -> ProcessingState`

## Dependencies

- Task 1: Processing error types
- Task 3: Content parsing service (`ContentParser`)
- Task 4: Semantic chunking service (`ChunkingService`)
- Task 5: Embedding management service (`EmbeddingService`)
- Task 6: Metadata extraction service (`MetadataExtractor`)
- Phase 1: `ItemRepository`, `ChunkRepository`, `AIProvider`

## Technical Notes

- Per `docs/developer/ai/workflows.md`: follow the Content Processing workflow design
- Use `langgraph` package — add to `pyproject.toml` if not present
- The workflow receives an `item_id`, fetches the item from DB, processes it, and updates the DB
- Services (`ContentParser`, `ChunkingService`, `EmbeddingService`, `MetadataExtractor`) are injected or instantiated within nodes
- The `AIProvider` instance needs to be passed through the graph (store in state or use a factory)
- Item `processing_status` transitions: `pending` → `processing` → `completed` or `failed`
- On validation failure, retry up to 3 times (increment `retry_count` in state)

## ProcessingState

```python
class ProcessingState(TypedDict):
    item_id: str
    raw_content: str
    content_type: str  # html, text, file
    title: str
    source_url: str | None
    parsed_text: str
    chunks: list[dict]  # ChunkResult as dicts
    embeddings: list[list[float]]
    metadata: dict  # ExtractedMetadata as dict
    chunk_ids: list[str]  # Stored chunk IDs
    validation_passed: bool
    retry_count: int
    error: str | None
```

## Graph Structure

```python
from langgraph.graph import StateGraph, END

builder = StateGraph(ProcessingState)

# Add nodes
builder.add_node("classify", classify_node)
builder.add_node("parse", parse_node)
builder.add_node("chunk", chunk_node)
builder.add_node("embed", embed_node)
builder.add_node("extract_metadata", extract_metadata_node)
builder.add_node("validate", validate_node)
builder.add_node("store", store_node)
builder.add_node("handle_error", handle_error_node)

# Add edges
builder.set_entry_point("classify")
builder.add_edge("classify", "parse")
builder.add_edge("parse", "chunk")
builder.add_edge("chunk", "embed")
builder.add_edge("embed", "extract_metadata")
builder.add_edge("extract_metadata", "validate")

# Conditional: validate → store or retry
builder.add_conditional_edges(
    "validate",
    route_after_validation,
    {"store": "store", "retry": "chunk", "fail": "handle_error"}
)
builder.add_edge("store", END)
builder.add_edge("handle_error", END)
```

## Files to Create/Modify

**Create:**

- `python-backend/src/workflows/processing.py` — LangGraph processing workflow

**Modify:**

- `python-backend/pyproject.toml` — Add `langgraph` dependency (if not present)

## Verification

```bash
cd python-backend
uv sync
uv run ruff check src/
uv run mypy src/

# Integration test (requires Ollama running):
uv run python -c "
import asyncio
from src.workflows.processing import process_item

async def test():
    # Assumes an item exists in the database
    result = await process_item('test-item-id')
    print(f'Status: {result[\"error\"] or \"success\"}')
    print(f'Chunks: {len(result[\"chunks\"])}')

asyncio.run(test())
"
```
