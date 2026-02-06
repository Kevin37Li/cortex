# Python Backend Architecture

FastAPI sidecar for AI processing and data management.

## Overview

The Python backend handles:

- AI operations (embeddings, chat, extraction)
- LangGraph workflow execution
- SQLite database access
- Background processing queues

It runs as a sidecar process, communicating with the Tauri frontend via localhost HTTP.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Tauri Application                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              React Frontend                          │    │
│  │  • UI rendering                                      │    │
│  │  • User interactions                                 │    │
│  │  • State management (Zustand, TanStack Query)       │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │              Rust Backend                            │    │
│  │  • Window management                                 │    │
│  │  • System tray                                       │    │
│  │  • Process management (spawns Python)               │    │
│  │  • File system access                                │    │
│  └──────────────────────┬──────────────────────────────┘    │
└─────────────────────────┼───────────────────────────────────┘
                          │ localhost:8742
┌─────────────────────────▼───────────────────────────────────┐
│                   Python Sidecar                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                  FastAPI                             │    │
│  │  • REST endpoints                                    │    │
│  │  • WebSocket for streaming                          │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │              Application Layer                       │    │
│  │  • LangGraph workflows                               │    │
│  │  • AI provider abstraction                          │    │
│  │  • Business logic                                    │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │              Data Layer                              │    │
│  │  • SQLite with sqlite-vec                           │    │
│  │  • Repository pattern                                │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
python-backend/
├── src/
│   ├── api/                    # FastAPI routes
│   │   ├── __init__.py
│   │   ├── deps.py            # Dependency injection helpers
│   │   ├── health.py          # Health check endpoint
│   │   ├── items.py           # CRUD for items
│   │   ├── processing.py     # Processing queue endpoints
│   │   ├── search.py          # Search endpoints
│   │   ├── chat.py            # Chat endpoints
│   │   └── settings.py        # Configuration endpoints
│   │
│   ├── workflows/             # LangGraph workflows
│   │   ├── __init__.py
│   │   ├── processing.py      # Content processing graph
│   │   ├── search.py          # Adaptive search graph
│   │   ├── chat.py            # RAG chat graph
│   │   ├── connections.py     # Connection discovery graph
│   │   └── digest.py          # Daily digest graph
│   │
│   ├── providers/             # AI provider implementations
│   │   ├── __init__.py
│   │   ├── base.py            # AIProvider interface
│   │   ├── ollama.py          # Ollama provider
│   │   └── cloud.py           # LiteLLM cloud provider
│   │
│   ├── db/                    # Database layer
│   │   ├── __init__.py
│   │   ├── database.py        # Connection management
│   │   ├── models.py          # Pydantic models (Item, Chunk, etc.)
│   │   ├── schema.sql         # Table definitions (applied by init_database)
│   │   └── repositories/      # Data access patterns
│   │       ├── base.py        # Abstract BaseRepository
│   │       ├── items.py
│   │       ├── chunks.py
│   │       └── app_metadata.py # Key-value metadata storage
│   │
│   ├── services/              # Business logic
│   │   ├── __init__.py
│   │   ├── parsing.py         # Content parsing (HTML to text)
│   │   ├── chunking.py        # Semantic text chunking
│   │   ├── embeddings.py      # Embedding generation and storage
│   │   ├── extraction.py      # Metadata extraction via LLM
│   │   └── processing.py      # Background processing queue
│   │
│   ├── config.py              # Application configuration (pydantic-settings)
│   ├── exceptions.py          # Custom exception hierarchy
│   └── main.py                # FastAPI app entry point
│
├── tests/
│   ├── api/
│   ├── services/
│   ├── workflows/
│   └── conftest.py
│
├── pyproject.toml             # Dependencies (Poetry/uv)
└── Dockerfile                 # For development
```

## API Design

### RESTful Endpoints

```python
# Items
POST   /api/items              # Create item
GET    /api/items              # List items
GET    /api/items/{id}         # Get item
PUT    /api/items/{id}         # Update item
DELETE /api/items/{id}         # Delete item

# Search
POST   /api/search             # Execute search
GET    /api/search/suggestions # Get search suggestions

# Chat
POST   /api/conversations                    # Create conversation
GET    /api/conversations                    # List conversations
GET    /api/conversations/{id}               # Get conversation
POST   /api/conversations/{id}/messages      # Send message
DELETE /api/conversations/{id}               # Delete conversation

