"""
CrimePatrol — Feature Engineering Agent
Assembles the feature vector from all collected data sources.
Writes to the Feature Store (feature_vectors table).
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from backend.agents.state import AgentState
from backend.core.observability.logger import get_logger
from backend.ml.features.feature_definitions import FEATURE_DEFAULTS

logger = get_logger(__name__)


def feature_engineering_node(state: AgentState) -> AgentState:
    return asyncio.get_event_loop().run_until_complete(_fe_async(state))


async def _fe_async(state: AgentState) -> AgentState:
    from backend.infrastructure.database.connection import get_session_factory
    from backend.infrastructure.database.models.all_models import FeatureVectorModel
    from backend.core.config import get_settings

    settings = get_settings()
    errors = list(state.get("errors", []))

    try:
        window_start_str = state.get("time_window_start", datetime.now(timezone.utc).isoformat())
        window_start = datetime.fromisoformat(window_start_str)
        incidents = state.get("raw_incidents", [])
        weather = state.get("weather_data", {})
        traffic = state.get("traffic_data", {})
        events = state.get("events_data", [])
        holiday = state.get("holiday_data", {})
        iot = state.get("iot_data", {})

        # ── Temporal features ────────────────────────────────────────────────
        hour = window_start.hour
        dow = window_start.weekday()
        month = window_start.month
        is_weekend = int(dow >= 5)
        is_night = int(hour >= 22 or hour < 5)
        season_map = {12: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2, 7: 2, 8: 2, 9: 3, 10: 3, 11: 3}
        season = season_map.get(month, 0)

        # ── Crime history features ────────────────────────────────────────────
        now = window_start
        last_24h = [i for i in incidents if (now - datetime.fromisoformat(i["occurred_at"])).total_seconds() <= 86400]
        last_7d  = [i for i in incidents if (now - datetime.fromisoformat(i["occurred_at"])).total_seconds() <= 604800]
        last_30d = incidents   # already filtered to 7 days in crime_data_agent — using all available

        def category_pct(incs: list, cat: str) -> float:
            if not incs:
                return 0.0
            return round(sum(1 for i in incs if i.get("crime_category") == cat) / len(incs), 4)

        rolling_avg = round(len(last_7d) / 7, 2) if last_7d else 0.0

        # ── Weather features ─────────────────────────────────────────────────
        condition = weather.get("condition", "")
        is_rainy = int(condition in ("rain", "heavy_rain", "rain_showers", "storm", "drizzle"))
        is_foggy = int(condition == "fog")

        # ── Events features ──────────────────────────────────────────────────
        active_events = [e for e in events if e.get("starts_at")]
        has_event = int(len(active_events) > 0)
        largest_crowd = max((e.get("expected_crowd", 0) for e in active_events), default=0)
        crowd_bucket_map = {"small": 1, "medium": 2, "large": 3, "massive": 4}
        max_bucket = max(
            (crowd_bucket_map.get(e.get("crowd_bucket", ""), 0) for e in active_events), default=0
        )

        # ── Assemble feature vector ───────────────────────────────────────────
        feature_vector = {
            **FEATURE_DEFAULTS,  # safe defaults for any missing feature
            "hour_of_day":       hour,
            "day_of_week":       dow,
            "month":             month,
            "is_weekend":        is_weekend,
            "is_holiday":        int(holiday.get("is_holiday", False)),
            "is_night":          is_night,
            "season":            season,
            "incident_count_24h": len(last_24h),
            "incident_count_7d":  len(last_7d),
            "incident_count_30d": len(last_30d),
            "theft_pct_7d":      category_pct(last_7d, "theft"),
            "violent_pct_7d":    category_pct(last_7d, "violent"),
            "rolling_avg_daily": rolling_avg,
            "temperature_c":     weather.get("temperature_c", 15.0),
            "humidity_pct":      weather.get("humidity_pct", 50),
            "wind_kmh":          weather.get("wind_kmh", 10.0),
            "precipitation_mm":  weather.get("precipitation_mm", 0.0),
            "visibility_km":     weather.get("visibility_km", 10.0),
            "is_rainy":          is_rainy,
            "is_foggy":          is_foggy,
            "congestion_pct":    traffic.get("congestion_pct", 20),
            "traffic_incidents": traffic.get("incident_count", 0),
            "road_closures":     traffic.get("road_closures", 0),
            "has_event":         has_event,
            "event_crowd_size":  largest_crowd,
            "event_crowd_bucket": max_bucket,
            "streetlight_pct":   iot.get("streetlight_pct", 92),
            "cctv_alert_count":  iot.get("cctv_alert_count", 0),
            "cctv_operational":  iot.get("cctv_operational", 8),
            "crowd_density":     iot.get("crowd_density", 1.0),
            "iot_anomaly":       int(iot.get("anomaly_detected", False)),
        }

        # ── Write to Feature Store ────────────────────────────────────────────
        fv_id = str(uuid.uuid4())
        session_factory = get_session_factory()
        async with session_factory() as session:
            fv_model = FeatureVectorModel(
                id=uuid.UUID(fv_id),
                area_id=uuid.UUID(state["area_id"]),
                window_start=window_start,
                window_hours=state.get("window_hours", 3),
                features=feature_vector,
                feature_version=settings.feature_schema_version,
                is_training_data=False,
            )
            session.add(fv_model)
            await session.commit()

        logger.info("feature_engineering_done", features=len(feature_vector), fv_id=fv_id)
        return {**state, "feature_vector": feature_vector, "feature_vector_id": fv_id}

    except Exception as exc:
        logger.error("feature_engineering_error", error=str(exc))
        errors.append(f"FeatureEngineeringAgent: {exc}")
        return {**state, "feature_vector": FEATURE_DEFAULTS, "errors": errors}
