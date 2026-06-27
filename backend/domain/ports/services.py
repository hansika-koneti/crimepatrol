"""
CrimePatrol Domain — External Service Ports
Abstract interfaces for weather, traffic, events, holidays, IoT.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


# =============================================================================
# Weather Port
# =============================================================================

@dataclass
class WeatherSnapshot:
    area_id: UUID
    recorded_at: datetime
    temperature_c: float
    feels_like_c: float
    humidity_pct: int
    condition: str           # 'clear' | 'rain' | 'storm' | 'fog' | 'snow'
    wind_kmh: float
    visibility_km: float
    precipitation_mm: float
    uv_index: int


class WeatherServicePort(ABC):
    @abstractmethod
    async def get_current(self, lat: float, lon: float, area_id: UUID) -> WeatherSnapshot: ...

    @abstractmethod
    async def get_forecast(
        self, lat: float, lon: float, area_id: UUID, hours_ahead: int = 24
    ) -> list[WeatherSnapshot]: ...


# =============================================================================
# Traffic Port
# =============================================================================

@dataclass
class TrafficSnapshot:
    area_id: UUID
    recorded_at: datetime
    congestion_pct: int      # 0–100
    incident_count: int
    flow_speed_kmh: float
    free_flow_speed: float
    road_closures: int


class TrafficServicePort(ABC):
    @abstractmethod
    async def get_flow(
        self, lat: float, lon: float, area_id: UUID, radius_km: float = 1.0
    ) -> TrafficSnapshot: ...


# =============================================================================
# Events Port
# =============================================================================

@dataclass
class PublicEvent:
    area_id: UUID | None
    city: str
    name: str
    category: str            # 'concert' | 'sports' | 'festival' | 'protest'
    venue: str | None
    expected_crowd: int | None
    crowd_bucket: str        # 'small' | 'medium' | 'large' | 'massive'
    location_lon: float | None
    location_lat: float | None
    starts_at: datetime
    ends_at: datetime
    source: str
    source_id: str | None = None


class EventsServicePort(ABC):
    @abstractmethod
    async def get_events(
        self, city: str, lat: float, lon: float, radius_km: float, date_from: datetime
    ) -> list[PublicEvent]: ...


# =============================================================================
# Holidays Port
# =============================================================================

@dataclass
class Holiday:
    name: str
    date: date
    country_code: str
    is_public: bool


class HolidayServicePort(ABC):
    @abstractmethod
    async def get_holidays(self, country_code: str, year: int) -> list[Holiday]: ...

    @abstractmethod
    def is_holiday(self, check_date: date, holidays: list[Holiday]) -> bool: ...


# =============================================================================
# IoT Port (simulated smart city infrastructure)
# =============================================================================

@dataclass
class IoTSnapshot:
    area_id: UUID
    recorded_at: datetime
    streetlight_pct: int      # % of streetlights operational
    cctv_alert_count: int
    cctv_operational: int
    crowd_density: float      # people per 100m²
    anomaly_detected: bool


class IoTServicePort(ABC):
    @abstractmethod
    async def get_snapshot(self, area_id: UUID) -> IoTSnapshot: ...
