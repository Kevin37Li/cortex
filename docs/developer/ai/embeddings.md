# Embeddings

Vector embeddings for semantic search and similarity.

## Overview

Embeddings convert text into numerical vectors that capture semantic meaning. Similar concepts have similar vectors, enabling:

- Semantic search (find conceptually related content)
- Connection discovery (items about the same topic)
- Query understanding (match intent, not just keywords)

## Embedding Strategy

### Document Processing

When content is saved:

```
┌─────────────────┐
│   Raw Content   │ Full webpage, PDF, note
└────────┬────────┘
         │
┌────────▼────────┐
│  Semantic Chunk │ Split by meaning, not character count
└────────┬────────┘
         │
┌────────▼────────┐
│    Embed Each   │ Generate vector for each chunk
│      Chunk      │
└────────┬────────┘
         │
┌────────▼────────┐
│  Store in DB    │ sqlite-vec for vector search
└─────────────────┘
```

### Chunking Strategy

**Why chunk?**

- Long documents exceed model context limits
- Smaller chunks enable more precise retrieval
- Each chunk can have its own relevance score

**Semantic chunking principles:**

- Respect paragraph boundaries
- Keep related sentences together
- Target 200-500 tokens per chunk
- Add overlap between chunks (50 tokens)

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,           # Target size in tokens
    chunk_overlap=50,         # Overlap for context continuity
    separators=["\n\n", "\n", ". ", " "],  # Split hierarchy
    length_function=token_counter,
)

chunks = splitter.split_text(document_text)
```

### Embedding Models

| Provider | Model                  | Dimensions | Speed  | Quality |
| -------- | ---------------------- | ---------- | ------ | ------- |
| Ollama   | nomic-embed-text       | 768        | Fast   | Good    |
| OpenAI   | text-embedding-3-small | 1536       | Fast   | Better  |
| OpenAI   | text-embedding-3-large | 3072       | Slower | Best    |

**Recommendation**: Use `nomic-embed-text` for local, `text-embedding-3-small` for cloud.

### Dimension Considerations

Higher dimensions = more precision but more storage:

| Dimensions | Storage per chunk | 10K items (~50K chunks) |
| ---------- | ----------------- | ----------------------- |
| 768        | 3 KB              | 150 MB                  |
| 1536       | 6 KB              | 300 MB                  |
| 3072       | 12 KB             | 600 MB                  |

For most use cases, 768-1536 dimensions are sufficient.

## EmbeddingService

The `EmbeddingService` class (`src/services/embeddings.py`) handles embedding generation and storage:

```python
from src.services import EmbeddingService
from src.api.dependencies import get_ai_provider

# Inject via FastAPI dependency
service = EmbeddingService(provider=ai_provider)

# Generate embeddings for persisted chunks (must have IDs)
await service.embed_chunks(db, chunks)

# Generate embedding for search query
query_embedding = await service.embed_query("machine learning basics", db=db)
```

Key behaviors:

- **Model consistency**: Tracks embedding model in `app_metadata` table; raises `EmbeddingModelMismatchError` if model changes
- **Deferred recording**: Records model name only after successful embedding storage (atomic with commit)
- **Batch processing**: Embeds chunks in configurable batches (default 32)
- **Dimension validation**: Validates all embeddings match `EMBEDDING_DIMENSION` (768)

## Storage with sqlite-vec

Embeddings are stored using the [sqlite-vec](https://github.com/asg017/sqlite-vec) extension:

```sql
-- Create virtual table for vector storage
CREATE VIRTUAL TABLE vec_chunks USING vec0(
    chunk_id INTEGER PRIMARY KEY,
    embedding FLOAT[768]  -- Match your model's dimensions
);

-- Vector similarity search (cosine distance)
SELECT
    chunk_id,
    distance
FROM vec_chunks
WHERE embedding MATCH ?
ORDER BY distance
LIMIT 10;
```

**Inserting embeddings requires serialization:**

```python
import sqlite_vec

# Must serialize before INSERT - raw lists won't work
serialized = sqlite_vec.serialize_float32(embedding)
await db.execute(
    "INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)",
    [chunk_id, serialized]
)
```

### Index Configuration

sqlite-vec uses approximate nearest neighbor (ANN) search for speed:

```sql
-- Configure index parameters
CREATE VIRTUAL TABLE vec_chunks USING vec0(
    chunk_id INTEGER PRIMARY KEY,
    embedding FLOAT[768],
    +idx_type = 'ivfflat',    -- Index type
    +nlist = 100              -- Number of clusters
);
```

**Trade-offs:**

- Higher `nlist` = better accuracy, slower build
- For < 100K chunks, default settings work well

## Search Implementation

The conceptual flow for search is shown below. See `python-backend/src/services/search.py` for the full production implementation with error handling, score normalization to [0, 1], missing-chunk filtering, and parallel query execution via secondary DB connections.

### Basic Vector Search

```python
async def vector_search(
    query: str,
    limit: int = 10
) -> list[SearchResult]:
    # Embed the query
    query_embedding = await provider.embed(query)

    # Search sqlite-vec
    results = db.execute("""
        SELECT
            c.id,
            c.item_id,
            c.content,
            v.distance
        FROM vec_chunks v
        JOIN chunks c ON c.id = v.chunk_id
        WHERE v.embedding MATCH ?
        ORDER BY v.distance
        LIMIT ?
    """, [query_embedding, limit])

    return [SearchResult(**row) for row in results]