# Processing
GET    /api/processing/queue   # Get processing queue status
POST   /api/processing/retry   # Retry failed items

# Settings
GET    /api/settings           # Get all settings
PUT    /api/settings           # Update settings
GET    /api/settings/ai        # Get AI provider settings
PUT    /api/settings/ai        # Update AI provider

# Health & Status
GET    /api/health             # Backend health check
GET    /api/health/ollama      # Ollama status
GET    /api/db/status          # Database verification (versions, tables, counts)
```

### WebSocket for Streaming

```python
# Chat streaming
WS /api/ws/chat/{conversation_id}

# Processing progress
WS /api/ws/processing/{item_id}
```

### Request/Response Examples

```python
# Create item
POST /api/items
{
    "url": "https://example.com/article",
    "title": "Article Title",
    "content": "<html>...</html>",
    "source": "browser_extension"
}

# Response
{
    "id": "item_abc123",
    "status": "processing",
    "created_at": "2024-01-15T10:30:00Z"
}

# Search
POST /api/search
{
    "query": "machine learning basics",
    "limit": 10
}

# Response
{
    "results": [
        {
            "item_id": "item_abc123",
            "title": "ML Fundamentals",
            "snippet": "...relevant text...",
            "score": 0.85
        }
    ],
    "query_type": "simple",
    "took_ms": 45
}
```

## FastAPI Implementation

### Main Application

```python
# src/main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.health import router as health_router
from .api.items import router as items_router
from .api.processing import router as processing_router
from .db import init_database
from .exceptions import AIProviderError, DatabaseError, ItemNotFoundError, ProcessingError
from .services.processing import ProcessingQueue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Cortex backend...")
    await init_database()
    queue = ProcessingQueue()
    app.state.processing_queue = queue
    await queue.start()
    yield
    logger.info("Shutting down Cortex backend...")
    await queue.stop()

app = FastAPI(title="Cortex Backend", lifespan=lifespan)

# Exception handlers (see error-handling.md for patterns)
@app.exception_handler(ItemNotFoundError)
async def item_not_found_handler(request: Request, exc: ItemNotFoundError):
    return JSONResponse(status_code=404, content={"error": exc.error_code, "message": str(exc)})

@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    return JSONResponse(status_code=500, content={"error": exc.error_code, "message": "Internal database error"})

@app.exception_handler(AIProviderError)
async def ai_provider_error_handler(request: Request, exc: AIProviderError):
    return JSONResponse(status_code=503, content={"error": exc.error_code, "message": str(exc)})

@app.exception_handler(ProcessingError)
async def processing_error_handler(request: Request, exc: ProcessingError):
    return JSONResponse(status_code=500, content={"error": exc.error_code, "message": str(exc)})

# CORS for Tauri webview
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "tauri://localhost",
        "http://localhost",
        "http://localhost:1420",
        "http://127.0.0.1",
        "http://127.0.0.1:1420",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router, prefix="/api")
app.include_router(items_router, prefix="/api")
app.include_router(processing_router, prefix="/api")
```

### Route Example

```python
# src/api/items.py
from fastapi import APIRouter, Depends, Query, Response

from ..db.models import Item, ItemCreate, ItemListResponse, ItemUpdate
from ..db.repositories import ItemRepository
from ..exceptions import ItemNotFoundError
from ..services.processing import ProcessingQueue
from .deps import get_db_connection, get_item_repo, get_processing_queue

router = APIRouter(prefix="/items", tags=["items"])

@router.post("/", response_model=Item, status_code=201,
             responses={422: {"description": "Validation error"}})
async def create_item(
    data: ItemCreate,
    db: aiosqlite.Connection = Depends(get_db_connection),
    repo: ItemRepository = Depends(get_item_repo),
    queue: ProcessingQueue = Depends(get_processing_queue),
) -> Item:
    """Create a new item and enqueue for background processing."""
    item = await repo.create(db, data)
    await db.commit()
    await queue.enqueue(item.id)
    return item

@router.get("/", response_model=ItemListResponse)
async def list_items(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: aiosqlite.Connection = Depends(get_db_connection),
    repo: ItemRepository = Depends(get_item_repo),
) -> ItemListResponse:
    """List items with pagination."""
    items = await repo.list(db, offset=offset, limit=limit)
    total = await repo.count(db)
    return ItemListResponse(items=items, total=total, offset=offset, limit=limit)

@router.delete("/{id}", status_code=204,
               responses={404: {"description": "Item not found"}})
