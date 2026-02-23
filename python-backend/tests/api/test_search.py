"""Tests for search API endpoint."""

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from src.exceptions import SearchError


def _assert_validation_error_payload(response_json: dict) -> list[dict]:
    """Assert FastAPI/Pydantic validation payload shape."""
    assert "detail" in response_json
    errors = response_json["detail"]
    assert isinstance(errors, list)
    assert errors
    first_error = errors[0]
    assert isinstance(first_error, dict)
    assert "type" in first_error
    assert "loc" in first_error
    assert "msg" in first_error
    return errors


class TestSearchItems:
    """Test POST /api/search/ endpoint."""

    async def test_search_success_returns_results(self, client: AsyncClient):
        """Test successful workflow response is returned as SearchResponse."""
        workflow_result = {
            "final_results": [
                {
                    "item_id": "item-1",
                    "item_title": "Hybrid Result",
                    "content_type": "note",
                    "chunk_id": "chunk-1",
                    "chunk_content": "Matched content",
                    "score": 0.95,
                    "rank": 1,
                }
            ]
        }

        with patch(
            "src.api.routes.search.search",
            new=AsyncMock(return_value=workflow_result),
        ) as search_mock:
            response = await client.post(
                "/api/search/",
                json={
                    "query": "hybrid retrieval",
                    "search_type": "hybrid",
                    "limit": 20,
                },
            )

        assert response.status_code == 200
        assert response.json() == {
            "results": workflow_result["final_results"],
            "total": 1,
            "query": "hybrid retrieval",
            "search_type": "hybrid",
        }
        search_mock.assert_awaited_once_with(
            query="hybrid retrieval",
            search_type="hybrid",
            limit=20,
        )

    async def test_search_empty_results_returns_200(self, client: AsyncClient):
        """Test empty workflow results return an empty list, not 404."""
        with patch(
            "src.api.routes.search.search",
            new=AsyncMock(return_value={"final_results": []}),
        ) as search_mock:
            response = await client.post(
                "/api/search/",
                json={
                    "query": "no matches",
                    "search_type": "fts",
                    "limit": 5,
                },
            )

        assert response.status_code == 200
        assert response.json() == {
            "results": [],
            "total": 0,
            "query": "no matches",
            "search_type": "fts",
        }
        search_mock.assert_awaited_once_with(
            query="no matches",
            search_type="fts",
            limit=5,
        )

    async def test_search_error_state_raises_search_error(self, client: AsyncClient):
        """Test workflow error state is translated to SearchError response."""
        with patch(
            "src.api.routes.search.search",
            new=AsyncMock(
                return_value={"error": "vector search failed", "error_step": "vector"}
            ),
        ) as search_mock:
            response = await client.post(
                "/api/search/",
                json={
                    "query": "test query",
                    "search_type": "vector",
                    "limit": 10,
                },
            )

        assert response.status_code == 500
        assert response.json() == {
            "error": "search_error",
            "message": "vector search failed",
        }
        search_mock.assert_awaited_once_with(
            query="test query",
            search_type="vector",
            limit=10,
        )

    async def test_search_error_state_with_empty_string_returns_500(
        self,
        client: AsyncClient,
    ):
        """Test falsey error payloads still map to SearchError response."""
        with patch(
            "src.api.routes.search.search",
            new=AsyncMock(return_value={"error": "", "error_step": "vector"}),
        ) as search_mock:
            response = await client.post(
                "/api/search/",
                json={
                    "query": "test query",
                    "search_type": "vector",
                    "limit": 10,
                },
            )

        assert response.status_code == 500
        assert response.json() == {
            "error": "search_error",
            "message": "",
        }
        search_mock.assert_awaited_once_with(
            query="test query",
            search_type="vector",
            limit=10,
        )

    async def test_search_raises_invalid_state_for_non_dict_workflow_result(
        self,
        client: AsyncClient,
    ):
        """Test malformed workflow state is translated to SearchError response."""
        with patch(
            "src.api.routes.search.search",
            new=AsyncMock(return_value=None),
        ) as search_mock:
            response = await client.post(
                "/api/search/",
                json={
                    "query": "test query",
                    "search_type": "hybrid",
                    "limit": 10,
                },
            )

        assert response.status_code == 500
        assert response.json() == {
            "error": "search_error",
            "message": "Search workflow returned invalid state",
        }
        search_mock.assert_awaited_once_with(
            query="test query",
            search_type="hybrid",
            limit=10,
        )

    async def test_search_error_is_passed_through(self, client: AsyncClient):
        """Test SearchError raised by workflow is returned unchanged."""
        with patch(
            "src.api.routes.search.search",
            new=AsyncMock(side_effect=SearchError("pipeline failure")),
        ) as search_mock:
            response = await client.post(
                "/api/search/",
                json={
                    "query": "test query",
                    "search_type": "hybrid",
                    "limit": 10,
                },
            )

        assert response.status_code == 500
        assert response.json() == {
            "error": "search_error",
            "message": "pipeline failure",
        }
        search_mock.assert_awaited_once_with(
            query="test query",
            search_type="hybrid",
            limit=10,
        )

    async def test_search_unexpected_exception_returns_500(self, client: AsyncClient):
        """Test unexpected workflow exception is handled as SearchError."""
        with patch(
            "src.api.routes.search.search",
            new=AsyncMock(side_effect=RuntimeError("connection lost")),
        ):
            response = await client.post(
                "/api/search/",
                json={
                    "query": "test query",
                    "search_type": "hybrid",
                    "limit": 10,
                },
            )

        assert response.status_code == 500
        assert response.json() == {
            "error": "search_error",
            "message": "connection lost",
        }


class TestSearchValidation:
    """Test request validation returns 422 for invalid payloads."""

    async def test_empty_query_returns_422(self, client: AsyncClient):
        response = await client.post("/api/search/", json={"query": ""})
        assert response.status_code == 422
        errors = _assert_validation_error_payload(response.json())
        assert errors[0]["loc"][-1] == "query"

    async def test_whitespace_only_query_returns_422(self, client: AsyncClient):
        response = await client.post("/api/search/", json={"query": "   "})
        assert response.status_code == 422
        _assert_validation_error_payload(response.json())

    async def test_missing_query_returns_422(self, client: AsyncClient):
        response = await client.post("/api/search/", json={})
        assert response.status_code == 422
        errors = _assert_validation_error_payload(response.json())
        assert errors[0]["loc"][-1] == "query"

    async def test_invalid_search_type_returns_422(self, client: AsyncClient):
        response = await client.post(
            "/api/search/", json={"query": "test", "search_type": "keyword"}
        )
        assert response.status_code == 422
        errors = _assert_validation_error_payload(response.json())
        assert errors[0]["loc"][-1] == "search_type"

    async def test_limit_below_minimum_returns_422(self, client: AsyncClient):
        response = await client.post("/api/search/", json={"query": "test", "limit": 0})
        assert response.status_code == 422
        errors = _assert_validation_error_payload(response.json())
        assert errors[0]["loc"][-1] == "limit"

    async def test_limit_above_maximum_returns_422(self, client: AsyncClient):
        response = await client.post(
            "/api/search/", json={"query": "test", "limit": 101}
        )
        assert response.status_code == 422
        errors = _assert_validation_error_payload(response.json())
        assert errors[0]["loc"][-1] == "limit"

    async def test_extra_fields_returns_422(self, client: AsyncClient):
        response = await client.post(
            "/api/search/", json={"query": "test", "unknown_field": "value"}
        )
        assert response.status_code == 422
        errors = _assert_validation_error_payload(response.json())
        assert any(error["loc"][-1] == "unknown_field" for error in errors)
