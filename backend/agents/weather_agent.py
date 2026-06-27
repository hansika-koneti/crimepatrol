"""
CrimePatrol — Weather, Traffic, Events, Holiday, Infrastructure Agents
Each agent has exactly one responsibility.
"""
import asyncio
from datetime import datetime, timezone

from backend.agents.state import AgentState
from backend.core.observability.logger import get_logger

logger = get_logger(__name__)


# =============================================================================
# Weather Agent
# =============================================================================

def weather_node(state: AgentState) -> AgentState:
    return asyncio.get_event_loop().run_until_complete(_weather_async(state))


async def _weather_async(state: AgentState) -> AgentState:
    from backend.infrastructure.api_integrations.weather.open_meteo import OpenMeteoWeatherService
    from backend.infrastructure.database.connection import get_session_factory
    from backend.infrastructure.database.repositories.area_repository import SQLAreaRepository
    from uuid import UUID

    area_id = UUID(state["area_id"])
    errors = list(state.get("errors", []))
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            area = await SQLAreaRepository(session).find_by_id(area_id)

        if area and area.centroid:
            lat, lon = area.centroid[1], area.centroid[0]
        else:
            lat, lon = 41.8827, -87.6298   # Chicago Loop fallback

        svc = OpenMeteoWeatherService()
        snap = await svc.get_current(lat, lon, area_id)
        weather = {
            "temperature_c": snap.temperature_c,
            "feels_like_c": snap.feels_like_c,
            "humidity_pct": snap.humidity_pct,
            "condition": snap.condition,
            "wind_kmh": snap.wind_kmh,
            "visibility_km": snap.visibility_km,
            "precipitation_mm": snap.precipitation_mm,
        }
        logger.info("weather_agent_done", condition=snap.condition, area_id=str(area_id))
        return {**state, "weather_data": weather}
    except Exception as exc:
        logger.error("weather_agent_error", error=str(exc))
        errors.append(f"WeatherAgent: {exc}")
        return {**state, "weather_data": {}, "errors": errors}


# =============================================================================
# Traffic Agent
# =============================================================================

def traffic_node(state: AgentState) -> AgentState:
    return asyncio.get_event_loop().run_until_complete(_traffic_async(state))


async def _traffic_async(state: AgentState) -> AgentState:
    from backend.infrastructure.api_integrations.traffic.tomtom import TomTomTrafficService
    from backend.infrastructure.database.connection import get_session_factory
    from backend.infrastructure.database.repositories.area_repository import SQLAreaRepository
    from uuid import UUID

    area_id = UUID(state["area_id"])
    errors = list(state.get("errors", []))
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            area = await SQLAreaRepository(session).find_by_id(area_id)

        lat, lon = (area.centroid[1], area.centroid[0]) if (area and area.centroid) else (41.8827, -87.6298)
        snap = await TomTomTrafficService().get_flow(lat, lon, area_id)
        traffic = {
            "congestion_pct": snap.congestion_pct,
            "incident_count": snap.incident_count,
            "flow_speed_kmh": snap.flow_speed_kmh,
            "road_closures": snap.road_closures,
        }
        logger.info("traffic_agent_done", congestion=snap.congestion_pct, area_id=str(area_id))
        return {**state, "traffic_data": traffic}
    except Exception as exc:
        logger.error("traffic_agent_error", error=str(exc))
        errors.append(f"TrafficAgent: {exc}")
        return {**state, "traffic_data": {}, "errors": errors}


# =============================================================================
# Events Agent
# =============================================================================

def events_node(state: AgentState) -> AgentState:
    return asyncio.get_event_loop().run_until_complete(_events_async(state))


async def _events_async(state: AgentState) -> AgentState:
    errors = list(state.get("errors", []))
    try:
        # Ticketmaster integration (returns empty list if no API key)
        from backend.infrastructure.api_integrations.events.ticketmaster import TicketmasterEventsService
        from backend.infrastructure.database.connection import get_session_factory
        from backend.infrastructure.database.repositories.area_repository import SQLAreaRepository
        from uuid import UUID

        area_id = UUID(state["area_id"])
        session_factory = get_session_factory()
        async with session_factory() as session:
            area = await SQLAreaRepository(session).find_by_id(area_id)

        lat, lon = (area.centroid[1], area.centroid[0]) if (area and area.centroid) else (41.8827, -87.6298)
        events = await TicketmasterEventsService().get_events(
            city=state.get("city", "Chicago"),
            lat=lat, lon=lon,
            radius_km=2.0,
            date_from=datetime.now(timezone.utc),
        )
        events_data = [
            {"name": e.name, "category": e.category, "crowd_bucket": e.crowd_bucket,
             "expected_crowd": e.expected_crowd or 0, "starts_at": e.starts_at.isoformat()}
            for e in events
        ]
        logger.info("events_agent_done", count=len(events_data))
        return {**state, "events_data": events_data}
    except Exception as exc:
        logger.error("events_agent_error", error=str(exc))
        errors.append(f"EventsAgent: {exc}")
        return {**state, "events_data": [], "errors": errors}


# =============================================================================
# Holiday Agent
# =============================================================================

def holiday_node(state: AgentState) -> AgentState:
    return asyncio.get_event_loop().run_until_complete(_holiday_async(state))


async def _holiday_async(state: AgentState) -> AgentState:
    from backend.infrastructure.api_integrations.holidays.nager_date import NagerDateHolidayService
    from backend.core.config import get_settings

    errors = list(state.get("errors", []))
    try:
        svc = NagerDateHolidayService()
        settings = get_settings()
        now = datetime.now(timezone.utc)
        holidays = await svc.get_holidays(settings.holiday_country_code, now.year)
        is_hol = svc.is_holiday(now.date(), holidays)
        hol_name = next((h.name for h in holidays if h.date == now.date()), None)
        logger.info("holiday_agent_done", is_holiday=is_hol, name=hol_name)
        return {**state, "holiday_data": {"is_holiday": is_hol, "holiday_name": hol_name}}
    except Exception as exc:
        logger.error("holiday_agent_error", error=str(exc))
        errors.append(f"HolidayAgent: {exc}")
        return {**state, "holiday_data": {"is_holiday": False, "holiday_name": None}, "errors": errors}


# =============================================================================
# Infrastructure Agent (Simulated IoT)
# =============================================================================

def infrastructure_node(state: AgentState) -> AgentState:
    return asyncio.get_event_loop().run_until_complete(_infrastructure_async(state))


async def _infrastructure_async(state: AgentState) -> AgentState:
    from backend.infrastructure.simulated_iot.iot_service import SimulatedIoTService
    from uuid import UUID

    area_id = UUID(state["area_id"])
    errors = list(state.get("errors", []))
    try:
        snap = await SimulatedIoTService().get_snapshot(area_id)
        iot = {
            "streetlight_pct": snap.streetlight_pct,
            "cctv_alert_count": snap.cctv_alert_count,
            "cctv_operational": snap.cctv_operational,
            "crowd_density": snap.crowd_density,
            "anomaly_detected": snap.anomaly_detected,
        }
        logger.info("infrastructure_agent_done", streetlight_pct=snap.streetlight_pct)
        return {**state, "iot_data": iot}
    except Exception as exc:
        logger.error("infrastructure_agent_error", error=str(exc))
        errors.append(f"InfrastructureAgent: {exc}")
        return {**state, "iot_data": {}, "errors": errors}
