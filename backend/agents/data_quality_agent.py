"""
CrimePatrol — Data Quality Agent
Validates all collected data before feature engineering.
"""
from backend.agents.state import AgentState
from backend.core.observability.logger import get_logger

logger = get_logger(__name__)

MIN_QUALITY_SCORE = 40.0   # below this → skip prediction


def data_quality_node(state: AgentState) -> AgentState:
    issues: list[str] = []
    checks_passed = 0
    checks_total = 0

    # ── 1. Crime incidents ───────────────────────────────────────────────────
    checks_total += 1
    incidents = state.get("raw_incidents", [])
    if len(incidents) > 0:
        checks_passed += 1
    else:
        issues.append("No crime incidents found for this area/window.")

    # ── 2. Weather data ──────────────────────────────────────────────────────
    checks_total += 1
    weather = state.get("weather_data", {})
    if weather.get("condition"):
        checks_passed += 1
    else:
        issues.append("Weather data missing or incomplete.")

    # ── 3. Traffic data ──────────────────────────────────────────────────────
    checks_total += 1
    traffic = state.get("traffic_data", {})
    if "congestion_pct" in traffic:
        checks_passed += 1
    else:
        issues.append("Traffic data missing.")

    # ── 4. IoT data ──────────────────────────────────────────────────────────
    checks_total += 1
    iot = state.get("iot_data", {})
    if "streetlight_pct" in iot:
        checks_passed += 1
    else:
        issues.append("IoT data missing.")

    # ── 5. Duplicate incident check ──────────────────────────────────────────
    checks_total += 1
    seen = set()
    dups = 0
    clean_incidents = []
    for inc in incidents:
        key = (inc.get("crime_type"), inc.get("occurred_at"), inc.get("lon"), inc.get("lat"))
        if key in seen:
            dups += 1
        else:
            seen.add(key)
            clean_incidents.append(inc)
    if dups == 0:
        checks_passed += 1
    else:
        issues.append(f"Removed {dups} duplicate incidents.")

    # ── 6. API failure detection ─────────────────────────────────────────────
    checks_total += 1
    error_count = len(state.get("errors", []))
    if error_count == 0:
        checks_passed += 1
    else:
        issues.append(f"{error_count} agent error(s) detected.")

    quality_score = round((checks_passed / checks_total) * 100, 2)
    quality_passed = quality_score >= MIN_QUALITY_SCORE

    report = {
        "quality_score": quality_score,
        "checks_passed": checks_passed,
        "checks_total": checks_total,
        "issues": issues,
        "incidents_before": len(incidents),
        "incidents_after": len(clean_incidents),
        "duplicates_removed": dups,
    }

    logger.info(
        "data_quality_agent_done",
        quality_score=quality_score,
        quality_passed=quality_passed,
        issues=issues,
    )

    return {
        **state,
        "raw_incidents": clean_incidents,
        "quality_report": report,
        "quality_passed": quality_passed,
    }
