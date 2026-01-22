# Task: Implement Ollama Provider Integration

## Summary

Create a provider abstraction for Ollama that enables local AI inference for embeddings and chat, with health checking. Implements the `AIProvider` interface documented in `docs/developer/ai/overview.md`.

## Acceptance Criteria

- [x] `AIProvider` abstract base class with `embed`, `embed_batch`, `chat`, `stream_chat` methods
- [x] `OllamaProvider` class implementing `AIProvider` interface
- [x] `GET /api/health/ollama` - Dedicated endpoint for Ollama status and models
- [x] Ollama added as component check in existing `/api/health` endpoint
- [x] Custom exception types (`AIProviderError`, `OllamaNotRunningError`, `OllamaModelNotFoundError`)
- [x] Pydantic models for type-safe responses (`ModelInfo`, `OllamaHealthResponse`)
- [x] Dependency injection via `get_ollama_provider()` in `deps.py`
- [x] Graceful handling when Ollama is not running
- [x] Configurable timeouts for requests

## Dependencies

- Task 1: Python backend project structure
- Task 5: Health check endpoint

## Existing Configuration

The following settings already exist in `python-backend/src/config.py` and should be used:

```python
ollama_host: str = "http://localhost:11434"
embedding_model: str = "nomic-embed-text"
chat_model: str = "llama3.2"
```

Add timeout settings to `Settings` class:

```python
ollama_timeout: float = 30.0  # General request timeout (seconds)
ollama_embed_timeout: float = 60.0  # Embedding may take longer
```

## Technical Notes

- Ollama API: `POST /api/embeddings`, `POST /api/generate`, `POST /api/chat`
- Use `httpx` for async HTTP client (move from dev to main dependencies)
- nomic-embed-text produces 768-dimension embeddings
- Ollama may not be running - handle gracefully with custom exceptions
- First request after startup loads model into memory (~5-15 seconds) - use appropriate timeouts

## Ollama API Reference

```python
# Generate embeddings
POST http://localhost:11434/api/embeddings
{
    "model": "nomic-embed-text",
    "prompt": "text to embed"
}
Response: { "embedding": [0.1, 0.2, ...] }

# Chat completion
POST http://localhost:11434/api/chat
{
    "model": "llama3.2",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
}
Response: { "message": {"role": "assistant", "content": "..."} }

# Streaming chat
POST http://localhost:11434/api/chat
{
    "model": "llama3.2",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": true
}
Response: Server-sent events with partial content

# List models
GET http://localhost:11434/api/tags
Response: { "models": [{"name": "nomic-embed-text", "size": 274302450, ...}] }
```

## Provider Interface

Implements the `AIProvider` interface from `docs/developer/ai/overview.md`:

```python
# python-backend/src/providers/base.py
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

class AIProvider(ABC):
    """Abstract base class for AI providers (Ollama, OpenAI, etc.)."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        ...

    @abstractmethod
    async def chat(self, messages: list[dict], system: str | None = None) -> str:
        """Generate chat completion."""
        ...

    @abstractmethod
    async def stream_chat(
        self, messages: list[dict], system: str | None = None
    ) -> AsyncIterator[str]:
        """Stream chat completion tokens."""
        ...


# python-backend/src/providers/ollama.py
class OllamaProvider(AIProvider):
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        embedding_model: str = "nomic-embed-text",
        chat_model: str = "llama3.2",
        timeout: float = 30.0,
        embed_timeout: float = 60.0,
    ) -> None: ...

    async def is_available(self) -> bool: ...
    async def list_models(self) -> list[ModelInfo]: ...

    # AIProvider implementation
    async def embed(self, text: str) -> list[float]: ...
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
    async def chat(self, messages: list[dict], system: str | None = None) -> str: ...
    async def stream_chat(
        self, messages: list[dict], system: str | None = None
    ) -> AsyncIterator[str]: ...
```

## Exception Types

Add to `python-backend/src/exceptions.py`:

```python
class AIProviderError(CortexError):
    """Base exception for AI provider errors."""
    pass


class OllamaNotRunningError(AIProviderError):
    """Ollama server is not accessible."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        super().__init__(f"Ollama not running at {base_url}")


class OllamaModelNotFoundError(AIProviderError):
    """Requested model not found in Ollama."""

    def __init__(self, model: str) -> None:
        self.model = model
        super().__init__(f"Model not found: {model}. Run: ollama pull {model}")


class OllamaTimeoutError(AIProviderError):
    """Request to Ollama timed out."""

    def __init__(self, operation: str, timeout: float) -> None:
        self.operation = operation
        self.timeout = timeout
        super().__init__(f"Ollama {operation} timed out after {timeout}s")
```

