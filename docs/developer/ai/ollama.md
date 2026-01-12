# Ollama Integration

Local AI inference using Ollama.

## Overview

Ollama is the default AI provider for Cortex, enabling fully local inference:
- No data leaves the device
- Works offline
- No API costs
- User controls model selection

## Architecture

```
┌─────────────────────────────────────────┐
│              Cortex App                  │
│  ┌─────────────────────────────────┐    │
│  │       OllamaProvider            │    │
│  │  • Health checks                │    │
│  │  • Model management             │    │
│  │  • Request batching             │    │
│  └──────────────┬──────────────────┘    │
└─────────────────┼───────────────────────┘
                  │ HTTP (localhost:11434)
┌─────────────────▼───────────────────────┐
│              Ollama Server               │
│  • Model loading/unloading              │
│  • GPU acceleration (if available)      │
│  • Concurrent request handling          │
└─────────────────────────────────────────┘
```

## Setup Flow

### Detection

On app startup, check if Ollama is available:

```python
async def check_ollama_status() -> OllamaStatus:
    try:
        response = await httpx.get("http://localhost:11434/api/tags")
        models = response.json().get("models", [])
        return OllamaStatus(
            running=True,
            models=[m["name"] for m in models],
            has_embedding_model="nomic-embed-text" in models,
            has_chat_model=any(m in models for m in CHAT_MODELS)
        )
    except httpx.ConnectError:
        return OllamaStatus(running=False)
```

### Guided Setup

If Ollama is not running or models are missing:

```
┌─────────────────────────────────────────────────────────────┐
│  Ollama Setup                                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ⚠️ Ollama is not running                                   │
│                                                              │
│  Cortex uses Ollama for local AI processing.                │
│                                                              │
│  1. Download Ollama from https://ollama.ai                  │
│  2. Install and run Ollama                                  │
│  3. Return here to continue setup                           │
│                                                              │
│  [Open Ollama Website]     [Check Again]                    │
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  Don't want to install Ollama?                              │
│  [Use Cloud AI Instead]                                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Model Downloads

Required models for Cortex:

| Model | Size | Purpose | Required |
|-------|------|---------|----------|
| nomic-embed-text | 274MB | Embeddings | Yes |
| llama3.2:3b | 2GB | Chat, extraction | Yes (or alternative) |
| mistral:7b | 4GB | Better chat quality | Optional |

Download UI:

```
┌─────────────────────────────────────────────────────────────┐
│  Download Required Models                                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  nomic-embed-text (274 MB)                                  │
│  ████████████████████████████████████████ 100%              │
│  ✓ Downloaded                                               │
│                                                              │
│  llama3.2:3b (2.0 GB)                                       │
│  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 30%              │
│  Downloading... 600 MB / 2.0 GB                             │
│                                                              │
│  [Cancel]                                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## API Usage

### Embeddings

```python
async def embed(self, text: str) -> list[float]:
    response = await self.client.post(
        "http://localhost:11434/api/embeddings",
        json={
            "model": self.embedding_model,
            "prompt": text
        }
    )
    return response.json()["embedding"]

async def embed_batch(self, texts: list[str]) -> list[list[float]]:
    # Ollama doesn't have native batching, so we parallelize
    tasks = [self.embed(text) for text in texts]
    return await asyncio.gather(*tasks)
```

### Chat Completion

```python
async def chat(
    self,
    messages: list[dict],
    system: str | None = None
) -> str:
    response = await self.client.post(
        "http://localhost:11434/api/chat",
        json={
            "model": self.chat_model,
            "messages": messages,
            "system": system,
            "stream": False
        }
    )
    return response.json()["message"]["content"]

async def stream_chat(
    self,
    messages: list[dict],
    system: str | None = None
) -> AsyncIterator[str]:
    async with self.client.stream(
        "POST",
        "http://localhost:11434/api/chat",
        json={
            "model": self.chat_model,
            "messages": messages,
            "system": system,
            "stream": True
        }
    ) as response:
        async for line in response.aiter_lines():
            data = json.loads(line)
            if content := data.get("message", {}).get("content"):
                yield content
```