async def delete_item(
    id: str,
    db: aiosqlite.Connection = Depends(get_db_connection),
    repo: ItemRepository = Depends(get_item_repo),
) -> Response:
    """Delete an item."""
    deleted = await repo.delete(db, id)
    if not deleted:
        raise ItemNotFoundError(item_id=id)
    await db.commit()
    return Response(status_code=204)
```

### Dependency Injection

Use `deps.py` to provide database connections and repositories to routes:

```python
# src/api/deps.py
from collections.abc import AsyncIterator

import aiosqlite

from ..db.database import db_connection
from ..db.repositories import ItemRepository, item_repo

async def get_db_connection() -> AsyncIterator[aiosqlite.Connection]:
    """Async generator for FastAPI Depends().

    Wraps db_connection() context manager for dependency injection.
    """
    async with db_connection() as db:
        yield db

def get_item_repo() -> ItemRepository:
    """Get the ItemRepository singleton.

    Repositories are stateless - db connection is passed per method.
    """
    return item_repo
```

**Usage in routes:**

```python
@router.post("/", response_model=Item)
async def create_item(
    data: ItemCreate,
    db: aiosqlite.Connection = Depends(get_db_connection),
    repo: ItemRepository = Depends(get_item_repo),
) -> Item:
    item = await repo.create(db, data)
    await db.commit()  # Caller controls transaction
    return item
```

**When to use each:**

| Dependency                | Use For                                             |
| ------------------------- | --------------------------------------------------- |
| `get_db_connection()`     | All database operations - routes manage connections |
| `get_item_repo()`         | Item CRUD - stateless singleton                     |
| `get_chunk_repo()`        | Chunk CRUD - stateless singleton                    |
| `get_ai_provider()`       | AI operations (embedding, chat, extraction)         |
| `get_embedding_service()` | Embedding generation with model consistency         |
| `get_processing_queue()`  | Background processing queue from `app.state`        |

### Service Dependencies

Services receive the database connection via method parameters, not constructor. This enables transaction batching across multiple operations.

```python
# src/api/deps.py
async def get_ai_provider() -> AsyncIterator[AIProvider]:
    """Get the configured AI provider."""
    yield OllamaProvider()  # MVP: Ollama; later: switch based on settings

async def get_embedding_service(
    provider: AIProvider = Depends(get_ai_provider),
) -> AsyncIterator[EmbeddingService]:
    """Get embedding service with injected provider."""
    yield EmbeddingService(provider=provider)
```

**Pattern: DB via method parameter, caller commits.**

```python
# ✅ GOOD: Service works with any connection, caller controls transaction
async def embed_chunks(self, db: aiosqlite.Connection, chunks: list[Chunk]) -> None:
    # ... generates embeddings, stores in vec_chunks ...
    # Does NOT commit - caller is responsible

# Usage in endpoint
service = EmbeddingService(provider)
await service.embed_chunks(db, chunks)
await db.commit()  # Route commits after all operations succeed
```

This pattern:

- Uses FastAPI's dependency injection with `Depends()`
- Leverages async generators for automatic connection cleanup
- Keeps route functions focused on business logic
- Makes testing easier (dependencies can be overridden)

### Dynamic Status Codes

When a response's HTTP status code depends on the response content (e.g., health checks returning 200 or 503), use `JSONResponse` with explicit `status_code`:

```python
from fastapi import APIRouter
from fastapi.responses import JSONResponse

@router.get("/health", response_model=HealthResponse,
            responses={200: {...}, 503: {...}})
async def health_check(db = Depends(get_db_connection)) -> JSONResponse:
    # ... check components ...
    status_code = 200 if overall_status == "healthy" else 503

    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(mode="json"),
    )
```

See `src/api/health.py` for the full implementation.

### WebSocket Streaming

```python
# src/api/chat.py
from fastapi import WebSocket, WebSocketDisconnect

@router.websocket("/ws/chat/{conversation_id}")
async def chat_websocket(
    websocket: WebSocket,
    conversation_id: str
):
    await websocket.accept()

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = data.get("message")

            # Stream response
            async for chunk in chat_workflow.stream(conversation_id, message):
                await websocket.send_json({
                    "type": "chunk",
                    "content": chunk
                })

            # Send completion signal
            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        pass
```

## Database Layer

The database module (`src/db/database.py`) provides:

- `init_database()` - Initialize schema and extensions on startup
- `verify_database()` - Check database status (used by `/api/db/status`)
- `get_connection()` - Async generator for connection management

### Connection Management

```python
# src/db/database.py
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import aiosqlite
import sqlite_vec

