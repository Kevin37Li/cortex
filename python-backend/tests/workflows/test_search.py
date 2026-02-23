"""Tests for search workflow routing and orchestration."""

import importlib
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from src.db import ChunkSearchResult, ContentType, SearchResultItem
from src.db.database import init_database
from src.exceptions import SearchError

workflow = importlib.import_module("src.workflows.search")


class TestImportSmoke:
    """Smoke tests for workflow and app import stability."""

    def test_main_imports_without_circular_dependency(self) -> None:
        main_module = importlib.import_module("src.main")
        assert hasattr(main_module, "app")


@pytest.fixture(scope="function")
async def search_workflow_db(temp_db_path: Path) -> AsyncIterator[None]:
    """Initialize a temporary DB for search workflow tests."""
    with patch("src.config.settings.db_path", temp_db_path):
        await init_database()
        yield


def _chunk(
    chunk_id: str,
    *,
    item_id: str = "item-1",
    content: str = "chunk content",
    score: float = 0.9,
) -> ChunkSearchResult:
    return ChunkSearchResult(
        chunk_id=chunk_id,
        item_id=item_id,
        content=content,
        score=score,
    )


def _result(
    chunk_id: str,
    *,
    rank: int = 1,
    item_id: str = "item-1",
    title: str = "Result item",
) -> SearchResultItem:
    return SearchResultItem(
        item_id=item_id,
        item_title=title,
        content_type=ContentType.NOTE,
        chunk_id=chunk_id,
        chunk_content="snippet",
        score=0.95,
        rank=rank,
    )


class TestSearchRoutingHelpers:
    """Unit tests for search workflow routing helpers."""

    def test_route_after_entry_routes_fts_to_fts_node(self) -> None:
        assert workflow.route_after_entry({"search_type": "fts"}) == "fts_search"

    def test_route_after_entry_routes_vector_to_embed_node(self) -> None:
        assert workflow.route_after_entry({"search_type": "vector"}) == "embed_query"

    def test_route_after_entry_routes_hybrid_to_embed_node(self) -> None:
        assert workflow.route_after_entry({"search_type": "hybrid"}) == "embed_query"

    def test_route_after_entry_prioritizes_error(self) -> None:
        assert workflow.route_after_entry({"error": "boom"}) == "handle_error"

    def test_route_after_vector_routes_hybrid_to_fts(self) -> None:
        assert workflow.route_after_vector({"search_type": "hybrid"}) == "fts_search"

    def test_route_after_vector_routes_vector_to_fuse(self) -> None:
        assert workflow.route_after_vector({"search_type": "vector"}) == "fuse_results"

    def test_route_after_vector_prioritizes_error(self) -> None:
        assert workflow.route_after_vector({"error": "boom"}) == "handle_error"


class TestFuseResultsNode:
    """Unit tests for fuse_results node behavior."""

    async def test_hybrid_uses_rrf_and_applies_limit(self) -> None:
        vector_results = [_chunk("chunk-1"), _chunk("chunk-2")]
        fts_results = [_chunk("chunk-2"), _chunk("chunk-1")]
        fused = [_chunk("chunk-2", score=1.0), _chunk("chunk-1", score=0.8)]

        with patch.object(
            workflow,
            "reciprocal_rank_fusion",
            return_value=fused,
        ) as rrf_mock:
            result = await workflow.fuse_results_node(
                {
                    "search_type": "hybrid",
                    "limit": 1,
                    "vector_results": vector_results,
                    "fts_results": fts_results,
                }
            )

        assert result["fused_results"] == [fused[0]]
        rrf_mock.assert_called_once_with(vector_results, fts_results)

    async def test_vector_mode_passes_through_vector_results(self) -> None:
        vector_results = [_chunk("chunk-1"), _chunk("chunk-2")]
        result = await workflow.fuse_results_node(
            {"search_type": "vector", "limit": 1, "vector_results": vector_results}
        )

        assert result["fused_results"] == [vector_results[0]]

    async def test_fts_mode_passes_through_fts_results(self) -> None:
        fts_results = [_chunk("chunk-a"), _chunk("chunk-b")]
        result = await workflow.fuse_results_node(
            {"search_type": "fts", "limit": 1, "fts_results": fts_results}
        )

        assert result["fused_results"] == [fts_results[0]]

    async def test_returns_error_state_when_rrf_raises(self) -> None:
        with patch.object(
            workflow,
            "reciprocal_rank_fusion",
            side_effect=RuntimeError("rrf failed"),
        ):
            result = await workflow.fuse_results_node(
                {
                    "search_type": "hybrid",
                    "limit": 5,
                    "vector_results": [_chunk("chunk-1")],
                    "fts_results": [_chunk("chunk-2")],
                }
            )

        assert result["error"] == "rrf failed"
        assert result["error_step"] == "fuse_results"


