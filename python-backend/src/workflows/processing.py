"""LangGraph content processing workflow.

Orchestrates the full content processing pipeline:
classify → parse → chunk → extract_metadata → validate → persist → complete

Uses LangGraph StateGraph for:
- Typed state management
- Conditional routing (validation retry loop)
- Error handling with graceful degradation
"""

import functools
import logging
from typing import TypedDict

from langgraph.graph import END, StateGraph

from src.db.database import db_connection
from src.db.models import ChunkCreate, ChunkResult, ExtractedMetadata, ItemUpdate
from src.db.repositories import chunk_repo, item_repo
from src.providers import AIProvider, OllamaProvider
from src.services import (
    ChunkingService,
    ContentParser,
    EmbeddingService,
    MetadataExtractor,
)

logger = logging.getLogger(__name__)


# Maximum retry attempts for validation failures
MAX_RETRIES = 3


class ProcessingState(TypedDict, total=False):
    """State schema for the content processing workflow.

    Using total=False allows fields to be absent until their node runs.
    """

    # Required - set at entry
    item_id: str

    # Set by classify
    raw_content: str
    content_type: str  # 'webpage', 'note', 'file' (match schema values!)
    title: str
    source_url: str | None
    ai_provider: AIProvider

    # Set by parse
    parsed_text: str

    # Set by chunk
    chunk_results: list[ChunkResult]  # In-memory before persistence

    # Set by extract_metadata
    metadata: ExtractedMetadata

    # Set by persist
    chunks: list  # After persistence, with IDs (list[Chunk])
    embeddings_stored: bool

    # Control flow
    validation_passed: bool
    retry_count: int
    error: str | None
    error_step: str | None


