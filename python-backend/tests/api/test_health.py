"""Tests for health check endpoint."""

from datetime import datetime

from httpx import AsyncClient
from src.api.dependencies import get_db_connection, get_ollama_provider
from src.main import app


class TestHealthEndpoint:
    """Tests for GET /api/health endpoint."""

    async def test_health_endpoint_success(self, client: AsyncClient):
        """Test health endpoint returns 200 with healthy status when database is available."""
        response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["checks"]["database"]["status"] == "healthy"
        assert data["checks"]["database"]["latency_ms"] is not None
        assert data["checks"]["database"]["latency_ms"] >= 0

    async def test_health_response_structure(self, client: AsyncClient):
        """Test health response contains all required fields."""
        response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert "checks" in data

        # Verify checks structure
        assert "database" in data["checks"]
        assert "status" in data["checks"]["database"]

    async def test_health_response_types(self, client: AsyncClient):
        """Test health response field types match expected types."""
        response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        # Verify types
        assert isinstance(data["status"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["checks"], dict)
        assert isinstance(data["checks"]["database"], dict)
        assert isinstance(data["checks"]["database"]["status"], str)

        # latency_ms should be int when healthy
        if data["checks"]["database"]["status"] == "healthy":
            assert isinstance(data["checks"]["database"]["latency_ms"], int)

    async def test_health_timestamp_format(self, client: AsyncClient):
        """Test health response timestamp is valid ISO 8601 format."""
        response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        # Should parse without error
        timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        assert timestamp is not None

    async def test_health_version_present(self, client: AsyncClient):
        """Test health response includes a version string."""
        response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        # Version should be a non-empty string
        assert len(data["version"]) > 0


class TestHealthEndpointFailure:
    """Tests for health endpoint failure scenarios."""

    async def test_health_endpoint_db_failure(self, client: AsyncClient):
        """Test health endpoint returns 503 when database is unavailable."""

        class MockFailingConnection:
            async def execute(self, query):
                raise Exception("Database connection failed")

        async def mock_get_db_connection():
            yield MockFailingConnection()

        class MockFailingOllamaProvider:
            async def is_available(self):
                return False

        async def mock_get_ollama_provider():
            yield MockFailingOllamaProvider()

        app.dependency_overrides[get_db_connection] = mock_get_db_connection
        app.dependency_overrides[get_ollama_provider] = mock_get_ollama_provider
        try:
            response = await client.get("/api/health")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["checks"]["database"]["status"] == "unhealthy"
            assert data["checks"]["database"]["error"] is not None
        finally:
            app.dependency_overrides.clear()

    async def test_health_endpoint_db_failure_has_error_message(
        self, client: AsyncClient
    ):
        """Test unhealthy response includes error details."""

        class MockFailingConnection:
            async def execute(self, query):
                raise Exception("Connection refused")

        async def mock_get_db_connection():
            yield MockFailingConnection()

        app.dependency_overrides[get_db_connection] = mock_get_db_connection
        try:
            response = await client.get("/api/health")

            data = response.json()
            assert "Connection refused" in data["checks"]["database"]["error"]
        finally:
            app.dependency_overrides.clear()
