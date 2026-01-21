"""Health check endpoint for Cortex backend."""

import time
from datetime import UTC, datetime

import aiosqlite
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from ..config import get_app_version
from ..db.models import ComponentCheck, HealthResponse
from .deps import get_db_connection

router = APIRouter(tags=["health"])


async def _check_database(db: aiosqlite.Connection) -> ComponentCheck:
    """Check database connectivity and measure latency."""
    start = time.perf_counter()
    try:
        await db.execute("SELECT 1")
        latency_ms = int((time.perf_counter() - start) * 1000)
        return ComponentCheck(status="healthy", latency_ms=latency_ms)
    except Exception as e:
        return ComponentCheck(status="unhealthy", error=str(e))


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy"},
    },
)
async def health_check(
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> JSONResponse:
    """Health check endpoint with database connectivity verification.

    Returns overall health status, version, timestamp, and component checks.
    """
    checks: dict[str, ComponentCheck] = {}

    # Check database
    checks["database"] = await _check_database(db)

    # Determine overall status
    all_healthy = all(check.status == "healthy" for check in checks.values())
    any_healthy = any(check.status == "healthy" for check in checks.values())

    if all_healthy:
        overall_status = "healthy"
    elif any_healthy:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    response = HealthResponse(
        status=overall_status,
        version=get_app_version(),
        timestamp=datetime.now(UTC),
        checks=checks,
    )

    status_code = (
        status.HTTP_200_OK
        if overall_status == "healthy"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(mode="json"),
    )
