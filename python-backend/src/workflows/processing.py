"""LangGraph content processing workflow.

Orchestrates the full content processing pipeline:
classify → parse → chunk → extract_metadata → validate → persist → complete

Uses LangGraph StateGraph for:
- Typed state management
- Conditional routing (validation retry loop)
- Error handling with graceful degradation
"""

import logging
from collections.abc import Callable
from typing import Any, TypedDict, cast

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.db import (
    ChunkCreate,
    ChunkResult,
    ContentType,
    ExtractedMetadata,
    ItemUpdate,
    ProcessingStatus,
    ProcessingStep,
    ProcessingUpdate,
    db_connection,
    normalize_item_metadata,
)
from src.db.repositories import chunk_repo, item_repo
from src.providers import AIProvider, OllamaProvider
from src.services import (
    ChunkingService,
    ContentParser,
    EmbeddingService,
    MetadataExtractor,
)
from src.workflows.utils import log_node_execution, route_or_error

logger = logging.getLogger(__name__)


# Maximum retry attempts for validation failures
MAX_RETRIES = 3
ProcessingUpdateEmitter = Callable[[ProcessingUpdate], None]

STEP_PROGRESS: dict[ProcessingStep, float] = {
    ProcessingStep.CLASSIFY: 0.05,
    ProcessingStep.PARSING: 0.20,
    ProcessingStep.CHUNKING: 0.40,
    ProcessingStep.EXTRACTING: 0.65,
    ProcessingStep.VALIDATING: 0.85,
    ProcessingStep.STORING: 0.95,
    ProcessingStep.COMPLETED: 1.0,
    ProcessingStep.FAILED: 1.0,
}

STEP_MESSAGES: dict[ProcessingStep, str] = {
    ProcessingStep.CLASSIFY: "Classifying content",
    ProcessingStep.PARSING: "Parsing content",
    ProcessingStep.CHUNKING: "Chunking content",
    ProcessingStep.EXTRACTING: "Extracting summary and concepts",
    ProcessingStep.VALIDATING: "Validating extracted content",
    ProcessingStep.STORING: "Persisting chunks and metadata",
    ProcessingStep.COMPLETED: "Processing completed",
    ProcessingStep.FAILED: "Processing failed",
}


class ProcessingState(TypedDict, total=False):
    """State schema for the content processing workflow.

    Using total=False allows fields to be absent until their node runs.
    """

    # Required - set at entry
    item_id: str

    # Set by classify
    raw_content: str
    content_type: ContentType
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
    error_step: ProcessingStep | None
    last_progress: float
    emit_update: ProcessingUpdateEmitter | None


NodeUpdate = ProcessingState


def _status_for_step(step: ProcessingStep) -> ProcessingStatus:
    if step == ProcessingStep.COMPLETED:
        return ProcessingStatus.COMPLETED
    if step == ProcessingStep.FAILED:
        return ProcessingStatus.FAILED
    return ProcessingStatus.PROCESSING


def _progress_for_step(step: ProcessingStep, last_progress: float) -> float:
    if step == ProcessingStep.FAILED:
        return last_progress if last_progress > 0.0 else 1.0
    return STEP_PROGRESS[step]


def emit_processing_update(
    state: ProcessingState,
    step: ProcessingStep,
    message: str | None = None,
) -> float | None:
    """Emit a typed processing update for websocket subscribers.

    Returns:
        The new progress value to include in the node's return dict,
        or None if no update was emitted.
    """
    item_id = state.get("item_id")
    emitter = state.get("emit_update")
    if not item_id or emitter is None:
        return None

    last_progress = state.get("last_progress", 0.0)
    progress = _progress_for_step(step, last_progress)

    try:
        update = ProcessingUpdate(
            item_id=item_id,
            status=_status_for_step(step),
            step=step,
            progress=progress,
            message=message or STEP_MESSAGES[step],
        )
    except Exception:
        logger.exception(
            "Failed to build processing update", extra={"item_id": item_id}
        )
        return None

    try:
        emitter(update)
    except Exception:
        logger.exception(
            "Processing update emitter failed",
            extra={"item_id": item_id, "step": step},
        )

    return progress


def _build_conservative_fallback_metadata(
    state: ProcessingState, llm_metadata: ExtractedMetadata | None
) -> ExtractedMetadata:
    """Build non-synthetic fallback metadata from source text only.

    Summary priority:
    1) LLM summary (if present)
    2) Item title (exact text)
    3) Raw excerpt from parsed content (exact text)

    Concepts/entities are only used when the LLM already provided them.
    """
    title = (state.get("title") or "").strip()
    parsed_text = (state.get("parsed_text") or "").strip()

    llm_summary = (llm_metadata.summary if llm_metadata else "").strip()
    if llm_summary:
        summary = llm_summary
    elif title:
        summary = title
    else:
        summary = parsed_text[:240]

    concepts = (
        [concept for concept in llm_metadata.concepts if concept]
        if llm_metadata
        else []
    )
    entities = (
        [entity for entity in llm_metadata.entities if entity] if llm_metadata else []
    )

    return ExtractedMetadata(summary=summary, concepts=concepts, entities=entities)


