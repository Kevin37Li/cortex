"""WebSocket infrastructure for the API layer."""

from src.api.websocket.manager import ClientConnection, ProcessingConnectionManager

__all__ = ["ClientConnection", "ProcessingConnectionManager"]
