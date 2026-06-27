"""
CrimePatrol Domain — Area Entity
"""
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class BoundingBox:
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    def contains(self, lon: float, lat: float) -> bool:
        return (
            self.min_lon <= lon <= self.max_lon
            and self.min_lat <= lat <= self.max_lat
        )


@dataclass
class Area:
    """A geographic monitoring zone (neighborhood, district, community area)."""
    id: UUID
    name: str
    city: str
    country_code: str = "US"
    population: int | None = None
    area_km2: float | None = None
    district_code: str | None = None
    centroid_lon: float | None = None
    centroid_lat: float | None = None
    metadata: dict = field(default_factory=dict)
    created_at: datetime | None = None

    @property
    def centroid(self) -> tuple[float, float] | None:
        if self.centroid_lon and self.centroid_lat:
            return (self.centroid_lon, self.centroid_lat)
        return None

    @property
    def population_density(self) -> float | None:
        """People per km²."""
        if self.population and self.area_km2 and self.area_km2 > 0:
            return round(self.population / self.area_km2, 2)
        return None
