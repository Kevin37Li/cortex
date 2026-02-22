"""FastAPI route modules for the API layer."""

from src.api.routes.health import router as health_router
from src.api.routes.items import router as items_router
from src.api.routes.processing import router as processing_router
from src.api.routes.search import router as search_router
from src.api.routes.ws import router as ws_router

__all__ = [
    "health_router",
    "items_router",
    "processing_router",
    "search_router",
    "ws_router",
]
