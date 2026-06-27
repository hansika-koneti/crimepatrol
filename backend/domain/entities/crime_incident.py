"""
CrimePatrol Domain — CrimeIncident Entity
Pure dataclass — no ORM, no framework dependencies.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID


class DataSource(str, Enum):
    HISTORICAL_CSV = "historical_csv"
    SCRAPER = "scraper"
    API = "api"
    MANUAL = "manual"


@dataclass
class GeoPoint:
    """WGS-84 geographic coordinate."""
    longitude: float
    latitude: float

    def __post_init__(self) -> None:
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(f"Invalid longitude: {self.longitude}")
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"Invalid latitude: {self.latitude}")


@dataclass
class CrimeIncident:
    """
    Represents a single crime incident.
    This is the canonical domain object — used throughout business logic.
    ORM models and API schemas map to/from this entity.
    """
    id: UUID
    crime_type: str
    crime_category: str
    location: GeoPoint
    occurred_at: datetime
    source: DataSource
    city: str

    # Optional fields
    area_id: UUID | None = None
    severity: int | None = None          # 1–5
    address: str | None = None
    reported_at: datetime | None = None
    source_url: str | None = None
    source_id: str | None = None         # original ID from source
    raw_text: str | None = None
    is_verified: bool = False
    is_duplicate: bool = False
    metadata: dict = field(default_factory=dict)
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.crime_type.strip():
            raise ValueError("crime_type cannot be empty.")
        if self.severity is not None and self.severity not in range(1, 6):
            raise ValueError(f"severity must be 1–5, got {self.severity}.")
