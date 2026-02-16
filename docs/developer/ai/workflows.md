# LangGraph Workflows

AI-powered processing pipelines orchestrated with LangGraph.

## Why LangGraph

Cortex has complex AI operations that aren't simple request-response:

- Multi-step processing with branching logic
- Retry loops for quality assurance
- State management across steps
- Conditional routing based on content type

LangGraph provides:

- **Typed state**: Each workflow has a clear schema
- **Conditional edges**: Route to different nodes based on state
- **Cycles**: Handle retry loops naturally
- **Checkpointing**: Resume interrupted workflows
- **Debuggability**: Visualize execution, trace issues

## Workflow Overview

| Workflow                 | Trigger             | Purpose                                         |
| ------------------------ | ------------------- | ----------------------------------------------- |
| **Content Processing**   | Item saved          | Transform raw content into searchable knowledge |
| **Adaptive Search**      | Search query        | Find relevant content with smart retrieval      |
| **RAG Chat**             | Chat message        | Answer questions using knowledge base           |
| **Connection Discovery** | Processing complete | Find relationships between items                |
| **Daily Digest**         | Scheduled           | Surface insights and forgotten content          |

## Workflow 1: Content Processing

**Purpose**: Transform raw saved content into searchable, connected knowledge.

```
New Item → Classify → Parse → Chunk → Embed → Extract Metadata → Validate → Store → Discover Connections
                ↓
         (retry for missing chunks; fallback metadata if extraction is incomplete)
```

### Flow

```
┌─────────────┐
│  New Item   │
└──────┬──────┘
       │
┌──────▼──────┐
│  Classify   │ Determine content type (HTML, PDF, audio)
└──────┬──────┘
       │
   ┌───┴───┐───────┐
   ▼       ▼       ▼
┌──────┐┌──────┐┌──────┐
│ HTML ││ PDF  ││Audio │ Type-specific parsing
└──┬───┘└──┬───┘└──┬───┘
   └───┬───┘───────┘
       │
┌──────▼──────┐
│   Chunk     │ Split into semantic segments
└──────┬──────┘
       │
┌──────▼──────┐
│   Embed     │ Generate vectors for each chunk
└──────┬──────┘
       │
┌──────▼──────┐
│  Extract    │ LLM extracts: summary, concepts, entities
└──────┬──────┘
       │
┌──────▼──────────────────────────────────────────┐
│  Validate                                       │
│  - Retry path: chunks missing                   │
│  - Fallback path: metadata incomplete           │
└──────┬──────────────────────────────────────────┘
       │
┌──────▼──────┐
│   Store     │ Persist to database
└──────┬──────┘
       │
┌──────▼──────┐
│  Connect    │ Find related items (async)
└─────────────┘
```

### State Schema

```python
class ProcessingState(TypedDict, total=False):
    item_id: str
    raw_content: str
    content_type: str  # webpage, note, file
    title: str
    source_url: str | None
    ai_provider: AIProvider
    parsed_text: str
    chunk_results: list[ChunkResult]
    metadata: ExtractedMetadata
    chunks: list  # After persistence, with IDs
    embeddings_stored: bool
    validation_passed: bool
    retry_count: int
    error: str | None
    error_step: ProcessingStep | None
    last_progress: float
    emit_update: ProcessingUpdateEmitter | None
```

### Key Design Decisions

- **Conditional parsing**: Different content types need different parsers
- **Semantic chunking**: Respects document structure, not fixed character counts
- **Validation routing**: Missing chunks trigger retry; incomplete metadata gets conservative fallback
- **Conservative fallback metadata**: Uses source text/title only and avoids synthetic concepts/entities
- **Async connections**: Don't block user confirmation on slow connection discovery

## Workflow 2: Adaptive Search

**Purpose**: Find relevant content even with vague or complex queries.

```
Query → Analyze → [Decompose if complex] → Vector Search → FTS Search → Fuse → [Expand if poor] → Return
```

### Flow

```
┌─────────────┐
│   Query     │
└──────┬──────┘
       │
┌──────▼──────┐
│  Analyze    │ Classify: simple, multi-faceted, temporal
└──────┬──────┘
       │
   ┌───┴────────────┐
   │ Multi-faceted  │
   ▼                │
┌──────────┐        │
│Decompose │        │ Break into sub-queries
└────┬─────┘        │
     │              │
┌────▼────────◀─────┘
│Vector Search│ Embed query, find similar chunks
└──────┬──────┘
       │
┌──────▼──────┐
│  FTS Search │ Full-text for exact matches
└──────┬──────┘
       │
┌──────▼──────┐
│    Fuse     │ Reciprocal Rank Fusion
└──────┬──────┘
       │
┌──────▼──────┐      ┌──────────────┐
│  Evaluate   │─────▶│   Expand     │ Add synonyms if poor results
└──────┬──────┘ Poor └──────────────┘
       │ Good
       │
┌──────▼──────┐
│   Return    │ Ranked results with snippets
└─────────────┘
```

