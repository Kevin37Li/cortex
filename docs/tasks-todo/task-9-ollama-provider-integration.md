# Task: Implement Ollama Provider Integration with Health Check

## Summary
Create Ollama provider service for local AI model access and health checking.

## Acceptance Criteria
- [ ] `OllamaProvider` service class with:
  - Connection configuration (host, port, default: localhost:11434)
  - `check_health() -> OllamaStatus` - verify Ollama is running
  - `list_models() -> list[str]` - get available models
  - `is_model_available(model: str) -> bool`
- [ ] `GET /api/health/ollama` endpoint returning:
  ```json
  {
    "status": "available",
    "version": "0.1.40",
    "models": ["llama3.2", "nomic-embed-text"]
  }
  ```
- [ ] Graceful handling when Ollama not running (status: "unavailable")
- [ ] Configuration in settings for Ollama URL
- [ ] Unit tests with mocked Ollama responses

## Dependencies
- Task 1: Python backend project structure
- Task 7: Health check endpoint (pattern reference)

## Technical Notes
- Use httpx for async HTTP client
- Ollama API: `GET /api/tags` for model list, `GET /` for health
- Don't fail app startup if Ollama unavailable
- This prepares for Phase 2 embedding/chat features

## Phase
Phase 1: Foundation
