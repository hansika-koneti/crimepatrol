"""
CrimePatrol — Health Check Service
Checks: application, database, Redis, ML model, external APIs.
"""
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ComponentStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass
class ComponentHealth:
    name: str
    status: ComponentStatus
    latency_ms: float | None = None
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class SystemHealth:
    status: ComponentStatus          # worst-case aggregate
    version: str
    environment: str
    uptime_seconds: float
    components: list[ComponentHealth] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "version": self.version,
            "environment": self.environment,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "components": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "latency_ms": c.latency_ms,
                    "details": c.details,
                    "error": c.error,
                }
                for c in self.components
            ],
        }


# Module-level startup timestamp
_startup_time: float = time.time()

APP_VERSION = "1.0.0"


def get_uptime() -> float:
    return time.time() - _startup_time


async def check_database(db_session_factory: Any) -> ComponentHealth:
    """Ping the PostgreSQL connection pool."""
    start = time.perf_counter()
    try:
        async with db_session_factory() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return ComponentHealth(
            name="postgresql",
            status=ComponentStatus.OK,
            latency_ms=latency_ms,
        )
    except Exception as exc:
        return ComponentHealth(
            name="postgresql",
            status=ComponentStatus.DOWN,
            error=str(exc),
        )


async def check_redis(redis_client: Any) -> ComponentHealth:
    """Ping the Redis connection."""
    start = time.perf_counter()
    try:
        await redis_client.ping()
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return ComponentHealth(
            name="redis",
            status=ComponentStatus.OK,
            latency_ms=latency_ms,
        )
    except Exception as exc:
        return ComponentHealth(
            name="redis",
            status=ComponentStatus.DEGRADED,  # degraded, not down — caching is optional
            error=str(exc),
        )


def check_ml_model(model_registry_path: str) -> ComponentHealth:
    """Check if an active model file exists."""
    import os
    from pathlib import Path

    registry = Path(model_registry_path)
    model_files = list(registry.glob("**/model.pkl")) if registry.exists() else []
    if model_files:
        latest = max(model_files, key=lambda p: p.stat().st_mtime)
        return ComponentHealth(
            name="ml_model",
            status=ComponentStatus.OK,
            details={"active_model": str(latest.parent.name)},
        )
    return ComponentHealth(
        name="ml_model",
        status=ComponentStatus.DEGRADED,
        error="No trained model found. Run training pipeline.",
    )


def aggregate_status(components: list[ComponentHealth]) -> ComponentStatus:
    statuses = {c.status for c in components}
    if ComponentStatus.DOWN in statuses:
        return ComponentStatus.DOWN
    if ComponentStatus.DEGRADED in statuses:
        return ComponentStatus.DEGRADED
    return ComponentStatus.OK
