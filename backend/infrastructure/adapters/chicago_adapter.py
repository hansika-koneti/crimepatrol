"""
CrimePatrol — Chicago Open Data Crime Adapter
Fetches from the City of Chicago Open Data Portal (Socrata API).
Dataset: Crimes - 2001 to Present (id: ijzp-q8t2)
URL: https://data.cityofchicago.org/resource/ijzp-q8t2.json
No API key required. App token increases rate limit (optional).
"""
from datetime import datetime, timezone
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.config import get_settings
from backend.core.observability.logger import get_logger
from backend.infrastructure.adapters.base_crime_adapter import (
    BaseCrimeAdapter,
    RawIncidentRecord,
)

logger = get_logger(__name__)


class ChicagoCrimeAdapter(BaseCrimeAdapter):
    """
    Fetches crime incidents from the Chicago Open Data Portal.

    Socrata API returns JSON with fields:
      id, date, primary_type, description, location_description,
      arrest, domestic, latitude, longitude, community_area, ...
    """

    BASE_URL = "https://data.cityofchicago.org/resource/ijzp-q8t2.json"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._headers: dict[str, str] = {}
        if self._settings.chicago_data_app_token:
            self._headers["X-App-Token"] = self._settings.chicago_data_app_token

    @property
    def city_name(self) -> str:
        return "Chicago"

    @property
    def country_code(self) -> str:
        return "US"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def _fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                self.BASE_URL,
                headers=self._headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    def _parse_record(self, row: dict[str, Any]) -> RawIncidentRecord | None:
        """Convert one Socrata row → RawIncidentRecord. Returns None if invalid."""
        try:
            lat = float(row.get("latitude") or 0)
            lon = float(row.get("longitude") or 0)
        except (TypeError, ValueError):
            return None

        # Chicago open data has some records with (0,0) coordinates
        if lat == 0.0 and lon == 0.0:
            return None

        crime_type = (row.get("primary_type") or "UNKNOWN").title()
        occurred_str = row.get("date", "")
        try:
            occurred_at = datetime.fromisoformat(occurred_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

        description = row.get("description", "")
        raw_text = f"{crime_type}: {description}".strip(": ")

        return RawIncidentRecord(
            source_id=str(row.get("id", "")),
            crime_type=crime_type,
            crime_category=self.normalize_crime_category(crime_type),
            longitude=lon,
            latitude=lat,
            occurred_at=occurred_at,
            address=row.get("block"),
            severity=self.infer_severity(crime_type),
            raw_text=raw_text,
            extra={
                "arrest": row.get("arrest"),
                "domestic": row.get("domestic"),
                "community_area": row.get("community_area"),
                "district": row.get("district"),
                "beat": row.get("beat"),
                "ward": row.get("ward"),
                "description": description,
            },
        )

    async def fetch_recent(
        self,
        hours_back: int = 24,
        limit: int = 1000,
    ) -> list[RawIncidentRecord]:
        from datetime import timedelta

        since = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        since_str = since.strftime("%Y-%m-%dT%H:%M:%S")

        params = {
            "$where": f"date >= '{since_str}'",
            "$limit": limit,
            "$order": "date DESC",
        }
        logger.info("chicago_adapter_fetch_recent", hours_back=hours_back, limit=limit)
        rows = await self._fetch(params)
        records = [r for row in rows if (r := self._parse_record(row)) is not None]
        logger.info("chicago_adapter_parsed", total=len(rows), valid=len(records))
        return records

    async def fetch_historical(
        self,
        start: datetime,
        end: datetime,
        limit: int = 50_000,
    ) -> list[RawIncidentRecord]:
        start_str = start.strftime("%Y-%m-%dT%H:%M:%S")
        end_str = end.strftime("%Y-%m-%dT%H:%M:%S")
        params = {
            "$where": f"date >= '{start_str}' AND date < '{end_str}'",
            "$limit": limit,
            "$order": "date ASC",
        }
        logger.info(
            "chicago_adapter_fetch_historical",
            start=start_str,
            end=end_str,
            limit=limit,
        )
        rows = await self._fetch(params)
        records = [r for row in rows if (r := self._parse_record(row)) is not None]
        logger.info("chicago_adapter_historical_parsed", total=len(rows), valid=len(records))
        return records
