"""Repository classes for data access."""

from src.db.repositories.app_metadata import AppMetadataRepository
from src.db.repositories.base import BaseRepository
from src.db.repositories.chunks import ChunkRepository
from src.db.repositories.items import ItemRepository

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
