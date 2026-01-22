"""Pydantic models for AI providers."""

from datetime import datetime

from pydantic import BaseModel


class ModelInfo(BaseModel):
    """Information about an available AI model."""

    name: str
    size: int | None = None
    modified_at: datetime | None = None
    digest: str | None = None


class OllamaHealthResponse(BaseModel):
    """Response model for Ollama health check endpoint."""

    status: str  # "healthy" | "unavailable"
    base_url: str
    models: list[str] | None = None
    error: str | None = None
    latency_ms: float | None = None
