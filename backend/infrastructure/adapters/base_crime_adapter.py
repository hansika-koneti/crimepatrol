"""
CrimePatrol — Base Crime Data Adapter (Abstract)
All city-specific adapters must implement this interface.
Switching cities = changing CITY_ADAPTER env var. Zero core changes.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawIncidentRecord:
    """
    Normalized incident record produced by any city adapter.
    The ETL pipeline converts this to a CrimeIncident domain entity.
    """
    source_id: str                 # original ID from the source system
    crime_type: str
    crime_category: str
    longitude: float
    latitude: float
    occurred_at: datetime
    address: str | None = None
    severity: int | None = None    # 1–5, adapter-inferred if not native
    raw_text: str | None = None
    source_url: str | None = None
    extra: dict | None = None      # adapter-specific fields preserved for ML


class BaseCrimeAdapter(ABC):
    """
    Abstract base for city crime data adapters.

    Each city adapter fetches, normalizes, and returns RawIncidentRecords.
    Adapters are responsible only for fetching and normalizing.
    Cleaning, deduplication, and saving are handled by the ETL pipeline.

    Environment variable CITY_ADAPTER selects the concrete class:
      'chicago'     → ChicagoCrimeAdapter
      'generic_csv' → GenericCSVAdapter
    """

    @property
    @abstractmethod
    def city_name(self) -> str:
        """Human-readable city name (e.g. 'Chicago')."""
        ...

    @property
    @abstractmethod
    def country_code(self) -> str:
        """ISO 3166-1 alpha-2 country code (e.g. 'US')."""
        ...

    @abstractmethod
    async def fetch_recent(
        self,
        hours_back: int = 24,
        limit: int = 1000,
    ) -> list[RawIncidentRecord]:
        """
        Fetch recent incidents from the source.
        Used by the hourly ETL job.
        """
        ...

    @abstractmethod
    async def fetch_historical(
        self,
        start: datetime,
        end: datetime,
        limit: int = 50_000,
    ) -> list[RawIncidentRecord]:
        """
        Fetch historical incidents for a date range.
        Used for initial data load and ML training set assembly.
        """
        ...

    def infer_severity(self, crime_type: str) -> int:
        """
        Map a crime type string to a severity score (1–5).
        Override in city adapters if the source provides native severity.
        """
        crime_type_lower = crime_type.lower()
        if any(k in crime_type_lower for k in ("homicide", "murder", "shooting")):
            return 5
        if any(k in crime_type_lower for k in ("assault", "robbery", "arson", "kidnap")):
            return 4
        if any(k in crime_type_lower for k in ("burglary", "battery", "sex offense")):
            return 3
        if any(k in crime_type_lower for k in ("theft", "motor vehicle", "vandalism")):
            return 2
        return 1

    def normalize_crime_category(self, crime_type: str) -> str:
        """
        Collapse crime types into broad categories for ML features.
        Override to add city-specific mappings.
        """
        t = crime_type.lower()
        if any(k in t for k in ("theft", "burglary", "robbery", "motor vehicle")):
            return "theft"
        if any(k in t for k in ("assault", "battery", "homicide", "shooting")):
            return "violent"
        if any(k in t for k in ("vandalism", "criminal damage")):
            return "property_damage"
        if any(k in t for k in ("narcotics", "drug")):
            return "narcotics"
        if any(k in t for k in ("sex", "rape", "prostitution")):
            return "sex_offense"
        if any(k in t for k in ("fraud", "deceptive")):
            return "fraud"
        return "other"
