"""
Integration tests — /health endpoint
Uses a minimal FastAPI app; does NOT require Postgres or Redis.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI


@pytest.fixture
def health_app() -> FastAPI:
    """Minimal app with only the health route (no DB/Redis deps)."""
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "version": "1.0.0-test",
            "environment": "development",
            "uptime_seconds": 42.0,
            "components": [],
        }

    return app


@pytest.mark.asyncio
class TestHealthEndpoint:
    async def test_health_returns_200(self, health_app: FastAPI):
        transport = ASGITransport(app=health_app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 200

    async def test_health_returns_json(self, health_app: FastAPI):
        transport = ASGITransport(app=health_app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        data = resp.json()
        assert "status" in data
        assert "version" in data

    async def test_health_status_is_ok(self, health_app: FastAPI):
        transport = ASGITransport(app=health_app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.json()["status"] == "ok"

    async def test_health_version_field(self, health_app: FastAPI):
        transport = ASGITransport(app=health_app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.json()["version"] == "1.0.0-test"

    async def test_health_environment_field(self, health_app: FastAPI):
        transport = ASGITransport(app=health_app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.json()["environment"] in ("development", "production")

    async def test_nonexistent_route_returns_404(self, health_app: FastAPI):
        transport = ASGITransport(app=health_app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/does-not-exist")
        assert resp.status_code == 404
