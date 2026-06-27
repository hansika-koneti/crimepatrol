"""
CrimePatrol — Open-Meteo Weather Service
Completely free, no API key required.
Docs: https://open-meteo.com/en/docs
"""
from datetime import datetime, timezone
from uuid import UUID

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.config import get_settings
from backend.core.exceptions import ExternalAPIError
from backend.core.observability.logger import get_logger
from backend.domain.ports.services import WeatherServicePort, WeatherSnapshot

logger = get_logger(__name__)

# WMO Weather Code → human-readable condition
WMO_CONDITIONS: dict[int, str] = {
    0: "clear", 1: "clear", 2: "partly_cloudy", 3: "overcast",
    45: "fog", 48: "fog",
    51: "drizzle", 53: "drizzle", 55: "drizzle",
    61: "rain", 63: "rain", 65: "heavy_rain",
    71: "snow", 73: "snow", 75: "heavy_snow",
    80: "rain_showers", 81: "rain_showers", 82: "heavy_rain",
    95: "storm", 96: "storm", 99: "storm",
}


class OpenMeteoWeatherService(WeatherServicePort):
    """Fetches current + forecasted weather from Open-Meteo (no key required)."""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    HOURLY_VARS = [
        "temperature_2m",
        "apparent_temperature",
        "relative_humidity_2m",
        "weathercode",
        "windspeed_10m",
        "visibility",
        "precipitation",
        "uv_index",
    ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    async def _fetch(self, lat: float, lon: float, hours_ahead: int) -> dict:
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(self.HOURLY_VARS),
            "forecast_days": max(1, (hours_ahead // 24) + 1),
            "timezone": "auto",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(self.BASE_URL, params=params)
            if response.status_code != 200:
                raise ExternalAPIError(
                    f"Open-Meteo returned {response.status_code}",
                    provider="open_meteo",
                    status_code=response.status_code,
                )
            return response.json()

    def _parse_hour(
        self, data: dict, hour_index: int, area_id: UUID, recorded_at: datetime
    ) -> WeatherSnapshot:
        h = data["hourly"]
        wmo = h["weathercode"][hour_index] or 0
        return WeatherSnapshot(
            area_id=area_id,
            recorded_at=recorded_at,
            temperature_c=h["temperature_2m"][hour_index] or 0.0,
            feels_like_c=h["apparent_temperature"][hour_index] or 0.0,
            humidity_pct=int(h["relative_humidity_2m"][hour_index] or 0),
            condition=WMO_CONDITIONS.get(wmo, "unknown"),
            wind_kmh=h["windspeed_10m"][hour_index] or 0.0,
            visibility_km=(h["visibility"][hour_index] or 0.0) / 1000.0,
            precipitation_mm=h["precipitation"][hour_index] or 0.0,
            uv_index=int(h["uv_index"][hour_index] or 0),
        )

    async def get_current(self, lat: float, lon: float, area_id: UUID) -> WeatherSnapshot:
        data = await self._fetch(lat, lon, hours_ahead=1)
        now = datetime.now(timezone.utc)
        # Find the closest past hour in the forecast
        times = data["hourly"]["time"]
        current_str = now.strftime("%Y-%m-%dT%H:00")
        try:
            idx = times.index(current_str)
        except ValueError:
            idx = 0
        snapshot = self._parse_hour(data, idx, area_id, now)
        logger.debug("weather_fetched", area_id=str(area_id), condition=snapshot.condition)
        return snapshot

    async def get_forecast(
        self, lat: float, lon: float, area_id: UUID, hours_ahead: int = 24
    ) -> list[WeatherSnapshot]:
        data = await self._fetch(lat, lon, hours_ahead=hours_ahead)
        times = data["hourly"]["time"]
        snapshots = []
        for i, time_str in enumerate(times[:hours_ahead]):
            try:
                recorded_at = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            snapshots.append(self._parse_hour(data, i, area_id, recorded_at))
        return snapshots
