"""Search API endpoints."""

import logging

from fastapi import APIRouter

from src.db import SearchRequest, SearchResponse
from src.exceptions import SearchError
from src.workflows import search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


@router.post(
    "/",
    response_model=SearchResponse,
    status_code=200,
    responses={500: {"description": "Search execution failed"}},
)
async def search_items(request: SearchRequest) -> SearchResponse:
    """Execute a search query against the knowledge base.

    Supports three search modes:
    - **hybrid** (default): Combines vector similarity and full-text search via RRF
    - **vector**: Semantic similarity search only
    - **fts**: Full-text keyword search only
    """
    try:
        result = await search(
            query=request.query,
            search_type=request.search_type,
            limit=request.limit,
        )
    except SearchError:
        raise
    except Exception as exc:
        logger.exception("Unexpected error during search workflow")
        raise SearchError(
            str(exc),
            query=request.query,
            step="workflow",
        ) from exc

    if not isinstance(result, dict):
        logger.error(
            "Search workflow returned invalid state type",
            extra={"query": request.query, "state_type": type(result).__name__},
        )
        raise SearchError(
            "Search workflow returned invalid state",
            query=request.query,
            step="workflow",
        )

    error = result.get("error")
    if error is not None:
        logger.error(
            "Search workflow returned error state",
            extra={"query": request.query, "step": result.get("error_step")},
        )
        raise SearchError(
            str(error),
            query=request.query,
            step=result.get("error_step"),
        )

    final_results = result.get("final_results", [])

    return SearchResponse(
        results=final_results,
        total=len(final_results),
        query=request.query,
        search_type=request.search_type,
    )
