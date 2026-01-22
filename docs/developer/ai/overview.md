# AI Architecture Overview

How Cortex uses AI for understanding and retrieving knowledge.

## Design Principles

### 1. Provider Agnostic

The application doesn't care whether AI runs locally or in the cloud. All AI operations go through a unified interface defined in `python-backend/src/providers/base.py`:

```python
class AIProvider(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    async def chat(
        self, messages: list[dict[str, str]], system: str | None = None
    ) -> str: ...

    @abstractmethod
    async def stream_chat(
        self, messages: list[dict[str, str]], system: str | None = None
    ) -> AsyncIterator[str]: ...
```

This abstraction allows:

- Swapping providers without changing application code
- Testing with mock providers
- Fallback chains (try local, fall back to cloud)

### 2. Local by Default

Ollama is the default and recommended provider:

- Maximum privacy (nothing leaves the device)
- Works offline
- No ongoing costs
- User controls which models to use

Cloud APIs are available for users who need them, but never required.

### 3. Graceful Degradation

When AI operations fail:

- Retry with exponential backoff
- Fall back to simpler operations (e.g., keyword search if embedding fails)
- Never block the user from accessing their data
- Log failures for debugging

## Provider Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Provider Layer                         │
│                                                              │
│  ┌─────────────────────┐      ┌─────────────────────────┐   │
│  │       Ollama        │      │     LiteLLM Proxy       │   │
│  │      (Default)      │      │    (Cloud Providers)    │   │
│  │                     │      │                         │   │
│  │  • localhost:11434  │      │  • OpenAI               │   │
│  │  • Model management │      │  • Anthropic            │   │
│  │  • Health checks    │      │  • Google               │   │
│  └──────────┬──────────┘      └────────────┬────────────┘   │
│             └──────────────┬───────────────┘                │
│                            │                                 │
│                 ┌──────────▼──────────┐                     │
│                 │  Unified Interface   │                     │
│                 │  AIProvider base     │                     │
│                 └──────────┬──────────┘                     │
│                            │                                 │
└────────────────────────────┼────────────────────────────────┘
                             │
                  ┌──────────▼──────────┐
                  │  LangGraph Workflows │
                  │  • Processing        │
                  │  • Search            │
                  │  • Chat              │
                  └─────────────────────┘
```

## Model Selection

Different tasks have different model requirements:

| Task           | Local (Ollama)   | Cloud (OpenAI)         | Notes                         |
| -------------- | ---------------- | ---------------------- | ----------------------------- |
| **Embeddings** | nomic-embed-text | text-embedding-3-small | Consistency matters—don't mix |
| **Extraction** | llama3.2:3b      | gpt-4o-mini            | Structured output, fast       |
| **Chat**       | mistral:7b       | gpt-4o-mini            | Quality/speed tradeoff        |
| **Grading**    | llama3.2:3b      | gpt-4o-mini            | Simple yes/no decisions       |

### Model Recommendations by Hardware

| RAM   | Embedding Model  | Chat Model   | Notes              |
| ----- | ---------------- | ------------ | ------------------ |
| 8GB   | nomic-embed-text | llama3.2:3b  | Minimum viable     |
| 16GB  | nomic-embed-text | mistral:7b   | Good balance       |
| 32GB+ | nomic-embed-text | llama3.1:70b | Best local quality |

## User Configuration Flow

### First Launch

```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  How would you like Cortex to process your content?         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  🏠 Local AI (Recommended)                              │ │
│  │  Maximum privacy. Everything runs on your machine.      │ │
│  │  Requirements: 8GB RAM minimum                          │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ☁️ Cloud AI                                            │ │
│  │  Better for older hardware. Requires API key.          │ │
│  │  Cost: ~$0.10-1.00/month typical usage                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  🔀 Hybrid                                              │ │
│  │  Local by default, cloud for complex queries.          │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Settings UI

Users can change providers anytime in Settings > AI:

- Switch between local/cloud/hybrid
- Select specific models for each task
- View usage statistics
- Test provider connectivity

## Error Handling

Provider operations use a specific exception hierarchy under `AIProviderError` (see `python-backend/src/exceptions.py`). Each provider has specific exceptions (e.g., `OllamaNotRunningError`, `OllamaModelNotFoundError`).

### Key Patterns

- **`is_available()`** returns `bool` for health checks - never raises
- **Operation methods** (`embed`, `chat`) raise specific exceptions on failure
- **Fallback chains**: Try local provider, fall back to cloud if configured

```python
# Health check pattern - graceful degradation
if not await ollama_provider.is_available():
    if user_has_cloud_fallback:
        return await cloud_provider.embed(text)
    return "degraded"  # Don't crash

# Operations raise on failure - handle appropriately
embedding = await provider.embed(text)  # May raise provider-specific exception
```

See [Ollama Error Handling](./ollama.md#error-handling) for detailed exception hierarchy and handling patterns.

## Cost Estimation (Cloud)

When using cloud providers, track and display costs:

| Operation                      | Typical Cost       | Per 100 Items |
| ------------------------------ | ------------------ | ------------- |
| Embed (text-embedding-3-small) | $0.00002/1K tokens | ~$0.02        |
| Extract (gpt-4o-mini)          | $0.00015/1K tokens | ~$0.15        |
| Chat (gpt-4o-mini)             | $0.00015/1K tokens | ~$0.05/query  |

Display in UI: "Estimated cost this month: $0.12"

## Configuration

Provider settings are defined in `python-backend/src/config.py` and can be overridden via environment variables with the `CORTEX_` prefix (pydantic-settings pattern).

See provider-specific documentation for detailed configuration:

- [Ollama Configuration](./ollama.md#configuration) - Local inference settings
- [Cloud Providers](./cloud-providers.md) - API keys and cloud settings

## Health Check Integration

The main `/api/health` endpoint includes AI provider status as a component check. The overall status uses "degraded" when some components (like database) are healthy but others (like Ollama) are not.

See [Ollama Health Endpoints](./ollama.md#health-check-endpoints) for detailed endpoint documentation.

## Testing AI Features

### Mock Provider

For tests, use a mock provider that returns deterministic results:

```python
class MockAIProvider(AIProvider):
    async def embed(self, text: str) -> list[float]:
        # Return consistent embedding based on text hash
        # Use 768 dimensions to match nomic-embed-text
        return [hash(text) % 100 / 100.0] * 768

    async def chat(self, messages: list[dict[str, str]], system: str | None = None) -> str:
        return "Mock response for testing"
```

### Integration Tests

Test against real Ollama with small models:

- Use `llama3.2:1b` for fast CI runs
- Test embedding dimension consistency
- Verify streaming works correctly

## Related Documentation

- [Ollama Integration](./ollama.md) - Local AI setup and configuration
- [Cloud Providers](./cloud-providers.md) - OpenAI and other cloud APIs
- [Embeddings](./embeddings.md) - Vector embedding strategy
- [LangGraph Workflows](./workflows.md) - AI-powered processing pipelines
