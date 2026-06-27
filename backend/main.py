"""
CrimePatrol — FastAPI Application Entrypoint
Wires together: middleware, routers, exception handlers,
startup/shutdown lifecycle (DB pool, Redis, scheduler).
"""
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.core.config import get_settings
from backend.core.exceptions import (
    AuthenticationError,
    CrimePatrolError,
    DatabaseError,
    DomainError,
    ExternalAPIError,
)
from backend.core.middleware import register_middleware
from backend.core.observability.logger import configure_logging, get_logger
from backend.infrastructure.database.connection import close_db, init_db
from backend.infrastructure.cache.redis_client import close_redis, init_redis

logger = get_logger(__name__)
settings = get_settings()


# =============================================================================
# Lifespan (replaces @app.on_event deprecated pattern)
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    # ── Startup ──────────────────────────────────────────────────────────────
    configure_logging()
    logger.info("crimepatrol_starting", env=settings.app_env, city=settings.city_name)

    await init_db()
    logger.info("database_pool_ready")

    await init_redis()
    logger.info("redis_connected")

    _register_scheduler(app)
    logger.info("scheduler_started")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("crimepatrol_shutting_down")
    app.state.scheduler.shutdown(wait=False)
    await close_redis()
    await close_db()


def _register_scheduler(app: FastAPI) -> None:
    from backend.core.scheduler.apscheduler_impl import APSchedulerBackend
    from backend.application.run_etl_pipeline import run_etl_pipeline
    from backend.application.trigger_monitoring import trigger_monitoring
    from backend.application.generate_report import generate_daily_report

    scheduler = APSchedulerBackend()
    scheduler.schedule_job(run_etl_pipeline, settings.etl_cron, "etl_pipeline")
    scheduler.schedule_job(trigger_monitoring, settings.monitoring_cron, "model_monitoring")
    scheduler.schedule_job(generate_daily_report, settings.daily_report_cron, "daily_report")
    scheduler.start()
    app.state.scheduler = scheduler


# =============================================================================
# FastAPI App
# =============================================================================

def create_app() -> FastAPI:
    _app = FastAPI(
        title="CrimePatrol API",
        description=(
            "AI-Powered Smart City Safety Analytics Platform. "
            "Predicts crime risk for geographic areas and time windows."
        ),
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Middleware
    register_middleware(_app)

    # Routers
    _register_routers(_app)

    # Exception handlers
    _register_exception_handlers(_app)

    return _app


def _register_routers(app: FastAPI) -> None:
    from backend.api.v1.controllers import (
        auth,
        health,
        areas,
        incidents,
        predictions,
        analytics,
        agents,
        reports,
        quality,
    )
    from backend.api.v1.websockets import dashboard

    prefix = "/api/v1"
    app.include_router(auth.router,        prefix=prefix, tags=["Authentication"])
    app.include_router(health.router,      prefix="",     tags=["Health"])
    app.include_router(areas.router,       prefix=prefix, tags=["Areas"])
    app.include_router(incidents.router,   prefix=prefix, tags=["Incidents"])
    app.include_router(predictions.router, prefix=prefix, tags=["Predictions"])
    app.include_router(analytics.router,   prefix=prefix, tags=["Analytics"])
    app.include_router(agents.router,      prefix=prefix, tags=["Agents"])
    app.include_router(reports.router,     prefix=prefix, tags=["Reports"])
    app.include_router(quality.router,     prefix=prefix, tags=["Data Quality"])
    app.include_router(dashboard.router,   prefix="",     tags=["WebSocket"])


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
        return JSONResponse(status_code=401, content=_error_body(exc.message))

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=422, content=_error_body(exc.message, exc.details))

    @app.exception_handler(DatabaseError)
    async def db_error_handler(request: Request, exc: DatabaseError) -> JSONResponse:
        logger.error("database_error", error=exc.message)
        return JSONResponse(status_code=503, content=_error_body("Database temporarily unavailable."))

    @app.exception_handler(ExternalAPIError)
    async def api_error_handler(request: Request, exc: ExternalAPIError) -> JSONResponse:
        logger.warning("external_api_error", provider=exc.provider, error=exc.message)
        return JSONResponse(status_code=502, content=_error_body(f"External service error: {exc.provider}"))

    @app.exception_handler(CrimePatrolError)
    async def generic_error_handler(request: Request, exc: CrimePatrolError) -> JSONResponse:
        logger.error("unhandled_app_error", error=exc.message)
        return JSONResponse(status_code=500, content=_error_body("Internal server error."))


def _error_body(message: str, details: Any = None) -> dict[str, Any]:
    return {"success": False, "data": None, "errors": [{"message": message, "details": details}]}


app = create_app()
