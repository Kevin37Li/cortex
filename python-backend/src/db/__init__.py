"""Database layer for Cortex backend."""

from .database import (
    EMBEDDING_DIMENSION,
    db_connection,
    init_database,
    verify_database,
)

__all__ = [
    "EMBEDDING_DIMENSION",
    "db_connection",
    "init_database",
    "verify_database",
]
