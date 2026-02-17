"""Tests for FastAPI exception handler registration."""

import json

from src.exceptions import SearchError
from src.main import app, search_error_handler
from starlette.requests import Request


class TestSearchErrorHandler:
    """Validate SearchError handler wiring and response contract."""

    async def test_search_error_handler_registered(self):
        assert SearchError in app.exception_handlers
        assert app.exception_handlers[SearchError] is search_error_handler

    async def test_search_error_handler_response(self):
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/search",
                "headers": [],
                "query_string": b"",
            }
        )

        response = await search_error_handler(
            request,
            SearchError("search failed at rerank", query="test query", step="rerank"),
        )

        assert response.status_code == 500
        assert json.loads(response.body) == {
            "error": "search_error",
            "message": "search failed at rerank",
        }