### State Schema

```python
class SearchState(TypedDict):
    original_query: str
    query_type: str  # simple, multi_faceted, temporal
    sub_queries: list[str]
    vector_results: list[SearchResult]
    fts_results: list[SearchResult]
    fused_results: list[SearchResult]
    result_quality: str  # good, poor
    expansion_terms: list[str]
    final_results: list[SearchResult]
```

### Key Design Decisions

- **Hybrid search**: Vector finds concepts, FTS finds exact phrases
- **Query decomposition**: "Compare X and Y" becomes searches for both
- **Automatic expansion**: Try related terms before returning empty results
- **RRF fusion**: Simple but effective combination of ranked lists

## Workflow 3: RAG Chat

**Purpose**: Answer questions using your personal knowledge base with citations.

```
Message → Retrieve → Grade Documents → [Rewrite if no relevant docs] → Generate → Ground Check → [Regenerate if hallucinating] → Return
```

### Flow

```
┌─────────────┐
│   Message   │
└──────┬──────┘
       │
┌──────▼──────┐
│  Retrieve   │ Search for relevant chunks
└──────┬──────┘
       │
┌──────▼──────┐
│   Grade     │ LLM: "Is this relevant to the question?"
└──────┬──────┘
       │
   ┌───┴───────────────────┐
   │ No relevant docs      │
   ▼                       │
┌──────────┐               │
│ Rewrite  │               │ Transform query for better retrieval
│  Query   │───────────────┘ (retry search)
└──────────┘
       │ Have relevant docs
       │
┌──────▼──────┐
│  Generate   │ Build answer with citations
└──────┬──────┘
       │
┌──────▼──────┐
│   Ground    │ Verify answer is supported by sources
└──────┬──────┘
       │
   ┌───┴───────────────────┐
   │ Not grounded          │
   ▼                       │
┌──────────┐               │
│Regenerate│               │ Try again with stricter prompt
└──────────┘
       │ Grounded
       │
┌──────▼──────┐
│   Return    │ Answer with citations
└─────────────┘
```

### State Schema

```python
class ChatState(TypedDict):
    conversation_id: str
    messages: list[Message]
    current_query: str
    retrieved_chunks: list[Chunk]
    graded_chunks: list[Chunk]  # Filtered to relevant only
    rewrite_count: int
    generated_answer: str
    citations: list[Citation]
    is_grounded: bool
    regenerate_count: int
```

### Key Design Decisions

- **Document grading**: Filter out tangentially related content before generation
- **Query rewriting**: Natural questions often aren't good search queries
- **Grounding check**: Catch hallucinations before showing to user
- **Citations**: Always link back to source items

## Workflow 4: Connection Discovery

**Purpose**: Automatically find relationships between items.

```
Item Ready → Find Similar → Extract Entities → Match Entities → Temporal Cluster → Score → Store
```

### Flow

```
┌─────────────┐
│ Item Ready  │ Triggered after processing
└──────┬──────┘
       │
┌──────▼──────┐
│Find Similar │ Vector search for similar items
└──────┬──────┘
       │
┌──────▼──────┐
│  Extract    │ Get entities (people, companies, concepts)
│  Entities   │
└──────┬──────┘
       │
┌──────▼──────┐
│   Match     │ Find items with same entities
│  Entities   │
└──────┬──────┘
       │
┌──────▼──────┐
│  Temporal   │ Find items saved around same time
│  Cluster    │
└──────┬──────┘
       │
┌──────▼──────┐
│   Score     │ Assign connection strength (0-1)
└──────┬──────┘
       │
┌──────▼──────┐
│   Store     │ Save bidirectional connections
└─────────────┘
```

### State Schema

```python
class ConnectionState(TypedDict):
    source_item_id: str
    similar_items: list[tuple[str, float]]  # (item_id, similarity)
    source_entities: list[Entity]
    entity_matches: list[tuple[str, list[Entity]]]  # (item_id, shared_entities)
    temporal_matches: list[str]  # item_ids saved around same time
    scored_connections: list[Connection]
```

### Key Design Decisions

- **Multiple signals**: Similarity + entity matching + temporal proximity
- **Background processing**: Runs after user gets "saved!" confirmation
- **Strength scoring**: Not all connections are equal
- **Bidirectional storage**: A→B implies B→A

## Workflow 5: Daily Digest

**Purpose**: Proactively surface insights and forgotten content.

```
Scheduled → Gather Recent → Find New Connections → Surface Gems → Generate Insights → Compose → Notify
```

### Flow

