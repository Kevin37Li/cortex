# AI Architecture Overview

How Cortex uses AI for understanding and retrieving knowledge.

## Design Principles

### 1. Provider Agnostic

The application doesn't care whether AI runs locally or in the cloud. All AI operations go through a unified interface:

```python
class AIProvider:
    async def embed(text: str) -> list[float]
    async def embed_batch(texts: list[str]) -> list[list[float]]
    async def chat(messages: list, system: str) -> str
    async def stream_chat(messages: list) -> AsyncIterator[str]
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

| Task | Local (Ollama) | Cloud (OpenAI) | Notes |
|------|----------------|----------------|-------|
| **Embeddings** | nomic-embed-text | text-embedding-3-small | Consistency matters—don't mix |
| **Extraction** | llama3.2:3b | gpt-4o-mini | Structured output, fast |
| **Chat** | mistral:7b | gpt-4o-mini | Quality/speed tradeoff |
| **Grading** | llama3.2:3b | gpt-4o-mini | Simple yes/no decisions |

### Model Recommendations by Hardware

| RAM | Embedding Model | Chat Model | Notes |
|-----|-----------------|------------|-------|
| 8GB | nomic-embed-text | llama3.2:3b | Minimum viable |
| 16GB | nomic-embed-text | mistral:7b | Good balance |
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

### Provider Unavailable

```python
# Ollama not running
if not await ollama_provider.health_check():
    if user_has_cloud_fallback:
        return await cloud_provider.embed(text)
    else:
        raise ProviderUnavailableError(
            "Ollama is not running. Start Ollama or configure a cloud provider."
        )
```

### Model Not Found

```python
# Requested model not downloaded
if model not in await ollama_provider.list_models():
    # Offer to download
    await ollama_provider.pull_model(model, progress_callback)
```

### Rate Limiting (Cloud)

```python
# Cloud API rate limited
try:
    return await cloud_provider.embed(text)
except RateLimitError:
    await asyncio.sleep(backoff)
    return await cloud_provider.embed(text)  # Retry
```

## Cost Estimation (Cloud)

When using cloud providers, track and display costs:

| Operation | Typical Cost | Per 100 Items |
|-----------|--------------|---------------|
| Embed (text-embedding-3-small) | $0.00002/1K tokens | ~$0.02 |
| Extract (gpt-4o-mini) | $0.00015/1K tokens | ~$0.15 |
| Chat (gpt-4o-mini) | $0.00015/1K tokens | ~$0.05/query |

Display in UI: "Estimated cost this month: $0.12"

## Testing AI Features

### Mock Provider

For tests, use a mock provider that returns deterministic results:

```python
class MockAIProvider(AIProvider):
    async def embed(self, text: str) -> list[float]:
        # Return consistent embedding based on text hash
        return [hash(text) % 100 / 100.0] * 384

    async def chat(self, messages: list, system: str) -> str:
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
