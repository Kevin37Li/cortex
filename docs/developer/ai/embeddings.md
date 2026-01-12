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

| Provider | Model | Dimensions | Speed | Quality |
|----------|-------|------------|-------|---------|
| Ollama | nomic-embed-text | 768 | Fast | Good |
| OpenAI | text-embedding-3-small | 1536 | Fast | Better |
| OpenAI | text-embedding-3-large | 3072 | Slower | Best |

**Recommendation**: Use `nomic-embed-text` for local, `text-embedding-3-small` for cloud.

### Dimension Considerations

Higher dimensions = more precision but more storage:

| Dimensions | Storage per chunk | 10K items (~50K chunks) |
|------------|-------------------|-------------------------|
| 768 | 3 KB | 150 MB |
| 1536 | 6 KB | 300 MB |
| 3072 | 12 KB | 600 MB |

For most use cases, 768-1536 dimensions are sufficient.

## Storage with sqlite-vec

Embeddings are stored using the [sqlite-vec](https://github.com/asg017/sqlite-vec) extension:

```sql
-- Create virtual table for vector storage
CREATE VIRTUAL TABLE vec_chunks USING vec0(
    chunk_id INTEGER PRIMARY KEY,
    embedding FLOAT[768]  -- Match your model's dimensions
);

-- Insert embedding
INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?);

-- Vector similarity search (cosine distance)
SELECT
    chunk_id,
    distance
FROM vec_chunks
WHERE embedding MATCH ?
ORDER BY distance
LIMIT 10;
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

Combines ranked lists from different search methods:

```python
def reciprocal_rank_fusion(
    *result_lists: list[SearchResult],
    k: int = 60,
    limit: int = 10
) -> list[SearchResult]:
    scores = defaultdict(float)

    for results in result_lists:
        for rank, result in enumerate(results):
            scores[result.id] += 1 / (k + rank + 1)

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [get_result(id) for id in sorted_ids[:limit]]
```

## Embedding Consistency

**Critical**: Never mix embeddings from different models in the same database.

If you change embedding models:
1. Re-embed all existing content
2. Or maintain separate vector tables per model

```python
# Track embedding model in metadata
class ChunkMetadata:
    embedding_model: str  # e.g., "nomic-embed-text"
    embedding_version: str  # e.g., "v1.5"
    embedded_at: datetime
```

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
    db.execute("UPDATE settings SET embedding_model = ?", [new_model])
```

## Performance Optimization

### Batch Embedding

Embed multiple chunks at once to reduce overhead:

```python
async def embed_batch(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = await provider.embed_batch(batch)
        embeddings.extend(batch_embeddings)
    return embeddings
```

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
