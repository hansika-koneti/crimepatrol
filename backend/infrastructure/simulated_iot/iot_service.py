"""
CrimePatrol — Simulated IoT Service
Simulates streetlight, CCTV, and crowd density data as if from real IoT APIs.
Each area gets statistically realistic values based on:
  - Time of day, day of week
  - Random sensor failures (realistic ~5% failure rate)
  - Anomaly injection (realistic ~2% anomaly rate)
This provides the ML model with infrastructure features
without requiring real hardware or IoT subscriptions.
"""
import math
import random
from datetime import datetime, timezone
from uuid import UUID

from backend.core.observability.logger import get_logger
from backend.domain.ports.services import IoTServicePort, IoTSnapshot

logger = get_logger(__name__)


class SimulatedIoTService(IoTServicePort):
    """
    Deterministic-ish simulation based on area_id seed + current time.
    Using a seeded RNG ensures consistent readings within the same minute
    (useful for testing), while varying across time windows.
    """

    STREETLIGHT_BASE_PCT = 92        # % operational baseline
    STREETLIGHT_FAILURE_RATE = 0.08  # 8% nightly degradation
    CCTV_BASE_COUNT = 8              # cameras per area
    CCTV_FAILURE_RATE = 0.05

    def _seed(self, area_id: UUID, dt: datetime) -> int:
        """Create a time-window-stable seed from area + hour."""
        return hash(str(area_id)) ^ (dt.year * 10000 + dt.month * 100 + dt.day) ^ (dt.hour * 7)

    async def get_snapshot(self, area_id: UUID) -> IoTSnapshot:
        now = datetime.now(timezone.utc)
        rng = random.Random(self._seed(area_id, now))
        hour = now.hour

        # Streetlights: lower at night (22:00–05:00), random failures
        is_night = hour >= 22 or hour < 5
        failure_chance = self.STREETLIGHT_FAILURE_RATE * (1.5 if is_night else 1.0)
        streetlight_pct = int(
            self.STREETLIGHT_BASE_PCT * (1 - rng.random() * failure_chance)
        )
        streetlight_pct = max(60, min(100, streetlight_pct))

        # CCTV: some cameras down due to maintenance / vandalism
        cctv_operational = self.CCTV_BASE_COUNT - rng.randint(0, 2)
        # CCTV alerts: more at night + weekends
        is_weekend = now.weekday() >= 5
        base_alerts = 1 if is_night else 0
        cctv_alert_count = base_alerts + rng.randint(0, 3 if is_weekend else 1)

        # Crowd density: sine curve peaking at 18:00, scaled by day type
        crowd_peak = 8.0 if is_weekend else 5.0
        crowd_density = max(
            0.1,
            crowd_peak * max(0, math.sin(math.pi * (hour - 8) / 14))
            + rng.uniform(-0.5, 0.5),
        )

        # Anomaly: ~2% chance
        anomaly_detected = rng.random() < 0.02

        if anomaly_detected:
            cctv_alert_count += rng.randint(2, 5)
            logger.warning(
                "iot_anomaly_detected",
                area_id=str(area_id),
                cctv_alerts=cctv_alert_count,
            )

        snapshot = IoTSnapshot(
            area_id=area_id,
            recorded_at=now,
            streetlight_pct=streetlight_pct,
            cctv_alert_count=cctv_alert_count,
            cctv_operational=cctv_operational,
            crowd_density=round(crowd_density, 2),
            anomaly_detected=anomaly_detected,
        )
        logger.debug(
            "iot_snapshot_generated",
            area_id=str(area_id),
            streetlight_pct=streetlight_pct,
            crowd_density=snapshot.crowd_density,
        )
        return snapshot