@log_node_execution("classify")
async def classify_node(state: ProcessingState) -> NodeUpdate:
    """Fetch item from DB, set processing status, determine content type.

    Creates the AI provider and stores it in state for downstream nodes.
    """
    current_step = ProcessingStep.CLASSIFY
    try:
        progress = emit_processing_update(state, step=current_step)
        item_id = state["item_id"]

        async with db_connection() as db:
            # Fetch item from database
            item = await item_repo.get(db, item_id)
            if item is None:
                return {
                    "error": f"Item not found: {item_id}",
                    "error_step": current_step,
                }

            # Update processing status to 'processing'
            await item_repo.update_status(db, item_id, ProcessingStatus.PROCESSING)
            await db.commit()

        # Create AI provider for downstream nodes
        provider = OllamaProvider()

        result: NodeUpdate = {
            "raw_content": item.content,
            "content_type": item.content_type,
            "title": item.title,
            "source_url": item.source_url,
            "ai_provider": provider,
        }
        if progress is not None:
            result["last_progress"] = progress
        return result
    except Exception as e:
        return {"error": str(e), "error_step": current_step}


@log_node_execution("parse")
async def parse_node(state: ProcessingState) -> NodeUpdate:
    """Parse raw content using ContentParser based on content type."""
    current_step = ProcessingStep.PARSING
    try:
        progress = emit_processing_update(state, step=current_step)
        parser = ContentParser()
        result = parser.parse(state["raw_content"], state["content_type"])

        # Use extracted title if better than existing
        new_title = result.title if result.title else state.get("title", "")

        node_result: NodeUpdate = {"parsed_text": result.text, "title": new_title}
        if progress is not None:
            node_result["last_progress"] = progress
        return node_result
    except Exception as e:
        return {"error": str(e), "error_step": current_step}


@log_node_execution("chunk")
async def chunk_node(state: ProcessingState) -> NodeUpdate:
    """Split parsed text into semantic chunks."""
    current_step = ProcessingStep.CHUNKING
    try:
        progress = emit_processing_update(state, step=current_step)
        chunker = ChunkingService()
        chunk_results = chunker.chunk_text(state["parsed_text"])

        result: NodeUpdate = {"chunk_results": chunk_results}
        if progress is not None:
            result["last_progress"] = progress
        return result
    except Exception as e:
        return {"error": str(e), "error_step": current_step}


@log_node_execution("extract_metadata")
async def extract_metadata_node(state: ProcessingState) -> NodeUpdate:
    """Extract summary, concepts, and entities using LLM."""
    current_step = ProcessingStep.EXTRACTING
    try:
        progress = emit_processing_update(state, step=current_step)
        provider = state["ai_provider"]
        extractor = MetadataExtractor(provider)

        metadata = await extractor.extract(
            text=state["parsed_text"],
            title=state.get("title"),
        )

        result: NodeUpdate = {"metadata": metadata}
        if progress is not None:
            result["last_progress"] = progress
        return result
    except Exception as e:
        return {"error": str(e), "error_step": current_step}


@log_node_execution("validate")
async def validate_node(state: ProcessingState) -> NodeUpdate:
    """Validate that chunks and metadata were successfully created."""
    current_step = ProcessingStep.VALIDATING
    try:
        progress = emit_processing_update(state, step=current_step)
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
                    "error_step": current_step,
                }
            return {"validation_passed": False, "retry_count": retry_count}

        # Check that metadata has required fields (summary and concepts)
        if metadata is None or not metadata.summary or not metadata.concepts:
            fallback = _build_conservative_fallback_metadata(state, metadata)
            logger.warning(
                "Validation recovered with conservative fallback metadata: "
                "llm_summary_present=%s llm_concepts_count=%d",
                bool(metadata and metadata.summary),
                len(metadata.concepts) if metadata else 0,
            )
            result: NodeUpdate = {"validation_passed": True, "metadata": fallback}
            if progress is not None:
                result["last_progress"] = progress
            return result

        logger.info(
            f"Validation passed: {len(chunk_results)} chunks, "
            f"{len(metadata.concepts)} concepts"
        )
        success_result: NodeUpdate = {"validation_passed": True}
        if progress is not None:
            success_result["last_progress"] = progress
        return success_result
    except Exception as e:
        return {"error": str(e), "error_step": current_step}