```

### Hybrid Search (Vector + Full-Text)

Combine vector similarity with keyword matching:

```python
async def hybrid_search(
    query: str,
    limit: int = 10
) -> list[SearchResult]:
    # Vector search
    vector_results = await vector_search(query, limit=limit * 2)

    # Full-text search
    fts_results = db.execute("""
        SELECT id, item_id, content, bm25(chunks_fts) as score
        FROM chunks_fts
        WHERE chunks_fts MATCH ?
        ORDER BY score
        LIMIT ?
    """, [query, limit * 2])

    # Reciprocal Rank Fusion
    return reciprocal_rank_fusion(vector_results, fts_results, limit=limit)
```

### Reciprocal Rank Fusion (RRF)

Combines ranked lists from different search methods. The actual implementation uses two explicit parameters (`vector_results`, `fts_results`) and normalizes fused scores to [0, 1] so the top result always has `score=1.0`:

```python
def reciprocal_rank_fusion(
    vector_results: list[ChunkSearchResult],
    fts_results: list[ChunkSearchResult],
    k: int = 60,
) -> list[ChunkSearchResult]:
    scores = defaultdict(float)

    for rank, result in enumerate(vector_results, start=1):
        scores[result.chunk_id] += 1 / (k + rank)

    for rank, result in enumerate(fts_results, start=1):
        scores[result.chunk_id] += 1 / (k + rank)

    # Sort by fused score descending, chunk_id ascending for deterministic tie-breaking
    # Normalize top score to 1.0
    ...
```

## Embedding Consistency

**Critical**: Never mix embeddings from different models in the same database.

The `EmbeddingService` enforces this automatically:

1. On first embedding, records the model name in `app_metadata` table
2. On subsequent embeddings, validates configured model matches stored model
3. Raises `EmbeddingModelMismatchError` if models differ

```python
# Model tracking via AppMetadataRepository singleton
from src.db.repositories import metadata_repo

current_model = await metadata_repo.get(db, "embedding_model")  # e.g., "nomic-embed-text"
```

If you need to change embedding models, you must re-embed all existing content.

### Migration Strategy

When upgrading embedding models:

```python
async def migrate_embeddings(new_model: str):
    # 1. Create new vector table
    db.execute("""
        CREATE VIRTUAL TABLE vec_chunks_new USING vec0(...)
    """)

    # 2. Re-embed all chunks
    chunks = db.execute("SELECT id, content FROM chunks")
    for chunk in chunks:
        new_embedding = await provider.embed(chunk.content)
        db.execute(
            "INSERT INTO vec_chunks_new VALUES (?, ?)",
            [chunk.id, new_embedding]
        )

    # 3. Swap tables
    db.execute("DROP TABLE vec_chunks")
    db.execute("ALTER TABLE vec_chunks_new RENAME TO vec_chunks")

    # 4. Update metadata
    db.execute(
        "INSERT OR REPLACE INTO app_metadata (key, value) VALUES ('embedding_model', ?)",
        [new_model]
    )
```

## Performance Optimization

### Batch Embedding

The `EmbeddingService` handles batching automatically:

```python
# Chunks are processed in batches (default 32)
service = EmbeddingService(provider, batch_size=32)
await service.embed_chunks(db, chunks)  # Batched internally
```

Embeddings are generated in batches via `provider.embed_batch()` but stored one-by-one (sqlite-vec constraint), with a single commit at the end for atomicity.

### Caching

Cache embeddings for frequently accessed content:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_embedding(text_hash: str) -> list[float] | None:
    return db.execute(
        "SELECT embedding FROM embedding_cache WHERE text_hash = ?",
        [text_hash]
    ).fetchone()
```

### Pre-computation

Embed common queries at startup:

```python
COMMON_QUERIES = [
    "machine learning",
    "product management",
    "startup advice",
    # ... user's frequent searches
]

async def precompute_query_embeddings():
    for query in COMMON_QUERIES:
        embedding = await provider.embed(query)
        cache.set(f"query:{query}", embedding)
```

## Quality Evaluation

### Relevance Testing

Periodically test search quality:

```python
TEST_CASES = [
    {
        "query": "how to price SaaS products",
        "expected_items": ["pricing-article-1", "pricing-note-2"],
    },
    # ... more test cases
]

async def evaluate_search_quality():
    scores = []
    for test in TEST_CASES:
        results = await vector_search(test["query"])
        result_ids = [r.item_id for r in results[:5]]
        hit_rate = len(set(result_ids) & set(test["expected_items"])) / len(test["expected_items"])
        scores.append(hit_rate)
    return sum(scores) / len(scores)
```

### Embedding Visualization

For debugging, project embeddings to 2D:

```python
from sklearn.manifold import TSNE

def visualize_embeddings(embeddings: list[list[float]], labels: list[str]):
    tsne = TSNE(n_components=2, random_state=42)
    coords = tsne.fit_transform(embeddings)
    # Plot with matplotlib or export for visualization
```

## Related Documentation

- [AI Overview](./overview.md) - Provider architecture
- [sqlite-vec](../data-storage/sqlite-vec.md) - Vector storage details
- [LangGraph Workflows](./workflows.md) - Search workflow implementation
