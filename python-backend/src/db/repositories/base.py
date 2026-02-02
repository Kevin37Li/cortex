"""Base repository with generic CRUD operations."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

import aiosqlite
from pydantic import BaseModel

# Type variables for generic repository
T = TypeVar("T", bound=BaseModel)  # Output model
CreateT = TypeVar("CreateT", bound=BaseModel)  # Create input model
UpdateT = TypeVar("UpdateT", bound=BaseModel)  # Update input model


class BaseRepository(ABC, Generic[T, CreateT, UpdateT]):
    """Abstract base repository defining common CRUD operations.

    This provides a generic interface for data access. Concrete implementations
    must define the table name, model type, and how to map between database
    rows and Pydantic models.

    Repositories are stateless - database connections are passed via method
    parameters. This allows callers to control transaction boundaries and
    commit timing.

    Type Parameters:
        T: The output Pydantic model type
        CreateT: The input model for create operations
        UpdateT: The input model for update operations

    Exception Handling Strategy:
        - get() returns None if not found (caller decides to raise)
        - update() raises ItemNotFoundError if item doesn't exist
        - delete() returns False if item doesn't exist

    Transaction Strategy:
        - Methods do NOT commit - caller is responsible for committing
        - This allows atomic transactions across multiple operations
    """

    @property
    @abstractmethod
    def table_name(self) -> str:
        """Return the database table name."""
        ...

    @abstractmethod
    async def create(self, db: aiosqlite.Connection, data: CreateT) -> T:
        """Create a new record and return it.

        UUID is generated internally using uuid4().
        Does NOT commit - caller is responsible for committing.

        Args:
            db: Database connection
            data: The input data for the new record

        Returns:
            The created record with all fields populated
        """
        ...

    @abstractmethod
    async def get(self, db: aiosqlite.Connection, id: str) -> T | None:
        """Get a record by ID.

        Args:
            db: Database connection
            id: The record's unique identifier

        Returns:
            The record if found, None otherwise
        """
        ...

    @abstractmethod
    async def list(
        self, db: aiosqlite.Connection, offset: int = 0, limit: int = 20
    ) -> list[T]:
        """List records with pagination.

        Args:
            db: Database connection
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of records
        """
        ...

    @abstractmethod
    async def update(self, db: aiosqlite.Connection, id: str, data: UpdateT) -> T:
        """Update a record.

        Does NOT commit - caller is responsible for committing.

        Args:
            db: Database connection
            id: The record's unique identifier
            data: The fields to update (None fields are skipped)

        Returns:
            The updated record

        Raises:
            ItemNotFoundError: If the record doesn't exist
        """
        ...

    @abstractmethod
    async def delete(self, db: aiosqlite.Connection, id: str) -> bool:
        """Delete a record.

        Does NOT commit - caller is responsible for committing.

        Args:
            db: Database connection
            id: The record's unique identifier

        Returns:
            True if deleted, False if record didn't exist
        """
        ...

    @abstractmethod
    async def count(self, db: aiosqlite.Connection) -> int:
        """Count total records in the table.

        Args:
            db: Database connection

        Returns:
            Total number of records
        """
        ...
