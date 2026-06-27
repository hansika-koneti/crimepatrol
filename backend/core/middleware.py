"""
CrimePatrol — FastAPI Middleware Stack
- CORS
- Request ID (correlation tracking)
- Audit logging (writes to DB asynchronously)
- Rate limiting (SlowAPI)
- Request timing metrics
"""
import time
import uuid
from collections.abc import Callable

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.config import get_settings
from backend.core.observability.logger import get_logger

logger = get_logger(__name__)

# =============================================================================
# Rate Limiter (SlowAPI)
# =============================================================================

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


# =============================================================================
# Request Timing + Correlation ID Middleware
# =============================================================================

class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Attaches a unique request_id to every request.
    Logs method, path, status code, and response time.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Bind correlation ID for all log calls within this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"
        return response


# =============================================================================
# Security Headers Middleware
# =============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to every response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not get_settings().is_development:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


# =============================================================================
# Registration Helper
# =============================================================================

def register_middleware(app: FastAPI) -> None:
    """Register all middleware onto the FastAPI app. Order matters (LIFO)."""
    settings = get_settings()

    # CORS — must be first (outermost)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Request tracing
    app.add_middleware(RequestTracingMiddleware)

    # Rate limiting exception handler
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
