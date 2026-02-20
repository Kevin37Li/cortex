"""LangGraph search workflow for vector/FTS/hybrid retrieval."""

import logging
from typing import Any, TypedDict, cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.db import ChunkSearchResult, SearchResultItem, SearchType, db_connection
from src.providers import OllamaProvider
from src.services.embeddings import EmbeddingService
from src.services.search import SearchService, reciprocal_rank_fusion
from src.workflows.utils import log_node_execution, route_or_error

logger = logging.getLogger(__name__)


class SearchState(TypedDict, total=False):
    """State schema for the search workflow."""

    # Required input
    query: str
    search_type: SearchType
    limit: int

    # Intermediate results
    query_embedding: list[float]
    vector_results: list[ChunkSearchResult]
    fts_results: list[ChunkSearchResult]
    fused_results: list[ChunkSearchResult]

    # Final result
    final_results: list[SearchResultItem]

    # Error handling
    error: str | None
    error_step: str | None


# Nodes return partial dicts; SearchState has total=False so partials are valid.
NodeUpdate = SearchState


def _create_embedding_service() -> EmbeddingService:
    """Create an embedding service backed by the default provider."""
    return EmbeddingService(provider=OllamaProvider())


def _create_search_service() -> SearchService:
    """Create a search service with the default embedding dependency."""
    return SearchService(embedding_service=_create_embedding_service())


@log_node_execution("embed_query")
async def embed_query_node(state: SearchState) -> NodeUpdate:
    """Generate query embedding for vector-capable search modes."""
    try:
        async with db_connection() as db:
            embedding_service = _create_embedding_service()
            embedding = await embedding_service.embed_query(state["query"], db=db)
        return {"query_embedding": embedding}
    except Exception as e:
        return {"error": str(e), "error_step": "embed_query"}


@log_node_execution("vector_search")
async def vector_search_node(state: SearchState) -> NodeUpdate:
    """Execute vector search using a pre-computed embedding when available."""
    try:
        async with db_connection() as db:
            search_service = _create_search_service()
            results = await search_service.vector_search(
                state["query"],
                db=db,
                limit=state.get("limit", 20),
                query_embedding=state.get("query_embedding"),
            )
        return {"vector_results": results}
    except Exception as e:
        return {"error": str(e), "error_step": "vector_search"}


@log_node_execution("fts_search")
async def fts_search_node(state: SearchState) -> NodeUpdate:
    """Execute full-text search using the query text."""
    try:
        async with db_connection() as db:
            search_service = _create_search_service()
            results = await search_service.fts_search(
                state["query"],
                db=db,
                limit=state.get("limit", 20),
            )
        return {"fts_results": results}
    except Exception as e:
        return {"error": str(e), "error_step": "fts_search"}


@log_node_execution("fuse_results")
async def fuse_results_node(state: SearchState) -> NodeUpdate:
    """Fuse vector/FTS result lists and enforce the configured result limit."""
    try:
        limit = state.get("limit", 20)
        search_type = state.get("search_type", "hybrid")
        vector_results = state.get("vector_results", [])
        fts_results = state.get("fts_results", [])

        if search_type == "hybrid":
            fused = reciprocal_rank_fusion(vector_results, fts_results)[:limit]
        elif search_type == "vector":
            fused = vector_results[:limit]
        else:
            fused = fts_results[:limit]

        return {"fused_results": fused}
    except Exception as e:
        return {"error": str(e), "error_step": "fuse_results"}


@log_node_execution("enrich_results")
async def enrich_results_node(state: SearchState) -> NodeUpdate:
    """Attach item metadata to fused chunk hits."""
    try:
        async with db_connection() as db:
            results = await SearchService.enrich_results(
                state.get("fused_results", []),
                db=db,
            )
        return {"final_results": results}
    except Exception as e:
        return {"error": str(e), "error_step": "enrich_results"}


@log_node_execution("handle_error")
async def handle_error_node(state: SearchState) -> NodeUpdate:
    """Log workflow errors and keep existing error fields unchanged."""
    logger.error(
        f"Search failed at step '{state.get('error_step')}': {state.get('error')}",
        extra={"query": state.get("query")},
    )
    return {}


def route_after_entry(state: SearchState) -> str:
    """Choose initial node based on search type."""
    if state.get("error"):
        return "handle_error"

    if state.get("search_type", "hybrid") == "fts":
        return "fts_search"
    return "embed_query"


def route_after_vector(state: SearchState) -> str:
    """Route from vector stage to either FTS (hybrid) or fuse (vector-only)."""
    if state.get("error"):
        return "handle_error"

    if state.get("search_type", "hybrid") == "hybrid":
        return "fts_search"
    return "fuse_results"


def build_search_graph() -> CompiledStateGraph[
    SearchState, None, SearchState, SearchState
]:
    """Build and compile the search workflow graph."""
    builder = StateGraph(SearchState)

    builder.add_node("embed_query", cast(Any, embed_query_node))
    builder.add_node("vector_search", cast(Any, vector_search_node))
    builder.add_node("fts_search", cast(Any, fts_search_node))
    builder.add_node("fuse_results", cast(Any, fuse_results_node))
    builder.add_node("enrich_results", cast(Any, enrich_results_node))
    builder.add_node("handle_error", cast(Any, handle_error_node))

    builder.add_conditional_edges(
        START,
        route_after_entry,
        {
            "embed_query": "embed_query",
            "fts_search": "fts_search",
            "handle_error": "handle_error",
        },
    )
    builder.add_conditional_edges(
        "embed_query",
        route_or_error("vector_search"),
        {"vector_search": "vector_search", "handle_error": "handle_error"},
    )
    builder.add_conditional_edges(
        "vector_search",
        route_after_vector,
        {
            "fts_search": "fts_search",
            "fuse_results": "fuse_results",
            "handle_error": "handle_error",
        },
    )
    builder.add_conditional_edges(
        "fts_search",
        route_or_error("fuse_results"),
        {"fuse_results": "fuse_results", "handle_error": "handle_error"},
    )
    builder.add_conditional_edges(
        "fuse_results",
        route_or_error("enrich_results"),
        {"enrich_results": "enrich_results", "handle_error": "handle_error"},
    )
    builder.add_conditional_edges(
        "enrich_results",
        route_or_error(END),
        {END: END, "handle_error": "handle_error"},
    )
    builder.add_edge("handle_error", END)

    return cast(
        CompiledStateGraph[SearchState, None, SearchState, SearchState],
        builder.compile(),
    )


graph = build_search_graph()


async def search(
    query: str,
    search_type: SearchType = "hybrid",
    limit: int = 20,
) -> SearchState:
    """Execute search workflow and return final state."""
    initial_state: SearchState = {
        "query": query,
        "search_type": search_type,
        "limit": limit,
    }
    result = await graph.ainvoke(initial_state)
    return cast(SearchState, result)
