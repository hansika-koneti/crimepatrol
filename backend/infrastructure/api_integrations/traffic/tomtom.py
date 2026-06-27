"""
CrimePatrol — Traffic & Events & Holidays API Integrations
"""
# ─── TomTom Traffic ──────────────────────────────────────────────────────────
# infrastructure/api_integrations/traffic/tomtom.py
from datetime import datetime, timezone
from uuid import UUID

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.config import get_settings
from backend.core.exceptions import ExternalAPIError
from backend.core.observability.logger import get_logger
from backend.domain.ports.services import TrafficServicePort, TrafficSnapshot

logger = get_logger(__name__)


class TomTomTrafficService(TrafficServicePort):
    """
    TomTom Traffic Flow API — free tier (2,500 calls/day).
    Endpoint: /flowSegmentData/absolute/10/json
    Returns current speed and freeflow speed for a coordinate.
    """

    BASE_URL = "https://api.tomtom.com/traffic/services/4"

    def __init__(self) -> None:
        self._settings = get_settings()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    async def get_flow(
        self, lat: float, lon: float, area_id: UUID, radius_km: float = 1.0
    ) -> TrafficSnapshot:
        if not self._settings.tomtom_api_key:
            # Return a simulated snapshot when no API key is configured
            return self._simulated_snapshot(area_id)

        url = f"{self.BASE_URL}/flowSegmentData/absolute/10/json"
        params = {
            "key": self._settings.tomtom_api_key,
            "point": f"{lat},{lon}",
            "unit": "KMPH",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                raise ExternalAPIError(
                    f"TomTom returned {resp.status_code}",
                    provider="tomtom",
                    status_code=resp.status_code,
                )
            data = resp.json().get("flowSegmentData", {})

        current_speed = float(data.get("currentSpeed", 30))
        free_flow = float(data.get("freeFlowSpeed", 50))
        congestion = max(0, min(100, int((1 - current_speed / max(free_flow, 1)) * 100)))

        return TrafficSnapshot(
            area_id=area_id,
            recorded_at=datetime.now(timezone.utc),
            congestion_pct=congestion,
            incident_count=0,      # TomTom incident API is separate
            flow_speed_kmh=current_speed,
            free_flow_speed=free_flow,
            road_closures=0,
        )

    def _simulated_snapshot(self, area_id: UUID) -> TrafficSnapshot:
        """Fallback when no API key — realistic hour-of-day simulation."""
        import random, math
        hour = datetime.now().hour
        # Rush hours: 8-10, 17-19
        rush = 1.0 if (8 <= hour <= 10 or 17 <= hour <= 19) else 0.3
        congestion = int(rush * 60 + random.uniform(0, 20))
        flow = max(10, 60 - congestion * 0.4)
        return TrafficSnapshot(
            area_id=area_id,
            recorded_at=datetime.now(timezone.utc),
            congestion_pct=min(100, congestion),
            incident_count=random.randint(0, 2) if rush > 0.5 else 0,
            flow_speed_kmh=round(flow, 1),
            free_flow_speed=60.0,
            road_closures=0,
        )