Register exception handler in `main.py`:

```python
@app.exception_handler(AIProviderError)
async def ai_provider_error_handler(
    request: Request, exc: AIProviderError
) -> JSONResponse:
    return JSONResponse(
        status_code=503,  # Service Unavailable
        content={"detail": str(exc), "error_type": type(exc).__name__},
    )
```

## Pydantic Models

Add to `python-backend/src/db/models.py` or create `python-backend/src/providers/models.py`:

```python
from pydantic import BaseModel
from datetime import datetime


class ModelInfo(BaseModel):
    """Information about an Ollama model."""
    name: str
    size: int | None = None
    modified_at: datetime | None = None
    digest: str | None = None


class OllamaHealthResponse(BaseModel):
    """Response for Ollama health check endpoint."""
    status: str  # "healthy" | "unavailable"
    base_url: str
    models: list[str] | None = None
    error: str | None = None
    latency_ms: float | None = None
```

## Dependency Injection

Add to `python-backend/src/api/deps.py`:

```python
from collections.abc import AsyncIterator
from src.providers.ollama import OllamaProvider
from src.config import settings


async def get_ollama_provider() -> AsyncIterator[OllamaProvider]:
    """Get OllamaProvider instance configured from settings."""
    provider = OllamaProvider(
        base_url=settings.ollama_host,
        embedding_model=settings.embedding_model,
        chat_model=settings.chat_model,
        timeout=settings.ollama_timeout,
        embed_timeout=settings.ollama_embed_timeout,
    )
    yield provider
```

## Files to Create/Modify

**Create:**

- `python-backend/src/providers/base.py` - AIProvider abstract base class
- `python-backend/src/providers/ollama.py` - OllamaProvider implementation
- `python-backend/src/providers/models.py` - Pydantic models for providers

**Modify:**

- `python-backend/src/api/health.py` - Add `/api/health/ollama` endpoint and Ollama component check
- `python-backend/src/api/deps.py` - Add `get_ollama_provider()` dependency
- `python-backend/src/exceptions.py` - Add AI provider exceptions
- `python-backend/src/main.py` - Register `AIProviderError` exception handler
- `python-backend/src/config.py` - Add timeout settings
- `python-backend/pyproject.toml` - Move `httpx` from dev to main dependencies

## Health Check Integration

Two integration points:

1. **Dedicated endpoint** `GET /api/health/ollama` - Returns detailed Ollama status with model list
2. **Component check** in existing `GET /api/health` - Add Ollama to the `checks` dictionary

```python
# In health.py
@router.get("/ollama", response_model=OllamaHealthResponse)
async def check_ollama_health(
    provider: OllamaProvider = Depends(get_ollama_provider),
) -> OllamaHealthResponse:
    """Check Ollama availability and list models."""
    start = time.perf_counter()
    try:
        if await provider.is_available():
            models = await provider.list_models()
            return OllamaHealthResponse(
                status="healthy",
                base_url=provider.base_url,
                models=[m.name for m in models],
                latency_ms=(time.perf_counter() - start) * 1000,
            )
    except Exception as e:
        return OllamaHealthResponse(
            status="unavailable",
            base_url=provider.base_url,
            error=str(e),
        )
```

## Verification

```bash
# Start Ollama first
ollama serve

# Check Ollama health (dedicated endpoint)
curl http://localhost:8742/api/health/ollama

# Response when Ollama is running:
{
    "status": "healthy",
    "base_url": "http://localhost:11434",
    "models": ["nomic-embed-text", "llama3.2"],
    "latency_ms": 45.2
}

# Response when Ollama is not running:
{
    "status": "unavailable",
    "base_url": "http://localhost:11434",
    "error": "Connection refused"
}

# Main health check includes Ollama component
curl http://localhost:8742/api/health

# Response includes:
{
    "status": "healthy",
    "checks": {
        "database": {"status": "healthy", ...},
        "ollama": {"status": "healthy", ...}
    }
}
```

---

## Implementation Details