def log_node_execution(node_name: str):
    """Decorator for logging workflow node execution.

    Logs entry, exit, and any exceptions that occur during node execution.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(state: ProcessingState) -> dict:
            item_id = state.get("item_id", "unknown")
            logger.info(f"Starting node: {node_name}", extra={"item_id": item_id})
            try:
                result = await func(state)
                logger.info(f"Completed node: {node_name}", extra={"item_id": item_id})
                return result
            except Exception as e:
                logger.error(
                    f"Failed node: {node_name}",
                    extra={"item_id": item_id, "error": str(e)},
                )
                raise

        return wrapper

    return decorator


@log_node_execution("classify")
async def classify_node(state: ProcessingState) -> dict:
    """Fetch item from DB, set processing status, determine content type.

    Creates the AI provider and stores it in state for downstream nodes.
    """
    try:
        item_id = state["item_id"]

        async with db_connection() as db:
            # Fetch item from database
            item = await item_repo.get(db, item_id)
            if item is None:
                return {"error": f"Item not found: {item_id}", "error_step": "classify"}

            # Update processing status to 'processing'
            await item_repo.update_status(db, item_id, "processing")
            await db.commit()

        # Create AI provider for downstream nodes
        provider = OllamaProvider()

        return {
            "raw_content": item.content,
            "content_type": item.content_type,
            "title": item.title,
            "source_url": item.source_url,
            "ai_provider": provider,
        }
    except Exception as e:
        return {"error": str(e), "error_step": "classify"}


@log_node_execution("parse")
async def parse_node(state: ProcessingState) -> dict:
    """Parse raw content using ContentParser based on content type."""
    try:
        parser = ContentParser()
        result = parser.parse(state["raw_content"], state["content_type"])

        # Use extracted title if better than existing
        new_title = result.title if result.title else state.get("title", "")

        return {"parsed_text": result.text, "title": new_title}
    except Exception as e:
        return {"error": str(e), "error_step": "parse"}


@log_node_execution("chunk")
async def chunk_node(state: ProcessingState) -> dict:
    """Split parsed text into semantic chunks."""
    try:
        chunker = ChunkingService()
        chunk_results = chunker.chunk_text(state["parsed_text"])

        return {"chunk_results": chunk_results}
    except Exception as e:
        return {"error": str(e), "error_step": "chunk"}


@log_node_execution("extract_metadata")
async def extract_metadata_node(state: ProcessingState) -> dict:
    """Extract summary, concepts, and entities using LLM."""
    try:
        provider = state["ai_provider"]
        extractor = MetadataExtractor(provider)

        metadata = await extractor.extract(
            text=state["parsed_text"],
            title=state.get("title"),
        )

        return {"metadata": metadata}
    except Exception as e:
        return {"error": str(e), "error_step": "extract_metadata"}


@log_node_execution("validate")
async def validate_node(state: ProcessingState) -> dict:
    """Validate that chunks and metadata were successfully created."""
    try:
        chunk_results = state.get("chunk_results", [])
        metadata = state.get("metadata")

        # Check that chunks were created
        if not chunk_results:
            retry_count = state.get("retry_count", 0) + 1
            logger.warning(
                f"Validation failed: no chunks created (retry {retry_count}/{MAX_RETRIES})"
            )
            # Set error if max retries exceeded
            if retry_count >= MAX_RETRIES:
                return {
                    "validation_passed": False,
                    "retry_count": retry_count,
                    "error": f"Validation failed after {MAX_RETRIES} retries: no chunks created",
                    "error_step": "validate",
                }
            return {"validation_passed": False, "retry_count": retry_count}

        # Check that metadata has required fields (summary and concepts)
        if metadata is None or not metadata.summary or not metadata.concepts:
            retry_count = state.get("retry_count", 0) + 1
            logger.warning(
                f"Validation failed: missing or incomplete metadata (retry {retry_count}/{MAX_RETRIES})"
            )
            # Set error if max retries exceeded
            if retry_count >= MAX_RETRIES:
                return {
                    "validation_passed": False,
                    "retry_count": retry_count,
                    "error": f"Validation failed after {MAX_RETRIES} retries: missing or incomplete metadata",
                    "error_step": "validate",
                }
            return {"validation_passed": False, "retry_count": retry_count}

        logger.info(
            f"Validation passed: {len(chunk_results)} chunks, "
            f"{len(metadata.concepts)} concepts"
        )
        return {"validation_passed": True}
    except Exception as e:
        return {"error": str(e), "error_step": "validate"}


@log_node_execution("persist")
async def persist_node(state: ProcessingState) -> dict:
    """Persist chunks, embeddings, and metadata to database.

    Only called after validation passes to avoid orphaned data on retries.
    Uses a single atomic commit at the end to prevent orphan data.
    """
    try:
        item_id = state["item_id"]
        chunk_results = state["chunk_results"]
        metadata = state["metadata"]
        provider = state["ai_provider"]

        async with db_connection() as db:
            # Convert ChunkResult list to ChunkCreate models
            chunk_creates = [
                ChunkCreate(
                    item_id=item_id,
                    chunk_index=cr.chunk_index,
                    content=cr.content,
                    token_count=cr.token_count,
                )
                for cr in chunk_results
            ]

            # Persist chunks (no commit yet)
            created_chunks = await chunk_repo.create_many(db, chunk_creates)
            logger.info(f"Persisted {len(created_chunks)} chunks for item {item_id}")

            # Generate and store embeddings (no commit - service updated)
            embedding_service = EmbeddingService(provider=provider)
            await embedding_service.embed_chunks(db, created_chunks)
            logger.info(f"Stored embeddings for {len(created_chunks)} chunks")

            # Merge extracted metadata into item's existing metadata
            item = await item_repo.get(db, item_id)
            existing_metadata = item.metadata or {} if item else {}

            # Add extracted metadata fields
            existing_metadata["summary"] = metadata.summary
            existing_metadata["concepts"] = metadata.concepts
            existing_metadata["entities"] = metadata.entities

            # Update title if we extracted a better one
            update_data = ItemUpdate(
                title=state.get("title"),
                metadata=existing_metadata,
            )
            await item_repo.update(db, item_id, update_data)

            # Single atomic commit - all-or-nothing
            await db.commit()

        return {"chunks": created_chunks, "embeddings_stored": True}
    except Exception as e:
        return {"error": str(e), "error_step": "persist"}


@log_node_execution("complete")
async def complete_node(state: ProcessingState) -> dict:
    """Mark item processing as completed."""
    try:
        item_id = state["item_id"]

        async with db_connection() as db:
            await item_repo.update_status(db, item_id, "completed")
            await db.commit()

        logger.info(f"Processing completed for item {item_id}")
        return {}
    except Exception as e:
        return {"error": str(e), "error_step": "complete"}


@log_node_execution("handle_error")
async def handle_error_node(state: ProcessingState) -> dict:
    """Handle processing errors by updating item status and metadata."""
    item_id = state.get("item_id")
    error = state.get("error", "Unknown error")
    error_step = state.get("error_step", "unknown")

    logger.error(
        f"Processing failed for item {item_id}: {error} (step: {error_step})",
        extra={"item_id": item_id, "error": error, "error_step": error_step},
    )

    if not item_id:
        logger.error("Cannot update status: item_id not set")
        return {}

    try:
        async with db_connection() as db:
            # Update processing status to 'failed'
            await item_repo.update_status(db, item_id, "failed")

            # Merge error info into item metadata (preserve existing)
            item = await item_repo.get(db, item_id)
            existing_metadata = item.metadata or {} if item else {}
            existing_metadata["processing_error"] = error
            existing_metadata["error_step"] = error_step

            await item_repo.update(db, item_id, ItemUpdate(metadata=existing_metadata))
            await db.commit()

    except Exception as e:
        logger.exception(f"Failed to update error status: {e}")

    return {}


def route_or_error(next_node: str):
    """Create a router that routes to next_node or handle_error if error is set."""

    def router(state: ProcessingState) -> str:
        if state.get("error"):
            return "handle_error"
        return next_node

    return router


def route_after_validation(state: ProcessingState) -> str:
    """Route based on validation result.

    - If error: route to handle_error
    - If validation passed: route to persist
    - If retry count < MAX_RETRIES: retry chunking
    - Otherwise: route to handle_error (max retries exceeded)
    """
    if state.get("error"):
        return "handle_error"
    if state.get("validation_passed"):
        return "persist"
    if state.get("retry_count", 0) < MAX_RETRIES:
        return "retry"
    # Max retries exceeded
    return "handle_error"


def build_processing_graph() -> StateGraph:
    """Build and compile the content processing workflow graph."""
    builder = StateGraph(ProcessingState)

    # Add nodes
    builder.add_node("classify", classify_node)
    builder.add_node("parse", parse_node)
    builder.add_node("chunk", chunk_node)
    builder.add_node("extract_metadata", extract_metadata_node)
    builder.add_node("validate", validate_node)
    builder.add_node("persist", persist_node)
    builder.add_node("complete", complete_node)
    builder.add_node("handle_error", handle_error_node)

    # Set entry point
    builder.set_entry_point("classify")

    # Add edges with error routing
    builder.add_conditional_edges(
        "classify",
        route_or_error("parse"),
        {"parse": "parse", "handle_error": "handle_error"},
    )
    builder.add_conditional_edges(
        "parse",
        route_or_error("chunk"),
        {"chunk": "chunk", "handle_error": "handle_error"},
    )
    builder.add_conditional_edges(
        "chunk",
        route_or_error("extract_metadata"),
        {"extract_metadata": "extract_metadata", "handle_error": "handle_error"},
    )
    builder.add_conditional_edges(
        "extract_metadata",
        route_or_error("validate"),
        {"validate": "validate", "handle_error": "handle_error"},
    )

    # Validate routes to persist, retry, or fail
    builder.add_conditional_edges(
        "validate",
        route_after_validation,
        {"persist": "persist", "retry": "chunk", "handle_error": "handle_error"},
    )

    builder.add_conditional_edges(
        "persist",
        route_or_error("complete"),
        {"complete": "complete", "handle_error": "handle_error"},
    )
    builder.add_conditional_edges(
        "complete",
        route_or_error(END),
        {END: END, "handle_error": "handle_error"},
    )
    builder.add_edge("handle_error", END)

    return builder.compile()


# Compile the graph once at module load
graph = build_processing_graph()


async def process_item(item_id: str) -> ProcessingState:
    """Process an item through the full content processing pipeline.

    This is the main entry point for processing a saved item.

    Args:
        item_id: The ID of the item to process.

    Returns:
        The final ProcessingState containing results or error information.
    """
    initial_state: ProcessingState = {"item_id": item_id}
    result = await graph.ainvoke(initial_state)
    return result
