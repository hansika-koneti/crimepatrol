"""
CrimePatrol — LangGraph Agent Graph
Wires all 14 agents into a directed StateGraph with conditional routing.

Flow:
  planner → [crime_data, weather, traffic, events, holiday, infrastructure]
           → data_quality → feature_engineering → prediction
           → [explainability, recommendation] → dashboard_update
           → report (daily, runs separately)
"""
from langgraph.graph import END, StateGraph

from backend.agents.state import AgentState
from backend.agents.planner_agent import planner_node
from backend.agents.crime_data_agent import crime_data_node
from backend.agents.weather_agent import weather_node
from backend.agents.traffic_agent import traffic_node
from backend.agents.events_agent import events_node
from backend.agents.holiday_agent import holiday_node
from backend.agents.infrastructure_agent import infrastructure_node
from backend.agents.data_quality_agent import data_quality_node
from backend.agents.feature_engineering_agent import feature_engineering_node
from backend.agents.prediction_agent import prediction_node
from backend.agents.explainability_agent import explainability_node
from backend.agents.recommendation_agent import recommendation_node
from backend.agents.dashboard_update_agent import dashboard_update_node


def _should_continue_after_quality(state: AgentState) -> str:
    """Route: if data quality failed, go to END. Otherwise continue."""
    if state.get("fatal_error"):
        return "end"
    if not state.get("quality_passed", True):
        return "end"
    return "feature_engineering"


def build_prediction_graph() -> StateGraph:
    """
    Constructs and compiles the prediction pipeline graph.
    Returns a compiled LangGraph that can be invoked with an AgentState.
    """
    graph = StateGraph(AgentState)

    # ── Register nodes ──────────────────────────────────────────────────────
    graph.add_node("planner",              planner_node)
    graph.add_node("crime_data",           crime_data_node)
    graph.add_node("weather",              weather_node)
    graph.add_node("traffic",              traffic_node)
    graph.add_node("events",               events_node)
    graph.add_node("holiday",              holiday_node)
    graph.add_node("infrastructure",       infrastructure_node)
    graph.add_node("data_quality",         data_quality_node)
    graph.add_node("feature_engineering",  feature_engineering_node)
    graph.add_node("prediction",           prediction_node)
    graph.add_node("explainability",       explainability_node)
    graph.add_node("recommendation",       recommendation_node)
    graph.add_node("dashboard_update",     dashboard_update_node)

    # ── Entry point ──────────────────────────────────────────────────────────
    graph.set_entry_point("planner")

    # ── Planner → Parallel data collection ──────────────────────────────────
    # LangGraph runs these sequentially for now; parallel execution can be
    # enabled via Send() API when async fan-out is needed.
    graph.add_edge("planner",        "crime_data")
    graph.add_edge("crime_data",     "weather")
    graph.add_edge("weather",        "traffic")
    graph.add_edge("traffic",        "events")
    graph.add_edge("events",         "holiday")
    graph.add_edge("holiday",        "infrastructure")

    # ── Data quality gate ────────────────────────────────────────────────────
    graph.add_edge("infrastructure", "data_quality")
    graph.add_conditional_edges(
        "data_quality",
        _should_continue_after_quality,
        {
            "feature_engineering": "feature_engineering",
            "end": END,
        },
    )

    # ── Core pipeline ────────────────────────────────────────────────────────
    graph.add_edge("feature_engineering", "prediction")
    graph.add_edge("prediction",          "explainability")
    graph.add_edge("explainability",      "recommendation")
    graph.add_edge("recommendation",      "dashboard_update")
    graph.add_edge("dashboard_update",    END)

    return graph.compile()


# Module-level compiled graph (lazy-initialized)
_prediction_graph = None


def get_prediction_graph():
    global _prediction_graph
    if _prediction_graph is None:
        _prediction_graph = build_prediction_graph()
    return _prediction_graph
