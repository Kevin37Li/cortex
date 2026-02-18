"""Tests for SearchService and reciprocal rank fusion."""

from unittest.mock import AsyncMock, patch

import aiosqlite
import pytest
import sqlite_vec
from src.db import ChunkSearchResult
from src.db.database import EMBEDDING_DIMENSION
from src.exceptions import SearchError
from src.services.search import SearchService, reciprocal_rank_fusion


def _one_hot_embedding(index: int) -> list[float]:
    embedding = [0.0] * EMBEDDING_DIMENSION
    embedding[index] = 1.0
    return embedding


async def _seed_search_data(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        INSERT INTO items (id, title, content, content_type)
        VALUES (?, ?, ?, ?)
        """,
        ["item-1", "First Item", "Item one content", "note"],
    )
    await db.execute(
        """
        INSERT INTO items (id, title, content, content_type)
        VALUES (?, ?, ?, ?)
        """,
        ["item-2", "Second Item", "Item two content", "webpage"],
    )

    await db.execute(
        """
        INSERT INTO chunks (id, item_id, content, chunk_index, token_count)
        VALUES (?, ?, ?, ?, ?)
        """,
        ["chunk-1", "item-1", "alpha beta gamma", 0, 3],
    )
    await db.execute(
        """
        INSERT INTO chunks (id, item_id, content, chunk_index, token_count)
        VALUES (?, ?, ?, ?, ?)
        """,
        ["chunk-2", "item-1", "alpha alpha delta", 1, 3],
    )
    await db.execute(
        """
        INSERT INTO chunks (id, item_id, content, chunk_index, token_count)
        VALUES (?, ?, ?, ?, ?)
        """,
        ["chunk-3", "item-2", "epsilon zeta", 0, 2],
    )

    await db.execute(
        "INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)",
        ["chunk-1", sqlite_vec.serialize_float32(_one_hot_embedding(0))],
    )
    await db.execute(
        "INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)",
        ["chunk-2", sqlite_vec.serialize_float32(_one_hot_embedding(1))],
    )
    await db.execute(
        "INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)",
        ["chunk-3", sqlite_vec.serialize_float32(_one_hot_embedding(2))],
    )
    await db.commit()


# search_service fixture is defined in tests/conftest.py


class TestVectorSearch:
    """Tests for vector_search behavior."""

    async def test_returns_ranked_results_with_normalized_scores(
        self,
        search_service: SearchService,
        db_with_vec: aiosqlite.Connection,
    ) -> None:
        await _seed_search_data(db_with_vec)

        results = await search_service.vector_search(
            "alpha",
            db=db_with_vec,
            limit=3,
            query_embedding=_one_hot_embedding(0),
        )

        assert len(results) == 3
        assert results[0].chunk_id == "chunk-1"
        assert all(0.0 <= result.score <= 1.0 for result in results)
        assert results[0].score >= results[1].score
        assert results[0].score >= results[2].score

    async def test_uses_precomputed_embedding_without_embed_query_call(
        self,
        search_service: SearchService,
        db_with_vec: aiosqlite.Connection,
    ) -> None:
        await _seed_search_data(db_with_vec)

        with patch.object(
            search_service._embedding_service,
            "embed_query",
            new_callable=AsyncMock,
        ) as embed_query_mock:
            results = await search_service.vector_search(
                "alpha",
                db=db_with_vec,
                limit=3,
                query_embedding=_one_hot_embedding(0),
            )

        assert results
        embed_query_mock.assert_not_awaited()

    async def test_clamps_limit_to_minimum(
        self,
        search_service: SearchService,
        db_with_vec: aiosqlite.Connection,
    ) -> None:
        await _seed_search_data(db_with_vec)

        results = await search_service.vector_search(
            "alpha",
            db=db_with_vec,
            limit=0,
            query_embedding=_one_hot_embedding(0),
        )

        assert len(results) == 1

    async def test_clamps_limit_to_maximum(
        self,
        search_service: SearchService,
    ) -> None:
        db = AsyncMock()
        cursor = AsyncMock()
        cursor.fetchall.return_value = []
        db.execute = AsyncMock(return_value=cursor)

        await search_service.vector_search(
            "alpha",
            db=db,
            limit=1000,
            query_embedding=_one_hot_embedding(0),
        )

        first_call_args = db.execute.await_args_list[0].args
        assert first_call_args[1][1] == 100

    async def test_wraps_unexpected_errors_in_search_error(
        self,
        search_service: SearchService,
        db_connection: aiosqlite.Connection,
    ) -> None:
        with pytest.raises(SearchError) as exc_info:
            await search_service.vector_search(
                "alpha",
                db=db_connection,
                query_embedding=_one_hot_embedding(0),
            )

        assert exc_info.value.step == "vector_search"
        assert "Vector search failed" in str(exc_info.value)


class TestFtsSearch:
    """Tests for fts_search behavior."""

    async def test_returns_normalized_scores_sorted_by_relevance(
        self,
        search_service: SearchService,
        db_with_vec: aiosqlite.Connection,
    ) -> None:
        await _seed_search_data(db_with_vec)

        results = await search_service.fts_search("alpha", db=db_with_vec, limit=20)

        assert len(results) == 2
        assert all(0.0 <= result.score <= 1.0 for result in results)
        assert results[0].score >= results[1].score

    async def test_sanitizes_malformed_match_input(
        self,
        search_service: SearchService,
        db_with_vec: aiosqlite.Connection,
    ) -> None:
        await _seed_search_data(db_with_vec)

        results = await search_service.fts_search('alpha "broken', db=db_with_vec)

        assert isinstance(results, list)
        assert all(0.0 <= result.score <= 1.0 for result in results)

    async def test_clamps_limit_to_minimum(
        self,
        search_service: SearchService,
        db_with_vec: aiosqlite.Connection,
    ) -> None:
        await _seed_search_data(db_with_vec)

        results = await search_service.fts_search("alpha", db=db_with_vec, limit=0)

        assert len(results) == 1

    async def test_clamps_limit_to_maximum(
        self,
        search_service: SearchService,
    ) -> None:
        db = AsyncMock()
        cursor = AsyncMock()
        cursor.fetchall.return_value = []
        db.execute = AsyncMock(return_value=cursor)

        await search_service.fts_search("alpha", db=db, limit=1000)

        first_call_args = db.execute.await_args_list[0].args
        assert first_call_args[1][1] == 100


class TestHybridSearch:
    """Tests for hybrid_search behavior."""

    async def test_deduplicates_and_truncates_fused_results(
        self,
        search_service: SearchService,
        db_with_vec: aiosqlite.Connection,
    ) -> None:
        vector_results = [
            ChunkSearchResult(
                chunk_id="chunk-z",
                item_id="item-1",
                content="vector z",
                score=1.0,
            ),
            ChunkSearchResult(
                chunk_id="chunk-a",
                item_id="item-2",
                content="vector a",
                score=0.9,
            ),
        ]
        fts_results = [
            ChunkSearchResult(
                chunk_id="chunk-a",
                item_id="item-2",
                content="fts a",
                score=1.0,
            ),
            ChunkSearchResult(
                chunk_id="chunk-z",
                item_id="item-1",
                content="fts z",
                score=0.9,
            ),
        ]

        with (
            patch.object(
                search_service,
                "vector_search",
                new=AsyncMock(return_value=vector_results),
            ) as vector_mock,
            patch.object(
                search_service,
                "fts_search",
                new=AsyncMock(return_value=fts_results),
            ) as fts_mock,
        ):
            results = await search_service.hybrid_search(
                "query",
                db=db_with_vec,
                limit=1,
            )

        assert len(results) == 1
        assert results[0].chunk_id == "chunk-a"
        vector_mock.assert_awaited_once_with("query", db=db_with_vec, limit=1)
        assert fts_mock.await_count == 1
        fts_call = fts_mock.await_args
        assert fts_call.kwargs["limit"] == 1
        assert fts_call.kwargs["db"] is not db_with_vec

    async def test_preserves_existing_search_error(
        self,
        search_service: SearchService,
        db_with_vec: aiosqlite.Connection,
    ) -> None:
        original = SearchError("boom", query="q", step="vector_search")
        with (
            patch.object(
                search_service,
                "vector_search",
                new=AsyncMock(side_effect=original),
            ),
            patch.object(
                search_service,
                "fts_search",
                new=AsyncMock(return_value=[]),
            ),
            pytest.raises(SearchError) as exc_info,
        ):
            await search_service.hybrid_search("q", db=db_with_vec)

        assert exc_info.value is original

    async def test_clamps_limit_to_maximum(
        self,
        search_service: SearchService,
        db_with_vec: aiosqlite.Connection,
    ) -> None:
        with (
            patch.object(
                search_service,
                "vector_search",
                new=AsyncMock(return_value=[]),
            ) as vector_mock,
            patch.object(
                search_service,
                "fts_search",
                new=AsyncMock(return_value=[]),
            ) as fts_mock,
        ):
            await search_service.hybrid_search("query", db=db_with_vec, limit=1000)

        vector_mock.assert_awaited_once_with("query", db=db_with_vec, limit=100)
        assert fts_mock.await_count == 1
        fts_call = fts_mock.await_args
        assert fts_call.kwargs["limit"] == 100
        assert fts_call.kwargs["db"] is not db_with_vec

    async def test_falls_back_to_single_connection_when_db_path_unavailable(
        self,
        search_service: SearchService,
        db_with_vec: aiosqlite.Connection,
    ) -> None:
        with (
            patch.object(
                search_service,
                "_resolve_main_db_path",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                search_service,
                "vector_search",
                new=AsyncMock(return_value=[]),
            ) as vector_mock,
            patch.object(
                search_service,
                "fts_search",
                new=AsyncMock(return_value=[]),
            ) as fts_mock,
        ):
            await search_service.hybrid_search("query", db=db_with_vec, limit=3)

        vector_mock.assert_awaited_once_with("query", db=db_with_vec, limit=3)
        fts_mock.assert_awaited_once_with("query", db=db_with_vec, limit=3)

    async def test_top_result_score_is_normalized_to_one(
        self,
        search_service: SearchService,
        db_with_vec: aiosqlite.Connection,
    ) -> None:
        """Hybrid results should have scores in [0, 1] comparable to vector/FTS."""
        vector_results = [
            ChunkSearchResult(
                chunk_id="chunk-a", item_id="item-1", content="a", score=0.9
            ),
            ChunkSearchResult(
                chunk_id="chunk-b", item_id="item-1", content="b", score=0.7
            ),
        ]
        fts_results = [
            ChunkSearchResult(
                chunk_id="chunk-b", item_id="item-1", content="b", score=0.9
            ),
        ]

        with (
            patch.object(
                search_service,
                "vector_search",
                new=AsyncMock(return_value=vector_results),
            ),
            patch.object(
                search_service, "fts_search", new=AsyncMock(return_value=fts_results)
            ),
        ):
            results = await search_service.hybrid_search("query", db=db_with_vec)

        assert results
        assert results[0].score == pytest.approx(1.0), (
            "Top hybrid result score must be 1.0, not a raw RRF value near 0"
        )
        assert all(0.0 <= r.score <= 1.0 for r in results)


class TestEnrichResults:
    """Tests for enrich_results behavior."""

    async def test_filters_orphans_clamps_score_and_assigns_contiguous_ranks(
        self,
        search_service: SearchService,
        db_with_vec: aiosqlite.Connection,
    ) -> None:
        await _seed_search_data(db_with_vec)
        results = [
            ChunkSearchResult(
                chunk_id="chunk-1",
                item_id="item-1",
                content="alpha beta gamma",
                score=2.5,
            ),
            ChunkSearchResult(
                chunk_id="missing-chunk",
                item_id="missing-item",
                content="orphan",
                score=0.4,
            ),
            ChunkSearchResult(
                chunk_id="chunk-3",
                item_id="item-2",
                content="epsilon zeta",
                score=-0.2,
            ),
        ]

        enriched = await search_service.enrich_results(results, db=db_with_vec)

        assert len(enriched) == 2
        assert [result.rank for result in enriched] == [1, 2]
        assert enriched[0].item_title == "First Item"
        assert enriched[1].item_title == "Second Item"
        assert enriched[0].score == 1.0
        assert enriched[1].score == 0.0


class TestSearchGuardrails:
    """Tests for query validation and helper behavior."""

    @pytest.mark.parametrize(
        "method_name", ["vector_search", "fts_search", "hybrid_search"]
    )
    async def test_rejects_blank_queries(
        self,
        method_name: str,
        search_service: SearchService,
        db_with_vec: aiosqlite.Connection,
    ) -> None:
        method = getattr(search_service, method_name)

        with pytest.raises(SearchError, match=r"blank"):
            await method("   ", db=db_with_vec)

    @pytest.mark.parametrize("query", [None, 123, True])
    @pytest.mark.parametrize(
        "method_name", ["vector_search", "fts_search", "hybrid_search"]
    )
    async def test_rejects_non_string_queries(
        self,
        method_name: str,
        query: object,
        search_service: SearchService,
        db_with_vec: aiosqlite.Connection,
    ) -> None:
        method = getattr(search_service, method_name)

        with pytest.raises(SearchError, match=r"string"):
            await method(query, db=db_with_vec)  # type: ignore[arg-type]

    @pytest.mark.parametrize("limit", [None, "10", 5.5, True])
    @pytest.mark.parametrize(
        "method_name", ["vector_search", "fts_search", "hybrid_search"]
    )
    async def test_rejects_non_integer_limits(
        self,
        method_name: str,
        limit: object,
        search_service: SearchService,
        db_with_vec: aiosqlite.Connection,
    ) -> None:
        method = getattr(search_service, method_name)

        with pytest.raises(SearchError, match=r"integer"):
            await method("alpha", db=db_with_vec, limit=limit)  # type: ignore[arg-type]


class TestReciprocalRankFusion:
    """Tests for reciprocal_rank_fusion helper."""

    def test_breaks_ties_deterministically_by_chunk_id(self) -> None:
        vector_results = [
            ChunkSearchResult(
                chunk_id="chunk-z",
                item_id="item-1",
                content="vector z",
                score=0.9,
            ),
            ChunkSearchResult(
                chunk_id="chunk-a",
                item_id="item-2",
                content="vector a",
                score=0.8,
            ),
        ]
        fts_results = [
            ChunkSearchResult(
                chunk_id="chunk-a",
                item_id="item-2",
                content="fts a",
                score=0.9,
            ),
            ChunkSearchResult(
                chunk_id="chunk-z",
                item_id="item-1",
                content="fts z",
                score=0.8,
            ),
        ]

        fused = reciprocal_rank_fusion(vector_results, fts_results)

        assert [result.chunk_id for result in fused] == ["chunk-a", "chunk-z"]

    def test_normalizes_top_score_to_one(self) -> None:
        vector_results = [
            ChunkSearchResult(
                chunk_id="chunk-1", item_id="item-1", content="a", score=0.9
            ),
            ChunkSearchResult(
                chunk_id="chunk-2", item_id="item-1", content="b", score=0.8
            ),
        ]
        fts_results = [
            ChunkSearchResult(
                chunk_id="chunk-2", item_id="item-1", content="b", score=0.9
            ),
        ]

        fused = reciprocal_rank_fusion(vector_results, fts_results)

        assert fused[0].score == pytest.approx(1.0)
        assert all(0.0 <= r.score <= 1.0 for r in fused)

    def test_raises_for_non_positive_k(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            reciprocal_rank_fusion([], [], k=0)