@log_node_execution("persist")
async def persist_node(state: ProcessingState) -> NodeUpdate:
    """Persist chunks, embeddings, and metadata to database.

    Only called after validation passes to avoid orphaned data on retries.
    Uses a single atomic commit at the end to prevent orphan data.
    """
    current_step = ProcessingStep.STORING
    try:
        progress = emit_processing_update(state, step=current_step)
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
            existing_metadata = (
                item.metadata.model_dump(exclude_none=True)
                if item and item.metadata
                else {}
            )

            # Add extracted metadata fields
            existing_metadata["summary"] = metadata.summary
            existing_metadata["concepts"] = metadata.concepts
            existing_metadata["entities"] = metadata.entities

            # Update title if we extracted a better one
            update_data = ItemUpdate(
                title=state.get("title"),
                metadata=normalize_item_metadata(existing_metadata),
            )
            await item_repo.update(db, item_id, update_data)

            # Single atomic commit - all-or-nothing
            await db.commit()

        result: NodeUpdate = {"chunks": created_chunks, "embeddings_stored": True}
        if progress is not None:
            result["last_progress"] = progress
        return result
    except Exception as e:
        return {"error": str(e), "error_step": current_step}


@log_node_execution("complete")
async def complete_node(state: ProcessingState) -> NodeUpdate:
    """Mark item processing as completed."""
    current_step = ProcessingStep.COMPLETED
    try:
        item_id = state["item_id"]

        async with db_connection() as db:
            await item_repo.update_status(db, item_id, ProcessingStatus.COMPLETED)
            await db.commit()

        progress = emit_processing_update(state, step=current_step)
        logger.info(f"Processing completed for item {item_id}")
        result: NodeUpdate = {}
        if progress is not None:
            result["last_progress"] = progress
        return result
    except Exception as e:
        return {"error": str(e), "error_step": current_step}


@log_node_execution("handle_error")
async def handle_error_node(state: ProcessingState) -> NodeUpdate:
    """Handle processing errors by updating item status and metadata."""
    item_id = state.get("item_id")
    error = state.get("error", "Unknown error")
    error_step = state.get("error_step") or ProcessingStep.FAILED
    failure_message = f"Processing failed during {error_step}: {error}"

    logger.error(
        f"Processing failed for item {item_id}: {error} (step: {error_step})",
        extra={"item_id": item_id, "error": error, "error_step": error_step},
    )

    if not item_id:
        logger.error("Cannot update status: item_id not set")
        emit_processing_update(
            state,
            step=ProcessingStep.FAILED,
            message=failure_message,
        )
        return {}

    try:
        async with db_connection() as db:
            # Update processing status to 'failed'
            await item_repo.update_status(db, item_id, ProcessingStatus.FAILED)

            # Merge error info into item metadata (preserve existing)
            item = await item_repo.get(db, item_id)
            existing_metadata = (
                item.metadata.model_dump(exclude_none=True)
                if item and item.metadata
                else {}
            )
            existing_metadata["processing_error"] = error
            existing_metadata["error_step"] = error_step

            await item_repo.update(
                db,
                item_id,
                ItemUpdate(metadata=normalize_item_metadata(existing_metadata)),
            )
            await db.commit()

    except Exception as e:
        logger.exception(f"Failed to update error status: {e}")
    finally:
        emit_processing_update(
            state,
            step=ProcessingStep.FAILED,
            message=failure_message,
        )

    return {}


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


def build_processing_graph() -> CompiledStateGraph[
    ProcessingState, None, ProcessingState, ProcessingState
]:
    """Build and compile the content processing workflow graph."""
    builder = StateGraph(ProcessingState)

    # Add nodes
    builder.add_node("classify", cast(Any, classify_node))
    builder.add_node("parse", cast(Any, parse_node))
    builder.add_node("chunk", cast(Any, chunk_node))
    builder.add_node("extract_metadata", cast(Any, extract_metadata_node))
    builder.add_node("validate", cast(Any, validate_node))
    builder.add_node("persist", cast(Any, persist_node))
    builder.add_node("complete", cast(Any, complete_node))
    builder.add_node("handle_error", cast(Any, handle_error_node))

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

    return cast(
        CompiledStateGraph[ProcessingState, None, ProcessingState, ProcessingState],
        builder.compile(),
    )


# Compile the graph once at module load
graph = build_processing_graph()


async def process_item(
    item_id: str,
    emit_update: ProcessingUpdateEmitter | None = None,
) -> ProcessingState:
    """Process an item through the full content processing pipeline.

    This is the main entry point for processing a saved item.

    Args:
        item_id: The ID of the item to process.

    Returns:
        The final ProcessingState containing results or error information.
    """
    initial_state: ProcessingState = {
        "item_id": item_id,
        "last_progress": 0.0,
    }
    if emit_update is not None:
        initial_state["emit_update"] = emit_update
    result = await graph.ainvoke(initial_state)
    return cast(ProcessingState, result)