_Tracked: 2026-01-22_

### Files Changed

| File | Change | Description |
|------|--------|-------------|
| `python-backend/src/providers/base.py` | Created | AIProvider abstract base class with embed, embed_batch, chat, stream_chat methods |
| `python-backend/src/providers/models.py` | Created | Pydantic models: ModelInfo, OllamaHealthResponse |
| `python-backend/src/providers/ollama.py` | Created | OllamaProvider implementing AIProvider with is_available, list_models |
| `python-backend/src/providers/__init__.py` | Modified | Export AIProvider, OllamaProvider, ModelInfo, OllamaHealthResponse |
| `python-backend/src/exceptions.py` | Modified | Added AIProviderError, OllamaNotRunningError, OllamaModelNotFoundError, OllamaTimeoutError, OllamaAPIResponseError |
| `python-backend/src/api/health.py` | Modified | Added /health/ollama endpoint and Ollama component check in /health |
| `python-backend/src/api/deps.py` | Modified | Added get_ollama_provider() dependency |
| `python-backend/src/config.py` | Modified | Added ollama_timeout, ollama_embed_timeout, ollama_availability_timeout settings |
| `python-backend/src/main.py` | Modified | Added AIProviderError exception handler returning 503 |
| `python-backend/pyproject.toml` | Modified | Moved httpx from dev to main dependencies |
| `python-backend/tests/test_providers_ollama.py` | Created | 24 tests for OllamaProvider class |
| `python-backend/tests/test_api_health_ollama.py` | Created | 7 tests for Ollama health endpoints |
| `python-backend/tests/test_api_health.py` | Modified | Updated mock to include Ollama provider dependency |

### Code Metrics

- **New files:** 5 (base.py, models.py, ollama.py, test_providers_ollama.py, test_api_health_ollama.py)
- **New lines:** ~1,100 (1,100 in new files + ~406 modified)
- **Tests added:** 31 tests (24 provider tests + 7 health endpoint tests)
- **Exceptions added:** 5 (AIProviderError, OllamaNotRunningError, OllamaModelNotFoundError, OllamaTimeoutError, OllamaAPIResponseError)

### Dependencies

- `httpx` - Moved from dev to main dependencies for async HTTP client

### Acceptance Criteria Implementation Locations

- [x] `AIProvider` abstract base class - `src/providers/base.py:7-78`
- [x] `OllamaProvider` class - `src/providers/ollama.py:19-254`
- [x] `GET /api/health/ollama` - `src/api/health.py:96-125`
- [x] Ollama component check - `src/api/health.py:29-39`, `src/api/health.py:64`
- [x] Custom exception types - `src/exceptions.py:35-75`
- [x] Pydantic models - `src/providers/models.py:8-24`
- [x] Dependency injection - `src/api/deps.py:33-40`
- [x] Graceful handling - `src/providers/ollama.py:47-59` (is_available returns False instead of raising)
- [x] Configurable timeouts - `src/config.py:33-36`, `src/providers/ollama.py:25-32`

---

## Learning Report

_Generated: 2026-01-22_

### Summary

Implemented the Ollama AI provider integration with a clean abstraction layer. The implementation includes:

- An `AIProvider` abstract base class enabling future provider swapping (OpenAI, Anthropic, etc.)
- Complete `OllamaProvider` with embedding, chat, and streaming capabilities
- Health check integration at two levels: component check in `/health` and dedicated `/health/ollama`
- Comprehensive exception hierarchy for granular error handling
- Full test coverage with 31 tests using httpx mocking patterns

### Patterns & Decisions

#### 1. Provider Abstraction Pattern

Created `AIProvider` ABC to decouple the application from Ollama-specific implementation. This enables:

- Easy provider swapping via configuration
- Consistent interface for all AI operations
- Testability through mock providers

```python
class AIProvider(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...
    @abstractmethod
    async def chat(self, messages: list[dict], system: str | None = None) -> str: ...
```

#### 2. Settings-Based Defaults Pattern

Instead of hardcoding default values in the provider, defaults reference the centralized `settings` object:

```python
def __init__(
    self,
    base_url: str = settings.ollama_host,
    timeout: float = settings.ollama_timeout,
    ...
) -> None:
```

This ensures single source of truth and environment variable configurability via `CORTEX_` prefix.

#### 3. Graceful Degradation Pattern

