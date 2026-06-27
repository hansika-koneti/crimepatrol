"""
CrimePatrol — LangGraph Agent State Schema
Shared state TypedDict flowing through all agents in the pipeline.
Every agent reads from and writes to this state.
"""
from datetime import datetime
from typing import Any, TypedDict
from uuid import UUID


class AgentState(TypedDict, total=False):
    # ── Input ─────────────────────────────────────────────────────────────────
    area_id: str                         # UUID string of the target area
    city: str                            # e.g. "Chicago"
    time_window_start: str               # ISO datetime string
    window_hours: int                    # prediction window length (default 3)
    agent_run_id: str                    # UUID string for this pipeline run

    # ── Planner ───────────────────────────────────────────────────────────────
    agents_to_run: list[str]             # agent names selected by PlannerAgent
    planner_notes: str                   # reasoning from planner

    # ── Data Collection ───────────────────────────────────────────────────────
    raw_incidents: list[dict]            # recent incidents fetched by CrimeDataAgent
    weather_data: dict                   # WeatherSnapshot as dict
    traffic_data: dict                   # TrafficSnapshot as dict
    events_data: list[dict]             # list of PublicEvent dicts
    holiday_data: dict                   # {is_holiday: bool, holiday_name: str|None}
    iot_data: dict                       # IoTSnapshot as dict

    # ── Data Quality ──────────────────────────────────────────────────────────
    quality_report: dict                 # DataQualityAgent output
    quality_passed: bool                 # whether quality threshold was met

    # ── Feature Engineering ───────────────────────────────────────────────────
    feature_vector: dict                 # assembled feature dict (all 29 features)
    feature_vector_id: str | None        # UUID of saved FeatureVector row

    # ── Prediction ────────────────────────────────────────────────────────────
    prediction: dict                     # Prediction entity as dict
    prediction_id: str | None            # UUID of saved Prediction row

    # ── Explainability ────────────────────────────────────────────────────────
    shap_values: dict
    top_features: list[dict]
    probability_dist: dict
    explanation_text: str                # LLM-generated narrative
    similar_cases: list[dict]

    # ── Recommendations ───────────────────────────────────────────────────────
    recommendations: list[dict]          # prioritized recommendation list

    # ── Errors ────────────────────────────────────────────────────────────────
    errors: list[str]                    # non-fatal errors collected during run
    fatal_error: str | None              # fatal error (stops pipeline)
