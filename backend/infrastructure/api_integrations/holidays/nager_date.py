"""
CrimePatrol — Holidays Service (Nager.Date API — free, no key)
"""
from datetime import date, datetime, timezone
from uuid import UUID

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.config import get_settings
from backend.core.observability.logger import get_logger
from backend.domain.ports.services import Holiday, HolidayServicePort

logger = get_logger(__name__)

_holiday_cache: dict[str, list[Holiday]] = {}   # in-memory cache (year+country key)


class NagerDateHolidayService(HolidayServicePort):
    """
    Nager.Date Public Holiday API — completely free, no API key required.
    https://date.nager.at/api/v3/PublicHolidays/{year}/{countryCode}
    """

    BASE_URL = "https://date.nager.at/api/v3"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=6))
    async def get_holidays(self, country_code: str, year: int) -> list[Holiday]:
        cache_key = f"{country_code}:{year}"
        if cache_key in _holiday_cache:
            return _holiday_cache[cache_key]

        url = f"{self.BASE_URL}/PublicHolidays/{year}/{country_code}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        holidays = [
            Holiday(
                name=h["localName"],
                date=date.fromisoformat(h["date"]),
                country_code=country_code,
                is_public=True,
            )
            for h in data
        ]
        _holiday_cache[cache_key] = holidays
        logger.info("holidays_fetched", country=country_code, year=year, count=len(holidays))
        return holidays

    def is_holiday(self, check_date: date, holidays: list[Holiday]) -> bool:
        return any(h.date == check_date for h in holidays)
