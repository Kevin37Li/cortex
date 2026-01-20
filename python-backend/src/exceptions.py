"""Custom exception hierarchy for Cortex backend."""


class CortexError(Exception):
    """Base exception for all Cortex-related errors."""

    pass


class ItemNotFoundError(CortexError):
    """Raised when an item is not found in the database.

    Used by repository update() methods when the item doesn't exist.
    """

    def __init__(self, item_id: str) -> None:
        self.item_id = item_id
        super().__init__(f"Item not found: {item_id}")


class ChunkNotFoundError(CortexError):
    """Raised when a chunk is not found in the database."""

    def __init__(self, chunk_id: str) -> None:
        self.chunk_id = chunk_id
        super().__init__(f"Chunk not found: {chunk_id}")


class DatabaseError(CortexError):
    """Raised for database-related errors."""

    pass
