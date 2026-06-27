"""
CrimePatrol Domain — Repository Ports (Abstract Interfaces)
Concrete implementations live in infrastructure/database/repositories/.
Business logic depends ONLY on these abstractions.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from backend.domain.entities.area import Area
from backend.domain.entities.crime_incident import CrimeIncident
from backend.domain.entities.prediction import Prediction
from backend.domain.entities.recommendation import Recommendation
from backend.domain.entities.risk_level import RiskLevel


class CrimeIncidentRepository(ABC):
    """Port for crime incident persistence."""

    @abstractmethod
    async def save(self, incident: CrimeIncident) -> CrimeIncident: ...

    @abstractmethod
    async def save_batch(self, incidents: list[CrimeIncident]) -> int:
        """Returns number of records saved (duplicates excluded)."""
        ...

    @abstractmethod
    async def find_by_id(self, incident_id: UUID) -> CrimeIncident | None: ...

    @abstractmethod
    async def find_by_area_and_window(
        self,
        area_id: UUID,
        start: datetime,
        end: datetime,
        crime_category: str | None = None,
    ) -> list[CrimeIncident]: ...

    @abstractmethod
    async def count_by_area_and_window(
        self, area_id: UUID, start: datetime, end: datetime
    ) -> int: ...

    @abstractmethod
    async def find_recent_by_city(
        self, city: str, limit: int = 50
    ) -> list[CrimeIncident]: ...

    @abstractmethod
    async def exists_by_source(self, source: str, source_id: str) -> bool: ...


class PredictionRepository(ABC):
    """Port for prediction persistence."""

    @abstractmethod
    async def save(self, prediction: Prediction) -> Prediction: ...

    @abstractmethod
    async def find_by_id(self, prediction_id: UUID) -> Prediction | None: ...

    @abstractmethod
    async def find_latest_by_area(self, area_id: UUID) -> Prediction | None: ...

    @abstractmethod
    async def find_history(
        self,
        area_id: UUID | None = None,
        risk_level: RiskLevel | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Prediction]: ...

    @abstractmethod
    async def find_high_risk_areas(
        self,
        city: str,
        window_start: datetime,
        top_n: int = 10,
    ) -> list[Prediction]: ...

    @abstractmethod
    async def find_similar(
        self,
        feature_vector: dict,
        top_k: int = 5,
    ) -> list[Prediction]: ...


class AreaRepository(ABC):
    """Port for geographic area persistence."""

    @abstractmethod
    async def find_by_id(self, area_id: UUID) -> Area | None: ...

    @abstractmethod
    async def find_all_by_city(self, city: str) -> list[Area]: ...

    @abstractmethod
    async def find_by_point(self, lon: float, lat: float) -> Area | None:
        """Find the area polygon containing this coordinate."""
        ...


class RecommendationRepository(ABC):
    """Port for recommendation persistence."""

    @abstractmethod
    async def save_batch(self, recommendations: list[Recommendation]) -> list[Recommendation]: ...

    @abstractmethod
    async def find_by_prediction(self, prediction_id: UUID) -> list[Recommendation]: ...
