"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import (
    health_router,
    items_router,
    processing_router,
    search_router,
    ws_router,
)
from src.api.websocket import ProcessingConnectionManager
from src.config import settings
from src.db import init_database, verify_database
from src.exceptions import (
    AIProviderError,
    DatabaseError,
    ItemNotFoundError,
    ProcessingError,
    SearchError,
)
from src.services import ProcessingQueue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup
    logger.info("Starting Cortex backend...")
    await init_database()
    ws_manager = ProcessingConnectionManager()
    queue = ProcessingQueue()
    unsubscribe_processing_updates = queue.subscribe_processing_updates(
        ws_manager.broadcast,
    )

    app.state.processing_queue = queue
    app.state.processing_ws_manager = ws_manager
    app.state.processing_ws_unsubscribe = unsubscribe_processing_updates
    await queue.start()
    yield
    # Shutdown: drain workers first so terminal events reach subscribers
    logger.info("Shutting down Cortex backend...")
    await queue.stop()
    unsubscribe_processing_updates()
    await ws_manager.shutdown()


app = FastAPI(title="Cortex Backend", lifespan=lifespan)


# Exception handlers
@app.exception_handler(ItemNotFoundError)
async def item_not_found_handler(request: Request, exc: ItemNotFoundError):
    """Handle ItemNotFoundError with 404 response."""
    return JSONResponse(
        status_code=404,
        content={"error": exc.error_code, "message": str(exc)},
    )


@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    """Handle DatabaseError with 500 response."""
    return JSONResponse(
        status_code=500,
        content={"error": exc.error_code, "message": "Internal database error"},
    )


@app.exception_handler(AIProviderError)
async def ai_provider_error_handler(request: Request, exc: AIProviderError):
    """Handle AIProviderError with 503 response."""
    return JSONResponse(
        status_code=503,
        content={"error": exc.error_code, "message": str(exc)},
    )


@app.exception_handler(ProcessingError)
async def processing_error_handler(request: Request, exc: ProcessingError):
    """Handle ProcessingError with 500 response."""
    return JSONResponse(
        status_code=500,
        content={"error": exc.error_code, "message": str(exc)},
    )


@app.exception_handler(SearchError)
async def search_error_handler(request: Request, exc: SearchError):
    """Handle SearchError with 500 response."""
    return JSONResponse(
        status_code=500,
        content={"error": exc.error_code, "message": str(exc)},
    )


# CORS for Tauri webview
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "tauri://localhost",
        "http://localhost",
        "http://localhost:1420",
        "http://127.0.0.1",
        "http://127.0.0.1:1420",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router, prefix="/api")
app.include_router(items_router, prefix="/api")
app.include_router(processing_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(ws_router, prefix="/api")


@app.get("/api/db/status")
async def database_status():
    """Database status endpoint - returns database info and statistics."""
    try:
        return await verify_database()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