## Model Management

### Listing Models

```python
async def list_models(self) -> list[str]:
    response = await self.client.get("http://localhost:11434/api/tags")
    return [m["name"] for m in response.json().get("models", [])]
```

### Pulling Models

```python
async def pull_model(
    self,
    model: str,
    progress_callback: Callable[[float], None] | None = None
) -> None:
    async with self.client.stream(
        "POST",
        "http://localhost:11434/api/pull",
        json={"model": model}
    ) as response:
        async for line in response.aiter_lines():
            data = json.loads(line)
            if "completed" in data and "total" in data:
                progress = data["completed"] / data["total"]
                if progress_callback:
                    progress_callback(progress)
```

### Model Selection UI

```
┌─────────────────────────────────────────────────────────────┐
│  Local AI Models                                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Embedding Model                                             │
│  [nomic-embed-text                              ▼]          │
│  384 dimensions • Required for search                       │
│                                                              │
│  Chat Model                                                  │
│  [llama3.2:3b                                   ▼]          │
│  Fast responses • Good for most tasks                       │
│                                                              │
│  Available models:                                          │
│  • nomic-embed-text (274 MB) ✓                              │
│  • llama3.2:3b (2 GB) ✓                                     │
│  • mistral:7b (4 GB) ✓                                      │
│                                                              │
│  [Download More Models]                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Performance Considerations

### Concurrent Requests

Ollama handles concurrent requests, but performance depends on:
- Available VRAM (GPU) or RAM (CPU)
- Model size
- Request complexity

Recommendation: Limit concurrent embedding requests to 4-8 for stability.

### Model Loading

First request after startup loads the model into memory (~5-15 seconds for 7B models). Subsequent requests are fast.

To keep models loaded:
```python
# Periodic keepalive request
async def keepalive(self):
    await self.client.post(
        "http://localhost:11434/api/generate",
        json={"model": self.chat_model, "prompt": "", "keep_alive": "10m"}
    )
```

### GPU vs CPU

- **With GPU**: 10-50 tokens/second for 7B models
- **CPU only**: 2-10 tokens/second for 7B models

The app should detect GPU availability and adjust expectations in the UI.

## Error Handling

### Ollama Not Running

```python
class OllamaNotRunningError(Exception):
    """Raised when Ollama server is not accessible."""
    pass

# In provider
async def embed(self, text: str) -> list[float]:
    try:
        response = await self.client.post(...)
    except httpx.ConnectError:
        raise OllamaNotRunningError(
            "Cannot connect to Ollama. Is it running?"
        )
```

### Model Not Found

```python
class ModelNotFoundError(Exception):
    """Raised when requested model is not available."""
    pass

# Check before operations
if model not in await self.list_models():
    raise ModelNotFoundError(f"Model {model} not found. Run: ollama pull {model}")
```

### Out of Memory

Large models may fail on limited hardware:

```python
# Detect OOM from Ollama response
if "out of memory" in response.text.lower():
    raise OutOfMemoryError(
        "Model too large for available memory. Try a smaller model."
    )
```

## Risks & Mitigations

### Risk: Ollama Dependency

**Concern**: Requiring users to install Ollama adds friction.

**Mitigations**:
- Clear setup wizard with step-by-step instructions
- App detects missing Ollama and guides user
- Cloud fallback available for users who don't want local setup
- Future: Consider bundling llama.cpp directly

### Risk: Local LLM Quality

**Concern**: Local models may produce poor extractions compared to GPT-4/Claude.

**Mitigations**:
- Validation loops in workflows catch obvious failures
- Prompts optimized for smaller models (simpler, more explicit)
- Users with powerful hardware can use larger models (70B)
- Hybrid mode lets users use cloud for complex queries
- Clear guidance on which tasks benefit from better models

## Related Documentation

- [AI Overview](./overview.md) - Provider architecture
- [Cloud Providers](./cloud-providers.md) - Alternative to local AI
- [Embeddings](./embeddings.md) - Vector embedding details
