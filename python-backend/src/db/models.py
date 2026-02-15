"""Pydantic models for database entities."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

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


# Enums


class ContentType(StrEnum):
    """Content type values for items."""

    WEBPAGE = "webpage"
    NOTE = "note"
    FILE = "file"


class ProcessingStatus(StrEnum):
    """Status values for the item processing lifecycle."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStep(StrEnum):
    """Step values emitted as processing updates."""

    CLASSIFY = "classify"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"


class ItemMetadata(BaseModel):
    """Structured item metadata shared between backend and frontend contracts."""

    summary: str | None = None
    concepts: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    processing_error: str | None = None
    error_step: ProcessingStep | None = None

    # Enforce a strict metadata contract for early-stage development.
    model_config = {"extra": "forbid"}


def normalize_item_metadata(metadata: object) -> ItemMetadata | None:
    """Normalize metadata payloads from DB/API into ItemMetadata."""

    if metadata is None:
        return None

    if isinstance(metadata, ItemMetadata):
        return metadata

    if not isinstance(metadata, dict):
        return None

    return ItemMetadata.model_validate(metadata)


# Item models


class ItemCreate(BaseModel):
    """Input model for creating an item."""

    title: str
    content: str
    content_type: ContentType
    source_url: str | None = None
    metadata: ItemMetadata | None = None


class ItemUpdate(BaseModel):
    """Input model for updating an item. All fields optional."""

    title: str | None = None
    content: str | None = None
    source_url: str | None = None
    metadata: ItemMetadata | None = None


class Item(BaseModel):
    """Output model representing a stored item."""

    id: str
    title: str
    content: str
    content_type: ContentType
    source_url: str | None
    created_at: datetime
    updated_at: datetime
    processing_status: ProcessingStatus
    metadata: ItemMetadata | None

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


# Processing queue models


class ProcessingUpdate(BaseModel):
    """Step-level update emitted while an item is processed."""

    type: Literal["processing_update"] = "processing_update"
    item_id: str
    status: ProcessingStatus
    step: ProcessingStep
    progress: float = Field(ge=0.0, le=1.0)
    message: str


class QueueStatus(BaseModel):
    """Current state of the processing queue."""

    pending_count: int
    processing_count: int
    processing_items: list[str]  # Item IDs currently being processed
    failed_count: int
    completed_count: int
    total_processed: int  # Lifetime total since startup


class RetryFailedResult(BaseModel):
    """Rich result from ProcessingQueue.retry_failed() for deterministic HTTP mapping."""

    requested_item_id: str | None = None
    retried_count: int = 0
    outcome: Literal["retried", "already_queued", "not_in_queue"] = "retried"


class RetryRequest(BaseModel):
    """Request body for POST /api/processing/retry."""

    item_id: str | None = None  # None = retry all failed


class RetryResponse(BaseModel):
    """Response body for POST /api/processing/retry."""

    retried_count: int
    outcome: Literal["retried", "already_queued", "not_in_queue"]