async def _load_sqlite_vec(db: aiosqlite.Connection) -> None:
    """Load the sqlite-vec extension."""
    await db.enable_load_extension(True)
    await db.execute("SELECT load_extension(?)", [sqlite_vec.loadable_path()])
    await db.enable_load_extension(False)

async def _configure_connection(db: aiosqlite.Connection) -> None:
    """Shared connection setup (PRAGMA, extensions, row factory)."""
    await db.execute("PRAGMA foreign_keys = ON")
    await _load_sqlite_vec(db)
    db.row_factory = aiosqlite.Row

@asynccontextmanager
async def db_connection() -> AsyncIterator[aiosqlite.Connection]:
    """Context manager for database connections.

    Use directly for LangGraph nodes, scripts, background tasks.
    For FastAPI routes, use get_db_connection() from api.deps.
    """
    async with aiosqlite.connect(settings.db_path) as db:
        await _configure_connection(db)
        yield db
```

**Usage patterns:**

- **FastAPI routes**: `Depends(get_db_connection)` - wraps context manager
- **LangGraph nodes**: `async with db_connection() as db:` - direct usage
- **Scripts/tests**: `async with db_connection() as db:` - direct usage

### Database Initialization

Database initialization happens during FastAPI startup via the lifespan manager (see the Main Application example above for the full lifespan including `ProcessingQueue`):

```python
# src/main.py (startup portion)
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    queue = ProcessingQueue()
    app.state.processing_queue = queue
    await queue.start()  # Recovers pending items from DB
    yield
    await queue.stop()
```

The `init_database()` function:

1. Creates the `~/.cortex/` directory if needed
2. Loads the sqlite-vec extension
3. Applies schema from `schema.sql` (tables, FTS, triggers, indexes)
4. Creates `vec_chunks` table programmatically (requires extension to be loaded first)

See [sqlite-vec documentation](../data-storage/sqlite-vec.md) for schema details.

### Repository Pattern

Repositories provide type-safe database access using Pydantic models. **Repositories are stateless** - database connections are passed via method parameters, enabling callers to control transaction boundaries.

#### Key Principles

1. **Stateless**: No `__init__` with db connection - db passed per method
2. **Caller commits**: Methods do NOT commit - atomic transactions are caller's responsibility
3. **Singleton instances**: Module-level singletons for shared access

#### Pydantic Models

```python
# src/db/models.py
from pydantic import BaseModel, Field

class ItemCreate(BaseModel):
    """Input model for creating an item."""
    title: str
    content: str
    content_type: str = Field(description="Type: 'webpage', 'note', 'file'")
    source_url: str | None = None

class ItemUpdate(BaseModel):
    """Input model for updating. All fields optional."""
    title: str | None = None
    content: str | None = None

class Item(BaseModel):
    """Output model representing a stored item."""
    id: str
    title: str
    content: str
    content_type: str
    processing_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

#### BaseRepository

Generic abstract class defining stateless CRUD interface:

```python
# src/db/repositories/base.py
class BaseRepository(ABC, Generic[T, CreateT, UpdateT]):
    """Abstract base repository with generic CRUD operations.

    Repositories are stateless - db connections passed via method parameters.
    This allows callers to control transaction boundaries and commit timing.

    Exception Handling Strategy:
        - get() returns None if not found (caller decides to raise)
        - update() raises ItemNotFoundError if item doesn't exist
        - delete() returns False if item doesn't exist

    Transaction Strategy:
        - Methods do NOT commit - caller is responsible for committing
        - This allows atomic transactions across multiple operations
    """

    @property
    @abstractmethod
    def table_name(self) -> str: ...

    @abstractmethod
    async def create(self, db: aiosqlite.Connection, data: CreateT) -> T: ...

    @abstractmethod
    async def get(self, db: aiosqlite.Connection, id: str) -> T | None: ...

    @abstractmethod
    async def list(self, db: aiosqlite.Connection, offset: int = 0, limit: int = 20) -> list[T]: ...

    @abstractmethod
    async def update(self, db: aiosqlite.Connection, id: str, data: UpdateT) -> T: ...

    @abstractmethod
    async def delete(self, db: aiosqlite.Connection, id: str) -> bool: ...

    @abstractmethod
    async def count(self, db: aiosqlite.Connection) -> int: ...
```

#### Concrete Repository

