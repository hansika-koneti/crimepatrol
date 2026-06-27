"""
CrimePatrol — Crime Incident Repository (Concrete Implementation)
Implements the CrimeIncidentRepository port using SQLAlchemy async.
"""
from datetime import datetime
from uuid import UUID

from geoalchemy2.functions import ST_SetSRID, ST_MakePoint, ST_Within
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.crime_incident import CrimeIncident, DataSource, GeoPoint
from backend.domain.ports.repositories import CrimeIncidentRepository
from backend.infrastructure.database.models.all_models import CrimeIncidentModel


def _to_entity(m: CrimeIncidentModel) -> CrimeIncident:
    """Map ORM model → domain entity."""
    # GeoAlchemy2 WKBElement → lon/lat
    from geoalchemy2.shape import to_shape
    shape = to_shape(m.location)
    return CrimeIncident(
        id=m.id,
        crime_type=m.crime_type,
        crime_category=m.crime_category or "",
        location=GeoPoint(longitude=shape.x, latitude=shape.y),
        occurred_at=m.occurred_at,
        source=DataSource(m.source),
        city=m.city,
        area_id=m.area_id,
        severity=m.severity,
        address=m.address,
        reported_at=m.reported_at,
        source_url=m.source_url,
        source_id=m.source_id,
        raw_text=m.raw_text,
        is_verified=m.is_verified,
        is_duplicate=m.is_duplicate,
        metadata=m.metadata_ or {},
        created_at=m.created_at,
    )


def _to_model(e: CrimeIncident) -> CrimeIncidentModel:
    """Map domain entity → ORM model."""
    return CrimeIncidentModel(
        id=e.id,
        area_id=e.area_id,
        crime_type=e.crime_type,
        crime_category=e.crime_category,
        severity=e.severity,
        location=ST_SetSRID(ST_MakePoint(e.location.longitude, e.location.latitude), 4326),
        address=e.address,
        occurred_at=e.occurred_at,
        reported_at=e.reported_at,
        source=e.source.value,
        source_url=e.source_url,
        source_id=e.source_id,
        raw_text=e.raw_text,
        is_verified=e.is_verified,
        is_duplicate=e.is_duplicate,
        city=e.city,
        metadata_=e.metadata,
    )


class SQLCrimeIncidentRepository(CrimeIncidentRepository):
    """PostgreSQL implementation of CrimeIncidentRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, incident: CrimeIncident) -> CrimeIncident:
        model = _to_model(incident)
        self._session.add(model)
        await self._session.flush()
        return _to_entity(model)

    async def save_batch(self, incidents: list[CrimeIncident]) -> int:
        """Insert non-duplicate incidents. Returns count inserted."""
        saved = 0
        for incident in incidents:
            if incident.source_id:
                exists = await self.exists_by_source(incident.source.value, incident.source_id)
                if exists:
                    continue
            self._session.add(_to_model(incident))
            saved += 1
        await self._session.flush()
        return saved

    async def find_by_id(self, incident_id: UUID) -> CrimeIncident | None:
        result = await self._session.get(CrimeIncidentModel, incident_id)
        return _to_entity(result) if result else None

    async def find_by_area_and_window(
        self,
        area_id: UUID,
        start: datetime,
        end: datetime,
        crime_category: str | None = None,
    ) -> list[CrimeIncident]:
        stmt = (
            select(CrimeIncidentModel)
            .where(
                and_(
                    CrimeIncidentModel.area_id == area_id,
                    CrimeIncidentModel.occurred_at >= start,
                    CrimeIncidentModel.occurred_at < end,
                    CrimeIncidentModel.is_duplicate.is_(False),
                )
            )
        )
        if crime_category:
            stmt = stmt.where(CrimeIncidentModel.crime_category == crime_category)
        stmt = stmt.order_by(CrimeIncidentModel.occurred_at.desc())
        result = await self._session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def count_by_area_and_window(
        self, area_id: UUID, start: datetime, end: datetime
    ) -> int:
        stmt = select(func.count()).where(
            and_(
                CrimeIncidentModel.area_id == area_id,
                CrimeIncidentModel.occurred_at >= start,
                CrimeIncidentModel.occurred_at < end,
                CrimeIncidentModel.is_duplicate.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def find_recent_by_city(
        self, city: str, limit: int = 50
    ) -> list[CrimeIncident]:
        stmt = (
            select(CrimeIncidentModel)
            .where(
                and_(
                    CrimeIncidentModel.city == city,
                    CrimeIncidentModel.is_duplicate.is_(False),
                )
            )
            .order_by(CrimeIncidentModel.occurred_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def exists_by_source(self, source: str, source_id: str) -> bool:
        stmt = select(CrimeIncidentModel.id).where(
            and_(
                CrimeIncidentModel.source == source,
                CrimeIncidentModel.source_id == source_id,
            )
        ).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