```
┌─────────────┐
│  Scheduled  │ Daily or weekly
└──────┬──────┘
       │
┌──────▼──────┐
│   Gather    │ Recent items (last 7 days)
│   Recent    │
└──────┬──────┘
       │
┌──────▼──────┐
│  Find New   │ Connections since last digest
│ Connections │
└──────┬──────┘
       │
┌──────▼──────┐
│  Surface    │ Old items you haven't accessed
│   Gems      │
└──────┬──────┘
       │
┌──────▼──────┐
│  Generate   │ LLM synthesizes themes
│  Insights   │
└──────┬──────┘
       │
┌──────▼──────┐
│  Compose    │ Format into readable digest
└──────┬──────┘
       │
┌──────▼──────┐
│   Notify    │ Show in app or system notification
└─────────────┘
```

### State Schema

```python
class DigestState(TypedDict):
    digest_date: date
    recent_items: list[Item]
    new_connections: list[Connection]
    surfaced_gems: list[Item]  # Old but valuable
    generated_insights: str
    composed_digest: DigestContent
```

### Key Design Decisions

- **Proactive value**: Brings forgotten knowledge back
- **Serendipity**: Random surfacing creates unexpected connections
- **Synthesis**: LLM sees patterns humans miss
- **User control**: Frequency is configurable (daily, weekly, manual)

## Implementation Notes

### Error Handling in Workflows

Each node should catch exceptions and return error state for routing:

```python
class ProcessingState(TypedDict, total=False):
    item_id: str
    # ... other fields
    error: str | None
    error_step: ProcessingStep | None
    retry_count: int

@log_node_execution("parse")
async def parse_node(state: ProcessingState) -> dict:
    current_step = ProcessingStep.PARSING
    try:
        parser = ContentParser()
        result = parser.parse(state["raw_content"], state["content_type"])
        return {"parsed_text": result.text}
    except Exception as e:
        return {"error": str(e), "error_step": current_step}
```

Use a `route_or_error()` factory for conditional edges:

```python
def route_or_error(next_node: str):
    """Route to next_node or handle_error if error is set."""
    def router(state: ProcessingState) -> str:
        if state.get("error"):
            return "handle_error"
        return next_node
    return router

# Usage in graph definition
builder.add_conditional_edges(
    "parse",
    route_or_error("chunk"),
    {"chunk": "chunk", "handle_error": "handle_error"}
)
```

### Validation Routing

Validation routing in content processing:

- Retry is used when chunking produced no chunks.
- Incomplete metadata (missing summary/concepts) is recovered in `validate_node()` with conservative fallback metadata, then the workflow proceeds to persist.

```python
def route_after_validation(state: ProcessingState) -> str:
    if state.get("error"):
        return "handle_error"
    if state.get("validation_passed"):
        return "persist"
    if state.get("retry_count", 0) < MAX_RETRIES:
        return "retry"  # Routes back to earlier node
    return "handle_error"  # Max retries exceeded
```

### Checkpointing

For long-running workflows (bulk import), enable checkpointing:

```python
from langgraph.checkpoint import MemorySaver

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

# Resume interrupted workflow
config = {"configurable": {"thread_id": workflow_id}}
result = await graph.ainvoke(state, config)
```

### Observability

Log workflow execution for debugging with a decorator:

```python
import functools

def log_node_execution(node_name: str):
    """Decorator for logging workflow node execution."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(state: ProcessingState) -> dict:
            item_id = state.get("item_id", "unknown")
            logger.info(f"Starting node: {node_name}", extra={"item_id": item_id})
            try:
                result = await func(state)
                logger.info(f"Completed node: {node_name}", extra={"item_id": item_id})
                return result
            except Exception as e:
                logger.error(f"Failed node: {node_name}", extra={"item_id": item_id, "error": str(e)})
                raise
        return wrapper
    return decorator
```

### Database Access in Nodes

Workflow nodes manage their own database connections:

```python
from src.db.database import db_connection
from src.db.models import ItemUpdate, ProcessingStep, normalize_item_metadata
from src.db.repositories import item_repo

@log_node_execution("persist")
async def persist_node(state: ProcessingState) -> dict:
    current_step = ProcessingStep.STORING
    try:
        async with db_connection() as db:
            # Multiple operations, single atomic commit
            chunks = await chunk_repo.create_many(db, chunk_creates)
            await embedding_service.embed_chunks(db, chunks)

            item = await item_repo.get(db, item_id)
            existing_metadata = (
                item.metadata.model_dump(exclude_none=True)
                if item and item.metadata
                else {}
            )
            existing_metadata["summary"] = metadata.summary
            existing_metadata["concepts"] = metadata.concepts
            existing_metadata["entities"] = metadata.entities

            await item_repo.update(
                db,
                item_id,
                ItemUpdate(metadata=normalize_item_metadata(existing_metadata)),
            )
            await db.commit()
        return {"chunks": chunks, "embeddings_stored": True}
    except Exception as e:
        return {"error": str(e), "error_step": current_step}
```

## Related Documentation

- [AI Overview](./overview.md) - Provider architecture
- [Embeddings](./embeddings.md) - Vector search details
- [Python Backend Architecture](../python-backend/architecture.md) - FastAPI integration
