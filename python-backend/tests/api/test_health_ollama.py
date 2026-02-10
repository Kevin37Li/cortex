"""Tests for Ollama health check endpoints."""

from unittest.mock import AsyncMock

from httpx import AsyncClient
from src.api.dependencies import get_db_connection, get_ollama_provider
from src.main import app
from src.providers.models import ModelInfo


class TestHealthEndpointWithOllama:
    """Tests for GET /api/health endpoint with Ollama component."""

    async def test_health_includes_ollama_check(
        self, client: AsyncClient, mock_ollama_provider
    ):
        """Test health endpoint includes Ollama in component checks."""
        mock_ollama_provider.is_available = AsyncMock(return_value=True)

        async def mock_get_ollama():
            yield mock_ollama_provider

        app.dependency_overrides[get_ollama_provider] = mock_get_ollama
        try:
            response = await client.get("/api/health")

            assert response.status_code == 200
            data = response.json()
            assert "ollama" in data["checks"]
            assert data["checks"]["ollama"]["status"] == "healthy"
            assert data["checks"]["ollama"]["latency_ms"] is not None
        finally:
            app.dependency_overrides.clear()

    async def test_health_degraded_when_ollama_unavailable(
        self, client: AsyncClient, mock_ollama_provider
    ):
        """Test health returns degraded status when Ollama is unavailable but DB is healthy."""
        mock_ollama_provider.is_available = AsyncMock(return_value=False)

        async def mock_get_ollama():
            yield mock_ollama_provider

        app.dependency_overrides[get_ollama_provider] = mock_get_ollama
        try:
            response = await client.get("/api/health")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "degraded"
            assert data["checks"]["database"]["status"] == "healthy"
            assert data["checks"]["ollama"]["status"] == "unhealthy"
        finally:
            app.dependency_overrides.clear()

    async def test_health_unhealthy_when_all_components_fail(
        self, client: AsyncClient, mock_ollama_provider
    ):
        """Test health returns unhealthy when all components fail."""
        mock_ollama_provider.is_available = AsyncMock(return_value=False)

        async def mock_get_ollama():
            yield mock_ollama_provider

        class MockFailingConnection:
            async def execute(self, query):
                raise Exception("Database connection failed")

        async def mock_get_db():
            yield MockFailingConnection()

        app.dependency_overrides[get_ollama_provider] = mock_get_ollama
        app.dependency_overrides[get_db_connection] = mock_get_db
        try:
            response = await client.get("/api/health")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["checks"]["database"]["status"] == "unhealthy"
            assert data["checks"]["ollama"]["status"] == "unhealthy"
        finally:
            app.dependency_overrides.clear()


class TestOllamaHealthEndpoint:
    """Tests for GET /api/health/ollama dedicated endpoint."""

    async def test_ollama_health_when_available(
        self, client: AsyncClient, mock_ollama_provider
    ):
        """Test dedicated Ollama health endpoint returns healthy with models."""
        mock_models = [
            ModelInfo(name="llama3.2:3b", size=1234567890),
            ModelInfo(name="nomic-embed-text", size=987654321),
        ]
        mock_ollama_provider.list_models = AsyncMock(return_value=mock_models)

        async def mock_get_ollama():
            yield mock_ollama_provider

        app.dependency_overrides[get_ollama_provider] = mock_get_ollama
        try:
            response = await client.get("/api/health/ollama")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["base_url"] == "http://localhost:11434"
            assert data["models"] == ["llama3.2:3b", "nomic-embed-text"]
            assert data["latency_ms"] is not None
            assert data["error"] is None
        finally:
            app.dependency_overrides.clear()

    async def test_ollama_health_when_unavailable(
        self, client: AsyncClient, mock_ollama_provider
    ):
        """Test dedicated Ollama health endpoint returns unavailable with error."""
        mock_ollama_provider.list_models = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        async def mock_get_ollama():
            yield mock_ollama_provider

        app.dependency_overrides[get_ollama_provider] = mock_get_ollama
        try:
            response = await client.get("/api/health/ollama")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unavailable"
            assert data["base_url"] == "http://localhost:11434"
            assert data["models"] is None
            assert data["error"] == "Connection refused"
        finally:
            app.dependency_overrides.clear()

    async def test_ollama_health_response_structure(
        self, client: AsyncClient, mock_ollama_provider
    ):
        """Test Ollama health response contains all required fields."""
        mock_ollama_provider.list_models = AsyncMock(return_value=[])

        async def mock_get_ollama():
            yield mock_ollama_provider

        app.dependency_overrides[get_ollama_provider] = mock_get_ollama
        try:
            response = await client.get("/api/health/ollama")

            assert response.status_code == 200
            data = response.json()

            # Verify all required fields are present
            assert "status" in data
            assert "base_url" in data
            assert "models" in data
            assert "error" in data
            assert "latency_ms" in data
        finally:
            app.dependency_overrides.clear()

    async def test_ollama_health_empty_models_list(
        self, client: AsyncClient, mock_ollama_provider
    ):
        """Test Ollama health endpoint handles empty models list."""
        mock_ollama_provider.list_models = AsyncMock(return_value=[])

        async def mock_get_ollama():
            yield mock_ollama_provider

        app.dependency_overrides[get_ollama_provider] = mock_get_ollama
        try:
            response = await client.get("/api/health/ollama")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["models"] == []
        finally:
            app.dependency_overrides.clear()
