"""Tests for search request/response models."""

import pytest
from pydantic import ValidationError
from src.db.models import (
    ChunkSearchResult,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)


class TestSearchRequest:
    """Validation tests for SearchRequest."""

    def test_defaults(self):
        request = SearchRequest(query="machine learning")

        assert request.query == "machine learning"
        assert request.limit == 20
        assert request.search_type == "hybrid"

    @pytest.mark.parametrize("limit", [1, 20, 100])
    def test_limit_accepts_bounds(self, limit: int):
        request = SearchRequest(query="test", limit=limit)

        assert request.limit == limit

    @pytest.mark.parametrize("limit", [0, 101])
    def test_limit_rejects_out_of_bounds(self, limit: int):
        with pytest.raises(ValidationError):
            SearchRequest(query="test", limit=limit)

    @pytest.mark.parametrize("search_type", ["hybrid", "vector", "fts"])
    def test_search_type_accepts_allowed_values(self, search_type: str):
        request = SearchRequest(query="test", search_type=search_type)

        assert request.search_type == search_type

    def test_search_type_rejects_invalid_value(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="test", search_type="keyword")

    def test_forbids_extra_fields(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="test", unknown_field="value")

    def test_rejects_empty_query(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="")

    @pytest.mark.parametrize("query", ["   ", "\n\t  "])
    def test_rejects_whitespace_only_query(self, query: str):
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(query=query)

        assert "Query must not be blank" in str(exc_info.value)

    def test_strips_whitespace_from_query(self):
        request = SearchRequest(query="  hello  ")

        assert request.query == "hello"

    def test_accepts_query_at_max_length(self):
        request = SearchRequest(query="a" * 1000)

        assert len(request.query) == 1000

    def test_accepts_padded_query_when_trimmed_length_is_max(self):
        request = SearchRequest(query=f" {'a' * 1000} ")

        assert request.query == "a" * 1000

    def test_rejects_query_exceeding_max_length(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="a" * 1001)


class TestSearchResultItem:
    """Validation tests for SearchResultItem."""

    def test_valid_result_item(self):
        result = SearchResultItem(
            item_id="item-1",
            item_title="Test Item",
            content_type="note",
            chunk_id="chunk-1",
            chunk_content="Matching snippet",
            score=0.75,
            rank=1,
        )

        assert result.item_id == "item-1"
        assert result.item_title == "Test Item"
        assert result.content_type == "note"
        assert result.chunk_content == "Matching snippet"
        assert result.score == 0.75
        assert result.rank == 1

    @pytest.mark.parametrize("score", [-0.01, 1.01])
    def test_rejects_score_out_of_bounds(self, score: float):
        with pytest.raises(ValidationError):
            SearchResultItem(
                item_id="item-1",
                item_title="Test Item",
                content_type="note",
                chunk_id="chunk-1",
                chunk_content="Matching snippet",
                score=score,
                rank=1,
            )

    def test_rejects_non_positive_rank(self):
        with pytest.raises(ValidationError):
            SearchResultItem(
                item_id="item-1",
                item_title="Test Item",
                content_type="note",
                chunk_id="chunk-1",
                chunk_content="Matching snippet",
                score=0.5,
                rank=0,
            )


class TestSearchResponse:
    """Validation tests for SearchResponse."""

    def test_valid_response(self):
        response = SearchResponse(
            results=[
                SearchResultItem(
                    item_id="item-1",
                    item_title="Test Item",
                    content_type="note",
                    chunk_id="chunk-1",
                    chunk_content="Matching snippet",
                    score=0.75,
                    rank=1,
                )
            ],
            total=1,
            query="test query",
            search_type="hybrid",
        )

        assert len(response.results) == 1
        assert response.total == 1
        assert response.query == "test query"
        assert response.search_type == "hybrid"

    def test_rejects_invalid_search_type(self):
        with pytest.raises(ValidationError):
            SearchResponse(
                results=[],
                total=0,
                query="test",
                search_type="keyword",
            )

    def test_rejects_negative_total(self):
        with pytest.raises(ValidationError):
            SearchResponse(
                results=[],
                total=-1,
                query="test",
                search_type="hybrid",
            )


class TestChunkSearchResult:
    """Validation tests for ChunkSearchResult."""

    def test_valid_chunk_search_result(self):
        result = ChunkSearchResult(
            chunk_id="chunk-1",
            item_id="item-1",
            content="raw chunk match",
            score=0.6,
        )

        assert result.chunk_id == "chunk-1"
        assert result.item_id == "item-1"
        assert result.content == "raw chunk match"
        assert result.score == 0.6

    @pytest.mark.parametrize("score", [-5.0, 0.0, 1.0, 999.0])
    def test_accepts_unbounded_scores(self, score: float):
        """Raw search backend scores are intentionally unbounded; normalization happens during enrichment."""
        result = ChunkSearchResult(
            chunk_id="chunk-1",
            item_id="item-1",
            content="raw chunk match",
            score=score,
        )

        assert result.score == score
