"""Repository classes for data access."""

from .app_metadata import AppMetadataRepository
from .base import BaseRepository
from .chunks import ChunkRepository
from .items import ItemRepository

# Module-level singleton instances (stateless repos)
item_repo = ItemRepository()
chunk_repo = ChunkRepository()
metadata_repo = AppMetadataRepository()

__all__ = [
    # Classes
    "AppMetadataRepository",
    "BaseRepository",
    "ChunkRepository",
    "ItemRepository",
    # Singleton instances
    "item_repo",
    "chunk_repo",
    "metadata_repo",
]