```python
# src/db/repositories/items.py
class ItemRepository(BaseRepository[Item, ItemCreate, ItemUpdate]):
    """Repository for managing items. Stateless - db passed per method."""

    @property
    def table_name(self) -> str:
        return "items"

    async def create(self, db: aiosqlite.Connection, data: ItemCreate) -> Item:
        item_id = str(uuid4())
        await db.execute(...)
        # Does NOT commit - caller is responsible
        return await self.get(db, item_id)

    async def update(self, db: aiosqlite.Connection, id: str, data: ItemUpdate) -> Item:
        existing = await self.get(db, id)
        if existing is None:
            raise ItemNotFoundError(item_id=id)
        # ... perform update, no commit
```

#### Singleton Instances

Module-level singletons are exported for shared access:

```python
# src/db/repositories/__init__.py
from .items import ItemRepository
from .chunks import ChunkRepository
from .app_metadata import AppMetadataRepository

# Singleton instances (stateless repos)
item_repo = ItemRepository()
chunk_repo = ChunkRepository()
metadata_repo = AppMetadataRepository()
```

Usage:

```python
# In FastAPI routes (via dependency injection)
from ..db.repositories import item_repo
item = await item_repo.create(db, data)
await db.commit()

# In LangGraph workflows (direct usage)
from src.db.repositories import item_repo
async with db_connection() as db:
    item = await item_repo.get(db, item_id)
    await item_repo.update_status(db, item_id, "processing")
    await db.commit()
```

#### When NOT to Extend BaseRepository

Use a standalone class when access patterns differ significantly. Example: `ChunkRepository` doesn't extend `BaseRepository` because:

- Chunks use batch operations (`create_many`) instead of single-item creates
- Chunks are always accessed relative to a parent item (`get_by_item`, `delete_by_item`)
- Standard CRUD semantics don't fit the parent-child relationship

```python
# src/db/repositories/chunks.py
class ChunkRepository:
    """Standalone repository for chunk-specific access patterns.

    Stateless - db passed per method. Does NOT commit.
    """

    async def create_many(self, db: aiosqlite.Connection, chunks: list[ChunkCreate]) -> list[Chunk]: ...
    async def get_by_item(self, db: aiosqlite.Connection, item_id: str) -> list[Chunk]: ...
    async def delete_by_item(self, db: aiosqlite.Connection, item_id: str) -> int: ...
```

#### Transaction Boundaries

The caller controls when to commit, enabling atomic multi-operation transactions:

```python
# ✅ GOOD: Single atomic commit after multiple operations
async with db_connection() as db:
    chunks = await chunk_repo.create_many(db, chunk_creates)
    await embedding_service.embed_chunks(db, chunks)
    await item_repo.update(db, item_id, ItemUpdate(metadata=metadata))
    await db.commit()  # All-or-nothing

# ❌ BAD: Auto-commit in repository leaves orphaned data on failure
async def create(self, db, data):
    await db.execute(...)
    await db.commit()  # Don't do this - caller should commit
```

#### Row-to-Model Conversion

All repositories use a private `_row_to_*` method for consistent database row mapping:

```python
def _row_to_item(self, row: aiosqlite.Row) -> Item:
    """Convert database row to Pydantic model."""
    # Handle JSON fields
    metadata = row["metadata"]
    if metadata is not None and isinstance(metadata, str):
        metadata = json.loads(metadata)

    # Handle datetime conversion
    return Item(
        id=row["id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        # ...
    )
```

## Background Processing

### Task Queue

For long-running tasks, use the in-process `ProcessingQueue` with a fixed worker pool. See `src/services/processing.py` for the full implementation.

