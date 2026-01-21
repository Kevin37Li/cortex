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
│   │   └── repositories/      # Data access patterns
│   │       ├── base.py        # Abstract BaseRepository
│   │       ├── items.py
│   │       ├── chunks.py
│   │       └── conversations.py
│   │
│   ├── services/              # Business logic
│   │   ├── __init__.py
│   │   ├── processing.py      # Item processing service
│   │   └── embeddings.py      # Embedding management
│   │
│   └── main.py                # FastAPI app entry point
│
├── tests/
│   ├── api/
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
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.health import router as health_router
from .api.items import router as items_router
from .db import init_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_database()
    yield
    # Shutdown (cleanup if needed)

app = FastAPI(title="Cortex Backend", lifespan=lifespan)

# CORS for Tauri webview
app.add_middleware(
    CORSMiddleware,
    allow_origins=["tauri://localhost", "http://localhost:*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router, prefix="/api")
app.include_router(items_router, prefix="/api")
```

### Route Example

```python
# src/api/items.py
from fastapi import APIRouter, Depends, Query, Response

from ..db.models import Item, ItemCreate, ItemListResponse, ItemUpdate
from ..db.repositories import ItemRepository
from ..exceptions import ItemNotFoundError
from .deps import get_item_repository

router = APIRouter(prefix="/items", tags=["items"])

@router.post("/", response_model=Item, status_code=201,
             responses={422: {"description": "Validation error"}})
async def create_item(
    data: ItemCreate,
    repo: ItemRepository = Depends(get_item_repository),
) -> Item:
    """Create a new item."""
    return await repo.create(data)

@router.get("/", response_model=ItemListResponse)
async def list_items(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    repo: ItemRepository = Depends(get_item_repository),
) -> ItemListResponse:
    """List items with pagination."""
    items = await repo.list(offset=offset, limit=limit)
    total = await repo.count()
    return ItemListResponse(items=items, total=total, offset=offset, limit=limit)

@router.delete("/{id}", status_code=204,
               responses={404: {"description": "Item not found"}})
async def delete_item(
    id: str,
    repo: ItemRepository = Depends(get_item_repository),
) -> Response:
    """Delete an item."""
    deleted = await repo.delete(id)
    if not deleted:
        raise ItemNotFoundError(id)
    return Response(status_code=204)
```

### Dependency Injection

Use `deps.py` to provide database access to routes. There are two patterns:

```python
# src/api/deps.py
from collections.abc import AsyncIterator

import aiosqlite

from ..db.database import get_connection
from ..db.repositories import ItemRepository

async def get_db_connection() -> AsyncIterator[aiosqlite.Connection]:
    """Get a raw database connection.

    Use for simple queries where repository abstraction is unnecessary.
    """
    async for db in get_connection():
        yield db

async def get_item_repository() -> AsyncIterator[ItemRepository]:
    """Get a repository instance with managed connection.

    Use for standard CRUD operations on domain entities.
    """
    async for db in get_connection():
        yield ItemRepository(db)
```

**When to use each:**

| Dependency              | Use For                                             |
| ----------------------- | --------------------------------------------------- |
| `get_db_connection()`   | Simple queries (`SELECT 1`), health checks, raw SQL |
| `get_item_repository()` | Domain entity CRUD, business logic requiring models |

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
import aiosqlite
import sqlite_vec

async def _load_sqlite_vec(db: aiosqlite.Connection) -> None:
    """Load the sqlite-vec extension."""
    await db.enable_load_extension(True)
    await db.execute("SELECT load_extension(?)", [sqlite_vec.loadable_path()])
    await db.enable_load_extension(False)

async def get_connection() -> AsyncIterator[aiosqlite.Connection]:
    """Async generator yielding configured database connections."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await _load_sqlite_vec(db)
        db.row_factory = aiosqlite.Row
        yield db
```

### Database Initialization

Database initialization happens during FastAPI startup via the lifespan manager:

```python
# src/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()  # Create tables, load extension, apply schema
    yield

app = FastAPI(title="Cortex Backend", lifespan=lifespan)
```

The `init_database()` function:

1. Creates the `~/.cortex/` directory if needed
2. Loads the sqlite-vec extension
3. Applies schema from `schema.sql` (tables, FTS, triggers, indexes)
4. Creates `vec_chunks` table programmatically (requires extension to be loaded first)

See [sqlite-vec documentation](../data-storage/sqlite-vec.md) for schema details.

### Repository Pattern

Repositories provide type-safe database access using Pydantic models. The pattern uses an abstract `BaseRepository` for standard CRUD operations, with flexibility for custom implementations when access patterns differ.

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

class ItemListResponse(BaseModel):
    """Paginated response for listing items."""
    items: list[Item]
    total: int
    offset: int
    limit: int
```

#### BaseRepository

Generic abstract class defining CRUD interface:

```python
# src/db/repositories/base.py
class BaseRepository(ABC, Generic[T, CreateT, UpdateT]):
    """Abstract base repository with generic CRUD operations.

    Exception Handling Strategy:
        - get() returns None if not found (caller decides to raise)
        - update() raises ItemNotFoundError if item doesn't exist
        - delete() returns False if item doesn't exist
    """

    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    @property
    @abstractmethod
    def table_name(self) -> str: ...

    @abstractmethod
    async def create(self, data: CreateT) -> T: ...

    @abstractmethod
    async def get(self, id: str) -> T | None: ...

    @abstractmethod
    async def list(self, offset: int = 0, limit: int = 20) -> list[T]: ...

    @abstractmethod
    async def update(self, id: str, data: UpdateT) -> T: ...

    @abstractmethod
    async def delete(self, id: str) -> bool: ...

    @abstractmethod
    async def count(self) -> int: ...
```

#### Concrete Repository

```python
# src/db/repositories/items.py
class ItemRepository(BaseRepository[Item, ItemCreate, ItemUpdate]):
    @property
    def table_name(self) -> str:
        return "items"

    def _row_to_item(self, row: aiosqlite.Row) -> Item:
        """Convert database row to Pydantic model."""
        return Item(
            id=row["id"],
            title=row["title"],
            # ... map all fields
        )

    async def create(self, data: ItemCreate) -> Item:
        item_id = str(uuid4())
        await self.db.execute(...)
        await self.db.commit()

        result = await self.get(item_id)
        if result is None:
            raise DatabaseError(f"Failed to retrieve created item: {item_id}")
        return result

    async def update(self, id: str, data: ItemUpdate) -> Item:
        existing = await self.get(id)
        if existing is None:
            raise ItemNotFoundError(id)
        # ... perform update
```

#### When NOT to Extend BaseRepository

Use a standalone class when access patterns differ significantly. Example: `ChunkRepository` doesn't extend `BaseRepository` because:

- Chunks use batch operations (`create_many`) instead of single-item creates
- Chunks are always accessed relative to a parent item (`get_by_item`, `delete_by_item`)
- Standard CRUD semantics don't fit the parent-child relationship

```python
# src/db/repositories/chunks.py
class ChunkRepository:
    """Standalone repository for chunk-specific access patterns."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create_many(self, chunks: list[ChunkCreate]) -> list[Chunk]: ...
    async def get_by_item(self, item_id: str) -> list[Chunk]: ...
    async def delete_by_item(self, item_id: str) -> int: ...
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

For long-running tasks, use a simple in-process queue:

```python
# src/services/processing.py
import asyncio
from collections import deque

class ProcessingQueue:
    def __init__(self):
        self.queue: deque[str] = deque()
        self.processing: set[str] = set()
        self._worker_task: asyncio.Task | None = None

    async def start(self):
        self._worker_task = asyncio.create_task(self._worker())

    async def stop(self):
        if self._worker_task:
            self._worker_task.cancel()

    async def enqueue(self, item_id: str):
        self.queue.append(item_id)

    async def _worker(self):
        while True:
            if self.queue:
                item_id = self.queue.popleft()
                self.processing.add(item_id)
                try:
                    await self._process_item(item_id)
                finally:
                    self.processing.discard(item_id)
            else:
                await asyncio.sleep(0.1)

    async def _process_item(self, item_id: str):
        # Run the processing workflow
        workflow = ProcessingWorkflow()
        await workflow.run(item_id)
```

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
