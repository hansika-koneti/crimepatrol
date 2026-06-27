"""
CrimePatrol — Custom Exception Hierarchy
All application exceptions inherit from CrimePatrolError.
FastAPI exception handlers are registered in main.py.
"""
from typing import Any


class CrimePatrolError(Exception):
    """Base exception for all CrimePatrol errors."""

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


# =============================================================================
# Domain Exceptions
# =============================================================================

class DomainError(CrimePatrolError):
    """Raised when a domain rule is violated."""


class InvalidCoordinatesError(DomainError):
    """Coordinates outside the configured city bounding box."""


class InvalidTimeWindowError(DomainError):
    """Time window is invalid (e.g. start > end, future date without flag)."""


class AreaNotFoundError(DomainError):
    """Requested geographic area does not exist."""


class PredictionNotFoundError(DomainError):
    """Prediction record not found."""


class IncidentNotFoundError(DomainError):
    """Crime incident record not found."""


# =============================================================================
# Application Exceptions
# =============================================================================

class ApplicationError(CrimePatrolError):
    """Raised by application-layer use cases."""


class AgentOrchestrationError(ApplicationError):
    """LangGraph agent pipeline failed."""


class ETLPipelineError(ApplicationError):
    """ETL pipeline encountered an unrecoverable error."""


class FeatureEngineeringError(ApplicationError):
    """Feature vector could not be assembled."""


class ModelNotAvailableError(ApplicationError):
    """No trained model is available for inference."""


class ReportGenerationError(ApplicationError):
    """Daily briefing or report generation failed."""


# =============================================================================
# Infrastructure Exceptions
# =============================================================================

class InfrastructureError(CrimePatrolError):
    """Base for all infrastructure / I-O errors."""


class DatabaseError(InfrastructureError):
    """Database operation failed."""


class ExternalAPIError(InfrastructureError):
    """External API call failed (weather, traffic, events, etc.)."""

    def __init__(self, message: str, provider: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code


class ScraperError(InfrastructureError):
    """Web scraper encountered an error."""

    def __init__(self, message: str, url: str | None = None) -> None:
        super().__init__(message)
        self.url = url


class RateLimitExceededError(InfrastructureError):
    """External API rate limit hit."""


class DataFreshnessError(InfrastructureError):
    """Data source is stale beyond acceptable threshold."""


class IoTSimulationError(InfrastructureError):
    """Simulated IoT endpoint returned unexpected data."""


# =============================================================================
# Security Exceptions
# =============================================================================

class AuthenticationError(CrimePatrolError):
    """Invalid credentials or expired token."""


class TokenExpiredError(AuthenticationError):
    """JWT access token has expired."""


class InvalidTokenError(AuthenticationError):
    """JWT token is malformed or has invalid signature."""


# =============================================================================
# Data Quality Exceptions
# =============================================================================

class DataQualityError(CrimePatrolError):
    """Data quality check failed below acceptable threshold."""

    def __init__(self, message: str, quality_score: float) -> None:
        super().__init__(message)
        self.quality_score = quality_score


class DuplicateRecordError(DataQualityError):
    """Attempted to insert a duplicate record."""

    def __init__(self, source: str, source_id: str) -> None:
        super().__init__(f"Duplicate record: {source}/{source_id}", quality_score=0.0)
        self.source = source
        self.source_id = source_id