class TestWorkflowNodes:
    """Unit tests for individual workflow nodes."""

    async def test_fts_search_node_returns_error_state_on_exception(
        self, search_workflow_db
    ) -> None:
        del search_workflow_db
        with patch.object(
            workflow.SearchService,
            "fts_search",
            new=AsyncMock(side_effect=RuntimeError("fts node failed")),
        ):
            result = await workflow.fts_search_node({"query": "alpha", "limit": 5})

        assert result["error"] == "fts node failed"
        assert result["error_step"] == "fts_search"

    async def test_enrich_results_node_returns_error_state_on_exception(
        self, search_workflow_db
    ) -> None:
        del search_workflow_db
        with patch.object(
            workflow.SearchService,
            "enrich_results",
            new=AsyncMock(side_effect=RuntimeError("enrich node failed")),
        ):
            result = await workflow.enrich_results_node(
                {"fused_results": [_chunk("chunk-1")]}
            )

        assert result["error"] == "enrich node failed"
        assert result["error_step"] == "enrich_results"


@pytest.mark.integration
class TestSearchWorkflow:
    """Integration-style tests for search workflow graph behavior."""

    async def test_hybrid_search_runs_vector_and_fts_then_enriches(
        self, search_workflow_db
    ) -> None:
        del search_workflow_db
        embedding = [0.1, 0.2, 0.3]
        vector_results = [_chunk("chunk-v1"), _chunk("chunk-v2")]
        fts_results = [_chunk("chunk-f1"), _chunk("chunk-f2")]
        enriched = [_result("chunk-v1")]

        with (
            patch.object(
                workflow.EmbeddingService,
                "embed_query",
                new=AsyncMock(return_value=embedding),
            ) as embed_query_mock,
            patch.object(
                workflow.SearchService,
                "vector_search",
                new=AsyncMock(return_value=vector_results),
            ) as vector_search_mock,
            patch.object(
                workflow.SearchService,
                "fts_search",
                new=AsyncMock(return_value=fts_results),
            ) as fts_search_mock,
            patch.object(
                workflow.SearchService,
                "enrich_results",
                new=AsyncMock(return_value=enriched),
            ) as enrich_results_mock,
        ):
            result = await workflow.search(
                "hybrid query", search_type="hybrid", limit=5
            )

        assert result["final_results"] == enriched
        embed_query_mock.assert_awaited_once()
        vector_search_mock.assert_awaited_once()
        assert vector_search_mock.await_args.kwargs["query_embedding"] == embedding
        fts_search_mock.assert_awaited_once()
        enrich_results_mock.assert_awaited_once()

    async def test_vector_search_skips_fts_node(self, search_workflow_db) -> None:
        del search_workflow_db
        vector_results = [_chunk("chunk-1"), _chunk("chunk-2"), _chunk("chunk-3")]
        enriched = [_result("chunk-1"), _result("chunk-2", rank=2)]

        with (
            patch.object(
                workflow.EmbeddingService,
                "embed_query",
                new=AsyncMock(return_value=[0.3, 0.4]),
            ) as embed_query_mock,
            patch.object(
                workflow.SearchService,
                "vector_search",
                new=AsyncMock(return_value=vector_results),
            ) as vector_search_mock,
            patch.object(
                workflow.SearchService,
                "fts_search",
                new=AsyncMock(return_value=[]),
            ) as fts_search_mock,
            patch.object(
                workflow.SearchService,
                "enrich_results",
                new=AsyncMock(return_value=enriched),
            ) as enrich_results_mock,
        ):
            result = await workflow.search(
                "vector query", search_type="vector", limit=2
            )

        assert result["final_results"] == enriched
        embed_query_mock.assert_awaited_once()
        vector_search_mock.assert_awaited_once()
        fts_search_mock.assert_not_awaited()
        enrich_results_mock.assert_awaited_once()
        enriched_input = enrich_results_mock.await_args.args[0]
        assert len(enriched_input) == 2
        assert [chunk.chunk_id for chunk in enriched_input] == ["chunk-1", "chunk-2"]

    async def test_fts_search_skips_embedding_and_vector_nodes(
        self, search_workflow_db
    ) -> None:
        del search_workflow_db
        fts_results = [_chunk("chunk-f1"), _chunk("chunk-f2")]
        enriched = [_result("chunk-f1")]

        with (
            patch.object(
                workflow.EmbeddingService,
                "embed_query",
                new=AsyncMock(return_value=[0.9]),
            ) as embed_query_mock,
            patch.object(
                workflow.SearchService,
                "vector_search",
                new=AsyncMock(return_value=[]),
            ) as vector_search_mock,
            patch.object(
                workflow.SearchService,
                "fts_search",
                new=AsyncMock(return_value=fts_results),
            ) as fts_search_mock,
            patch.object(
                workflow.SearchService,
                "enrich_results",
                new=AsyncMock(return_value=enriched),
            ) as enrich_results_mock,
        ):
            result = await workflow.search("fts query", search_type="fts", limit=3)

        assert result["final_results"] == enriched
        embed_query_mock.assert_not_awaited()
        vector_search_mock.assert_not_awaited()
        fts_search_mock.assert_awaited_once()
        enrich_results_mock.assert_awaited_once()

    async def test_embed_query_error_routes_to_handle_error(
        self, search_workflow_db
    ) -> None:
        del search_workflow_db

        with patch.object(
            workflow.EmbeddingService,
            "embed_query",
            new=AsyncMock(side_effect=Exception("ollama down")),
        ):
            result = await workflow.search("test query", search_type="vector", limit=5)

        assert "ollama down" in result["error"]
        assert result["error_step"] == "embed_query"

    async def test_vector_error_routes_to_handle_error(
        self, search_workflow_db
    ) -> None:
        del search_workflow_db

        with (
            patch.object(
                workflow.EmbeddingService,
                "embed_query",
                new=AsyncMock(return_value=[0.1]),
            ),
            patch.object(
                workflow.SearchService,
                "vector_search",
                new=AsyncMock(
                    side_effect=SearchError(
                        "vector boom", query="vector query", step="vector_search"
                    )
                ),
            ),
            patch.object(
                workflow.SearchService,
                "fts_search",
                new=AsyncMock(return_value=[]),
            ) as fts_search_mock,
            patch.object(
                workflow.SearchService,
                "enrich_results",
                new=AsyncMock(return_value=[]),
            ) as enrich_results_mock,
        ):
            result = await workflow.search(
                "vector query",
                search_type="vector",
                limit=5,
            )

        assert "vector boom" in result["error"]
        assert result["error_step"] == "vector_search"
        fts_search_mock.assert_not_awaited()
        enrich_results_mock.assert_not_awaited()

    async def test_handle_error_logs_and_preserves_error_fields(self) -> None:
        state: workflow.SearchState = {
            "query": "query text",
            "error": "boom",
            "error_step": "vector_search",
        }

        with patch.object(workflow.logger, "error") as error_mock:
            result = await workflow.handle_error_node(state)

        assert result == {}
        assert state["error"] == "boom"
        assert state["error_step"] == "vector_search"
        assert state["query"] == "query text"
        error_mock.assert_called_once_with(
            "Search failed at step 'vector_search': boom",
            extra={"query": "query text"},
        )
