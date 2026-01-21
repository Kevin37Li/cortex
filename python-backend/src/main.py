"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.health import router as health_router
from .api.items import router as items_router
from .config import settings
from .db import init_database, verify_database
from .exceptions import DatabaseError, ItemNotFoundError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup
    logger.info("Starting Cortex backend...")
    await init_database()
    yield
    # Shutdown
    logger.info("Shutting down Cortex backend...")


app = FastAPI(title="Cortex Backend", lifespan=lifespan)


# Exception handlers
@app.exception_handler(ItemNotFoundError)
async def item_not_found_handler(request: Request, exc: ItemNotFoundError):
    """Handle ItemNotFoundError with 404 response."""
    return JSONResponse(
        status_code=404,
        content={"error": "item_not_found", "message": str(exc)},
    )


@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    """Handle DatabaseError with 500 response."""
    return JSONResponse(
        status_code=500,
        content={"error": "database_error", "message": "Internal database error"},
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
