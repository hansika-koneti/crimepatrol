"""
CrimePatrol — Area Repository (Concrete Implementation)
Implements AreaRepository port using SQLAlchemy + PostGIS spatial queries.
"""
from uuid import UUID

from geoalchemy2.functions import ST_SetSRID, ST_MakePoint, ST_Within
from geoalchemy2.shape import to_shape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.area import Area
from backend.domain.ports.repositories import AreaRepository
from backend.infrastructure.database.models.all_models import AreaModel


def _to_entity(m: AreaModel) -> Area:
    centroid_lon, centroid_lat = None, None
    if m.centroid is not None:
        shape = to_shape(m.centroid)
        centroid_lon, centroid_lat = shape.x, shape.y
    return Area(
        id=m.id,
        name=m.name,
        city=m.city,
        country_code=m.country_code,
        population=m.population,
        area_km2=m.area_km2,
        district_code=m.district_code,
        centroid_lon=centroid_lon,
        centroid_lat=centroid_lat,
        metadata=m.metadata_ or {},
        created_at=m.created_at,
    )


class SQLAreaRepository(AreaRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, area_id: UUID) -> Area | None:
        result = await self._session.get(AreaModel, area_id)
        return _to_entity(result) if result else None

    async def find_all_by_city(self, city: str) -> list[Area]:
        stmt = select(AreaModel).where(AreaModel.city == city).order_by(AreaModel.name)
        result = await self._session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def find_by_point(self, lon: float, lat: float) -> Area | None:
        """Find the area whose polygon contains the given coordinate (PostGIS ST_Within)."""
        point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
        stmt = (
            select(AreaModel)
            .where(ST_Within(point, AreaModel.geom))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalars().first()
        return _to_entity(row) if row else None
