"""WebSocket infrastructure for the API layer."""

from .manager import ClientConnection, ProcessingConnectionManager

__all__ = ["ClientConnection", "ProcessingConnectionManager"]
