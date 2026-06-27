"""
CrimePatrol — Async SQLAlchemy Engine + Session Factory
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.core.config import get_settings
from backend.core.observability.logger import get_logger

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


async def init_db() -> None:
    """Create the async engine and session factory. Call once at startup."""
    global _engine, _session_factory
    settings = get_settings()

    _engine = create_async_engine(
        settings.database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,             # detect stale connections
        pool_recycle=3600,              # recycle connections hourly
        echo=settings.is_development,  # SQL logging in dev only
    )
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,         # keep objects usable after commit
        autoflush=False,
    )
    logger.info("database_engine_created", url=settings.postgres_host)


async def close_db() -> None:
    """Dispose the engine. Call at shutdown."""
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("database_engine_disposed")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session.
    Automatically commits on success, rolls back on exception.

    Usage::
        async def endpoint(session: AsyncSession = Depends(get_session)):
            ...
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory (for health checks, schedulers)."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized.")
    return _session_factory
