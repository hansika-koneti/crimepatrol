"""
CrimePatrol — Shared Test Fixtures
Provides: async test client, mock settings, in-memory SQLite session.
"""
import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

# ── Override settings before any app import ─────────────────────────────────
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-ci-32chars--")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("TOMTOM_API_KEY", "")
os.environ.setdefault("TICKETMASTER_API_KEY", "")
os.environ.setdefault("CITY_ADAPTER", "chicago")
os.environ.setdefault("CITY_NAME", "Chicago")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.com")
os.environ.setdefault("ADMIN_PASSWORD", "TestPass123!")


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Single event loop for the entire session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db_session() -> MagicMock:
    """A mock async SQLAlchemy session."""
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_redis() -> MagicMock:
    """A mock async Redis client."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.ping = AsyncMock(return_value=True)
    return redis


@pytest_asyncio.fixture
async def minimal_app() -> FastAPI:
    """
    A minimal FastAPI app with only the health router mounted.
    No DB, no Redis — suitable for health-endpoint tests.
    """
    from fastapi import FastAPI
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "test"}

    return app


@pytest_asyncio.fixture
async def client(minimal_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Async test client for the minimal app."""
    transport = ASGITransport(app=minimal_app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