```python
# src/services/processing.py
import asyncio
from src.config import settings

QUEUE_MAXSIZE = 1000

class ProcessingQueue:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
        self._worker_tasks: list[asyncio.Task[None]] = []
        self._stopping = False

        # In-memory tracking (de-duplication + status)
        self._in_queue: set[str] = set()
        self.processing: set[str] = set()
        self.failed_items: set[str] = set()
        self.completed_count: int = 0
        self.total_processed: int = 0

    async def enqueue(self, item_id: str) -> bool:
        """Enqueue with backpressure/dedupe; returns True only if newly queued."""
        if item_id in self._in_queue or item_id in self.processing:
            return False
        self._in_queue.add(item_id)  # Reserve early for concurrent dedup
        await self.queue.put(item_id)  # Blocks when full (backpressure)
        return True

    async def start(self) -> None:
        """Start workers and recover pending/failed items from DB."""
        if self._worker_tasks:
            return  # Idempotent
        # Recover pending/processing items from DB, rebuild failed set
        worker_count = max(1, settings.max_concurrent_processing)
        self._worker_tasks = [
            asyncio.create_task(self._worker()) for _ in range(worker_count)
        ]

    async def stop(self) -> None:
        """Gracefully drain queue, then cancel workers."""
        self._stopping = True
        try:
            await asyncio.wait_for(self.queue.join(), timeout=5.0)
        except TimeoutError:
            pass
        for task in self._worker_tasks:
            task.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks = []

    async def get_queue_status(self) -> QueueStatus:
        """Return current queue status for API reporting.

        Async for forward compatibility (e.g. future database queries).
        """
        ...

    async def retry_failed(self, item_id: str | None = None) -> RetryFailedResult:
        """Re-enqueue failed items. Returns rich result for deterministic HTTP mapping."""
        ...
```

**Key design decisions:**

- **Fixed worker pool**: `max_concurrent_processing` workers loop on `queue.get()`, capping concurrency with stable task count
- **Bounded queue + backpressure**: `asyncio.Queue(maxsize=1000)` blocks producers via `await queue.put()` when saturated
- **De-duplication**: Items tracked in `_in_queue` and `processing` sets to prevent double-processing
- **Status ownership**: The LangGraph workflow owns DB status updates; the queue only tracks in-memory state for reporting
- **Startup recovery**: On startup, re-enqueue `pending`/`processing` items and rebuild `failed_items` set from DB
- **Idempotent lifecycle**: `start()` and `stop()` guard against duplicate calls
- **Singleton**: Managed via `app.state.processing_queue` in FastAPI lifespan
- **Auto-enqueue on item creation**: `create_item` endpoint enqueues after commit (see Route Example above)
- **Rich result model**: `retry_failed()` returns `RetryFailedResult` (with `outcome` and `retried_count`) instead of a plain `int`, enabling the API layer to map outcomes to HTTP status codes without inspecting queue internals

### Rich Service Result Pattern

When a service method's outcome affects the HTTP response status, return a structured result model instead of a primitive. This keeps HTTP semantics in the API layer while giving it enough context to make the right decision.

```python
# ❌ BAD: API layer must guess meaning from an int
async def retry_failed(self, item_id: str | None = None) -> int:
    ...  # Returns count, but what does 0 mean? Not found? Already queued?

# ✅ GOOD: Rich result with explicit outcome
class RetryFailedResult(BaseModel):
    requested_item_id: str | None = None
    retried_count: int = 0
    outcome: Literal["retried", "already_queued", "not_in_queue"] = "retried"

async def retry_failed(self, item_id: str | None = None) -> RetryFailedResult:
    ...  # API layer checks outcome to decide 200 vs 404
```

The API layer can then do a **two-layer existence check** when the service reports `"not_in_queue"`: the queue only knows in-memory state, so the endpoint does a secondary DB lookup to distinguish "item doesn't exist" (404) from "item exists but isn't queued" (200). See `src/api/processing.py` for the full implementation.

## Configuration

### Settings Management

```python
# src/config.py
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from pydantic_settings import BaseSettings

def get_app_version() -> str:
    """Get application version from package metadata."""
    try:
        return version("cortex-backend")
    except PackageNotFoundError:
        return "0.0.0-dev"

class Settings(BaseSettings):
    # Database
    db_path: Path = Path.home() / ".cortex" / "cortex.db"

    # Server
    host: str = "127.0.0.1"
    port: int = 8742

    # AI Provider
    ai_provider: str = "ollama"  # ollama, openai, hybrid
    ollama_host: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    chat_model: str = "llama3.2:3b"

    # Processing
    max_concurrent_processing: int = 2
    chunk_size: int = 500
    chunk_overlap: int = 50

    model_config = {"env_prefix": "CORTEX_"}

settings = Settings()
```

## Error Handling

See [Error Handling](../architecture/error-handling.md#python-error-handling) for Python exception patterns, FastAPI exception handlers, and error response formats.

## Testing

See [Testing](../quality-tooling/testing.md#python-testing) for pytest setup, fixtures, and example tests.

## Related Documentation

- [Python Sidecar](../architecture/python-sidecar.md) - Why this architecture
- [Bundling](./bundling.md) - Packaging Python for distribution
- [LangGraph Workflows](../ai/workflows.md) - AI workflow implementation
