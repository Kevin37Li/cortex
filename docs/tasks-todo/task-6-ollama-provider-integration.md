# Task: Implement Ollama Provider Integration

## Summary

Create a provider abstraction for Ollama that enables local AI inference for embeddings and chat, with health checking.

## Acceptance Criteria

- [ ] `OllamaProvider` class with embedding and chat methods
- [ ] `GET /api/health/ollama` - Check Ollama availability and models
- [ ] Configurable Ollama base URL (default: `http://localhost:11434`)
- [ ] List available models
- [ ] Generate embeddings using nomic-embed-text (or similar)
- [ ] Graceful handling when Ollama is not running
- [ ] Timeout handling for long-running requests

## Dependencies

- Task 1: Python backend project structure
- Task 5: Health check endpoint

## Technical Notes

- Ollama API: `POST /api/embeddings`, `POST /api/generate`
- Use `httpx` for async HTTP client
- nomic-embed-text produces 768-dimension embeddings
- Ollama may not be running - handle gracefully

## Ollama API Reference

```python
# Generate embeddings
POST http://localhost:11434/api/embeddings
{
    "model": "nomic-embed-text",
    "prompt": "text to embed"
}
Response: { "embedding": [0.1, 0.2, ...] }

# List models
GET http://localhost:11434/api/tags
Response: { "models": [{"name": "nomic-embed-text", ...}] }
```

## Provider Interface

```python
class OllamaProvider:
    def __init__(self, base_url: str = "http://localhost:11434")

    async def is_available(self) -> bool
    async def list_models(self) -> list[ModelInfo]
    async def embed(self, text: str, model: str = "nomic-embed-text") -> list[float]
    async def embed_batch(self, texts: list[str], model: str) -> list[list[float]]
```

## Files to Create

- `python-backend/src/providers/base.py` - Provider interface
- `python-backend/src/providers/ollama.py` - Ollama provider
- `python-backend/src/api/routes/health.py` - Add Ollama health check

## Verification

```bash
# Start Ollama first
ollama serve

# Check Ollama health
curl http://localhost:8742/api/health/ollama

# Response when Ollama is running:
{
    "status": "healthy",
    "base_url": "http://localhost:11434",
    "models": ["nomic-embed-text", "llama2", ...]
}

# Response when Ollama is not running:
{
    "status": "unavailable",
    "error": "Connection refused"
}
```
