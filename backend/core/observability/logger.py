"""
CrimePatrol — Structured JSON Logging
Uses structlog for machine-readable logs in production and
human-friendly colored logs in development.
"""
import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from backend.core.config import get_settings


def _add_severity(
    logger: Any, method: str, event_dict: EventDict
) -> EventDict:
    """Map structlog level names to Google Cloud Logging severity."""
    level = event_dict.get("level", method).upper()
    event_dict["severity"] = level
    return event_dict


def _drop_color_message_key(
    logger: Any, method: str, event_dict: EventDict
) -> EventDict:
    """Remove uvicorn's color_message key from logs."""
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog + stdlib logging.
    Call once at application startup.
    """
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        _add_severity,
        _drop_color_message_key,
    ]

    if settings.log_format == "json":
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Silence noisy libraries in production
    for name in ("uvicorn.access", "sqlalchemy.engine", "scrapy"):
        level = logging.WARNING if settings.is_production else log_level
        logging.getLogger(name).setLevel(level)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a named structlog logger. Import and use this everywhere."""
    return structlog.get_logger(name)