The provider distinguishes between "availability check" and "operation failure":

- `is_available()` returns `bool` - used for health checks, never raises
- Operation methods (`embed`, `chat`) raise specific exceptions - used for actual work

This allows the health check to show "degraded" status when Ollama is down without crashing.

#### 4. Exception Hierarchy

Built a specific exception hierarchy under `AIProviderError`:

```
CortexError
└── AIProviderError
    ├── OllamaNotRunningError (connection refused)
    ├── OllamaModelNotFoundError (404 response)
    ├── OllamaTimeoutError (request timeout)
    └── OllamaAPIResponseError (malformed response)
```

Each exception includes contextual data (model name, URL, response data) for debugging.

#### 5. Dependency Injection Simplification

After centralizing defaults in settings, `deps.py` was simplified from explicit parameter passing:

```python
# Before (redundant)
provider = OllamaProvider(
    base_url=settings.ollama_host,
    embedding_model=settings.embedding_model,
    ...
)

# After (clean)
yield OllamaProvider()
```

### Challenges & Solutions

#### 1. Malformed API Response Handling

**Challenge:** Initial implementation silently returned empty data (`[]` or `""`) when Ollama API returned unexpected responses. This could mask bugs and make debugging difficult.

**Solution:** Added `OllamaAPIResponseError` exception that is raised when expected keys are missing from the response. The exception includes the full response data for debugging:

```python
if embedding is None:
    raise OllamaAPIResponseError("embed", self.embedding_model, data)
```

#### 2. Multiple Timeout Requirements

**Challenge:** Different operations need different timeouts:
- Health checks: fast (5s) - don't want to wait long
- Chat: moderate (30s) - user-facing operations
- Embeddings: long (60s) - first request loads model into memory

**Solution:** Added three distinct timeout settings:

```python
ollama_timeout: float = 30.0           # General requests
ollama_embed_timeout: float = 60.0     # Embedding (model loading)
ollama_availability_timeout: float = 5.0  # Quick health checks
```

#### 3. Health Check Status Granularity

**Challenge:** Main `/health` endpoint needed to integrate Ollama without making Ollama failures crash the entire health check.

**Solution:** Introduced "degraded" status when some components are healthy:

```python
if all_healthy:
    overall_status = "healthy"
elif any_healthy:
    overall_status = "degraded"  # DB up, Ollama down
else:
    overall_status = "unhealthy"
```

### Lessons Learned

#### What Worked Well

1. **Task spec completeness** - The task document provided exact API formats, exception signatures, and file locations. This reduced ambiguity significantly.

2. **Test-first mindset** - Writing comprehensive tests caught the malformed response issue during CodeRabbit review.

3. **Centralized configuration** - Using pydantic-settings with environment prefix (`CORTEX_`) enables easy deployment configuration.

4. **Async throughout** - Using `httpx.AsyncClient` with context managers ensures proper resource cleanup.

#### What Could Be Improved

1. **Batch embedding efficiency** - Current `embed_batch` calls `embed` sequentially. Future optimization could use concurrent requests or Ollama's native batch support if available.

2. **Connection pooling** - Each request creates a new `AsyncClient`. Consider a persistent client for high-throughput scenarios.

3. **Retry logic** - No automatic retries on transient failures. Could add exponential backoff for production resilience.

#### Recommendations for Future Tasks

1. When adding new providers (OpenAI, Anthropic), follow the same pattern: implement `AIProvider` interface, add provider-specific exceptions under `AIProviderError`.

2. The `availability_timeout` pattern (short timeout for health checks) should be applied to other external service integrations.

3. Consider adding a `MockProvider` for development/testing that doesn't require Ollama running.

### Documentation Impact

#### Existing Docs That Need Updates

1. **`docs/developer/ai/overview.md`** - Should be updated to reflect actual implementation:
   - Add exception types section
   - Document timeout configuration
   - Add health check integration details

2. **`docs/developer/ai/ollama.md`** - Should document:
   - Available configuration settings
   - Exception handling patterns
   - Health check endpoints

#### New Patterns to Document

1. **Provider abstraction pattern** - How to add new AI providers
2. **Graceful degradation** - `is_available()` vs operation methods pattern
3. **Settings-based defaults** - Using settings values as function defaults

#### Documentation Gaps Found

- No existing documentation on the exception handling patterns for external services
- Health check integration patterns not documented
