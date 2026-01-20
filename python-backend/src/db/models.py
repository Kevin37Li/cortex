"""Pydantic models for database entities."""

from datetime import datetime

from pydantic import BaseModel, Field

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
