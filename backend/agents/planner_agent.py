"""
CrimePatrol — Planner Agent
Decides which downstream agents to run based on the request context.
Cheap decision: no LLM call needed here — pure rule-based routing.
"""
from backend.agents.state import AgentState
from backend.core.observability.logger import get_logger

logger = get_logger(__name__)

ALL_DATA_AGENTS = ["crime_data", "weather", "traffic", "events", "holiday", "infrastructure"]


def planner_node(state: AgentState) -> AgentState:
    """
    Determines the agent execution plan.
    For now: always run all data collection agents.
    Future: skip agents based on cached data freshness.
    """
    import uuid

    run_id = state.get("agent_run_id") or str(uuid.uuid4())
    logger.info("planner_agent_running", run_id=run_id, area_id=state.get("area_id"))

    return {
        **state,
        "agent_run_id": run_id,
        "agents_to_run": ALL_DATA_AGENTS,
        "planner_notes": "Full data collection pipeline scheduled.",
        "errors": state.get("errors", []),
    }
