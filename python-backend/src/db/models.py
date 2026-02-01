"""Pydantic models for database entities."""

from datetime import datetime

from pydantic import BaseModel, Field

# Content processing models


class ParsedContent(BaseModel):
    """Result of parsing raw content."""

    text: str  # Clean extracted text
    title: str | None = None  # Extracted title (HTML) or None
    word_count: int
    language: str | None = (
        None  # Always None for MVP; reserved for future language detection
    )


class ChunkResult(BaseModel):
    """A single chunk produced by the chunking service."""

    content: str
    chunk_index: int
    token_count: int


class ExtractedMetadata(BaseModel):
    """Metadata extracted from content via LLM."""

    summary: str = ""  # 2-3 sentence summary (default empty for partial results)
    concepts: list[str] = Field(default_factory=list)  # Key topics/concepts (3-7 items)
    entities: list[str] = Field(
        default_factory=list
    )  # Named entities: people, orgs, places (0-10 items)


# Item models


class ItemCreate(BaseModel):
    """Input model for creating an item."""

    title: str
    content: str
    content_type: str = Field(description="Type of content: 'webpage', 'note', 'file'")
    source_url: str | None = None
    metadata: dict | None = None


class ItemUpdate(BaseModel):
    """Input model for updating an item. All fields optional."""

    title: str | None = None
    content: str | None = None
    source_url: str | None = None
    metadata: dict | None = None


class Item(BaseModel):
    """Output model representing a stored item."""

    id: str
    title: str
    content: str
    content_type: str
    source_url: str | None
    created_at: datetime
    updated_at: datetime
    processing_status: str = Field(
        description="Status: 'pending', 'processing', 'completed', 'failed'"
    )
    metadata: dict | None

    model_config = {"from_attributes": True}


# Chunk models


class ChunkCreate(BaseModel):
    """Input model for creating a chunk."""

    item_id: str
    chunk_index: int
    content: str
    token_count: int | None = None


class Chunk(BaseModel):
    """Output model representing a stored chunk."""

    id: str
    item_id: str
    chunk_index: int
    content: str
    token_count: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


# Response models


class ItemListResponse(BaseModel):
    """Paginated response for listing items."""

    items: list[Item]
    total: int
    offset: int
    limit: int


# Health check models


class ComponentCheck(BaseModel):
    """Health check result for a single component."""

    status: str  # "healthy" | "unhealthy"
    latency_ms: int | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str  # "healthy" | "degraded" | "unhealthy"
    version: str
    timestamp: datetime
    checks: dict[str, ComponentCheck]
