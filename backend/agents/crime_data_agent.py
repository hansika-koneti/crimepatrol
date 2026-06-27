"""
CrimePatrol — Crime Data Collection Agent
Fetches recent incidents for the target area from the city adapter.
"""
import asyncio
from datetime import datetime, timedelta, timezone

from backend.agents.state import AgentState
from backend.core.config import get_settings
from backend.core.observability.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


def crime_data_node(state: AgentState) -> AgentState:
    """Synchronous wrapper — LangGraph nodes must be sync or use asyncio.run()."""
    return asyncio.get_event_loop().run_until_complete(_crime_data_async(state))


async def _crime_data_async(state: AgentState) -> AgentState:
    from backend.infrastructure.database.connection import get_session_factory
    from backend.infrastructure.database.repositories.crime_repository import SQLCrimeIncidentRepository
    from backend.infrastructure.database.repositories.area_repository import SQLAreaRepository

    area_id = state.get("area_id")
    window_start_str = state.get("time_window_start")
    errors = list(state.get("errors", []))

    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            crime_repo = SQLCrimeIncidentRepository(session)
            now = datetime.now(timezone.utc)
            window_start = datetime.fromisoformat(window_start_str) if window_start_str else now
            lookback = window_start - timedelta(days=7)

            from uuid import UUID
            incidents = await crime_repo.find_by_area_and_window(
                area_id=UUID(area_id),
                start=lookback,
                end=window_start + timedelta(hours=state.get("window_hours", 3)),
            )

        raw = [
            {
                "crime_type": i.crime_type,
                "crime_category": i.crime_category,
                "occurred_at": i.occurred_at.isoformat(),
                "severity": i.severity,
                "lon": i.location.longitude,
                "lat": i.location.latitude,
            }
            for i in incidents
        ]
        logger.info("crime_data_agent_done", count=len(raw), area_id=area_id)
        return {**state, "raw_incidents": raw}

    except Exception as exc:
        logger.error("crime_data_agent_error", error=str(exc))
        errors.append(f"CrimeDataAgent: {exc}")
        return {**state, "raw_incidents": [], "errors": errors}
