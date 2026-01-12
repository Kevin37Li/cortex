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
│   │   ├── models.py          # SQLAlchemy/Pydantic models
│   │   └── repositories/      # Data access patterns
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

# Health
GET    /api/health             # Backend health check
GET    /api/health/ollama      # Ollama status
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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .api import items, search, chat, settings
from .db.database import init_db, close_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()

app = FastAPI(
    title="Cortex Backend",
    lifespan=lifespan
)

# CORS for Tauri webview
app.add_middleware(
    CORSMiddleware,
    allow_origins=["tauri://localhost", "http://localhost:*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(items.router, prefix="/api/items", tags=["items"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}
```

### Route Example

```python
# src/api/items.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

router = APIRouter()

class CreateItemRequest(BaseModel):
    url: str | None = None
    title: str
    content: str
    source: str = "manual"

class ItemResponse(BaseModel):
    id: str
    title: str
    status: str
    created_at: datetime

@router.post("/", response_model=ItemResponse)
async def create_item(
    request: CreateItemRequest,
    background_tasks: BackgroundTasks,
    db: Database = Depends(get_db)
):
    # Create item record
    item = await db.items.create(
        url=request.url,
        title=request.title,
        content=request.content,
        source=request.source,
        status="pending"
    )

    # Queue processing in background
    background_tasks.add_task(process_item, item.id)

    return ItemResponse(
        id=item.id,
        title=item.title,
        status=item.status,
        created_at=item.created_at
    )
```

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

### Connection Management

```python
# src/db/database.py
import aiosqlite
from pathlib import Path

DATABASE_PATH = Path.home() / ".cortex" / "cortex.db"

class Database:
    def __init__(self):
        self.conn: aiosqlite.Connection | None = None

    async def connect(self):
        self.conn = await aiosqlite.connect(DATABASE_PATH)
        # Enable sqlite-vec extension
        await self.conn.enable_load_extension(True)
        await self.conn.load_extension("vec0")
        await self.conn.enable_load_extension(False)

    async def close(self):
        if self.conn:
            await self.conn.close()

# Dependency injection
async def get_db() -> Database:
    db = Database()
    await db.connect()
    try:
        yield db
    finally:
        await db.close()
```

### Repository Pattern

```python
# src/db/repositories/items.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Item:
    id: str
    title: str
    url: str | None
    content: str
    status: str
    created_at: datetime
    processed_at: datetime | None

class ItemRepository:
    def __init__(self, db: Database):
        self.db = db

    async def create(self, **kwargs) -> Item:
        item_id = str(uuid4())
        await self.db.conn.execute("""
            INSERT INTO items (id, title, url, content, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [item_id, kwargs["title"], kwargs.get("url"), kwargs["content"],
              "pending", datetime.utcnow()])
        await self.db.conn.commit()
        return await self.get(item_id)

    async def get(self, item_id: str) -> Item | None:
        cursor = await self.db.conn.execute(
            "SELECT * FROM items WHERE id = ?", [item_id]
        )
        row = await cursor.fetchone()
        return Item(**row) if row else None
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
from pydantic_settings import BaseSettings
from pathlib import Path

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

    class Config:
        env_prefix = "CORTEX_"

settings = Settings()
```

## Error Handling

### Custom Exceptions

```python
# src/exceptions.py
class CortexError(Exception):
    """Base exception for Cortex backend."""
    pass

class ItemNotFoundError(CortexError):
    """Item does not exist."""
    pass

class ProcessingError(CortexError):
    """Error during content processing."""
    pass

class AIProviderError(CortexError):
    """Error from AI provider."""
    pass
```

### Exception Handlers

```python
# src/main.py
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(ItemNotFoundError)
async def item_not_found_handler(request: Request, exc: ItemNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": "item_not_found", "message": str(exc)}
    )

@app.exception_handler(ProcessingError)
async def processing_error_handler(request: Request, exc: ProcessingError):
    return JSONResponse(
        status_code=500,
        content={"error": "processing_error", "message": str(exc)}
    )
```

## Testing

### Test Setup

```python
# tests/conftest.py
import pytest
from httpx import AsyncClient
from src.main import app
from src.db.database import Database

@pytest.fixture
async def db():
    """In-memory database for tests."""
    db = Database(":memory:")
    await db.connect()
    await db.run_migrations()
    yield db
    await db.close()

@pytest.fixture
async def client(db):
    """Test client with mocked database."""
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

### Example Tests

```python
# tests/api/test_items.py
import pytest

@pytest.mark.asyncio
async def test_create_item(client):
    response = await client.post("/api/items", json={
        "title": "Test Item",
        "content": "Test content",
        "source": "test"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Item"
    assert data["status"] == "pending"
```

## Related Documentation

- [Python Sidecar](../architecture/python-sidecar.md) - Why this architecture
- [Bundling](./bundling.md) - Packaging Python for distribution
- [LangGraph Workflows](../ai/workflows.md) - AI workflow implementation
