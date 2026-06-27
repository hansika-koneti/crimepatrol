"""
CrimePatrol — Prediction, Explainability, Recommendation, Dashboard Update Agents
"""
import asyncio
import uuid
from datetime import datetime, timezone

from backend.agents.state import AgentState
from backend.core.observability.logger import get_logger

logger = get_logger(__name__)


# =============================================================================
# Prediction Agent — pure ML, NO LLM
# =============================================================================

def prediction_node(state: AgentState) -> AgentState:
    errors = list(state.get("errors", []))
    try:
        from backend.ml.inference.predictor import predict

        prediction = predict(
            feature_vector=state.get("feature_vector", {}),
            area_id=uuid.UUID(state["area_id"]),
            predicted_for=datetime.fromisoformat(state.get("time_window_start", datetime.now(timezone.utc).isoformat())),
            window_hours=state.get("window_hours", 3),
        )
        pred_dict = {
            "id": str(prediction.id),
            "risk_score": prediction.risk_score,
            "risk_level": prediction.risk_level.value,
            "crime_type": prediction.crime_type,
            "confidence": prediction.confidence,
            "model_version": prediction.model_version,
            "probability_dist": prediction.probability_dist,
        }
        logger.info("prediction_agent_done", risk_level=prediction.risk_level.value, score=prediction.risk_score)
        return {
            **state,
            "prediction": pred_dict,
            "shap_values": prediction.shap_values,
            "top_features": [{"feature": f.feature, "contribution": f.contribution, "direction": f.direction} for f in prediction.top_features],
            "probability_dist": prediction.probability_dist,
        }
    except Exception as exc:
        logger.error("prediction_agent_error", error=str(exc))
        errors.append(f"PredictionAgent: {exc}")
        return {**state, "prediction": {}, "errors": errors}


# =============================================================================
# Explainability Agent — LLM narrates SHAP output
# =============================================================================

def explainability_node(state: AgentState) -> AgentState:
    return asyncio.get_event_loop().run_until_complete(_explain_async(state))


async def _explain_async(state: AgentState) -> AgentState:
    from backend.core.config import get_settings
    errors = list(state.get("errors", []))

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import HumanMessage

        settings = get_settings()
        if not settings.gemini_api_key:
            return {**state, "explanation_text": _fallback_explanation(state)}

        pred = state.get("prediction", {})
        top_feats = state.get("top_features", [])
        weather = state.get("weather_data", {})
        incidents = state.get("raw_incidents", [])

        feat_summary = "\n".join(
            f"• {f['feature']} ({'↑' if f['direction']=='increases_risk' else '↓'} risk, weight={f['contribution']:.3f})"
            for f in top_feats[:5]
        )
        prompt = f"""You are a crime analyst AI for a Smart City Safety Platform.
A machine learning model predicted the following for a city area:

Risk Level: {pred.get('risk_level')}
Risk Score: {pred.get('risk_score')}/100
Most Probable Crime Type: {pred.get('crime_type')}
Confidence: {round(pred.get('confidence', 0) * 100, 1)}%
Recent Incidents (24h): {len([i for i in incidents if True])}
Weather: {weather.get('condition')} at {weather.get('temperature_c')}°C

Top Contributing Factors (from SHAP analysis):
{feat_summary}

Write a 3-sentence natural language explanation of WHY this risk level was predicted.
Be specific. Mention actual values. Do NOT use bullet points. Do NOT exceed 60 words."""

        llm = ChatGoogleGenerativeAI(model=settings.gemini_model, google_api_key=settings.gemini_api_key)
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        explanation = response.content.strip()

        # Also find similar historical cases
        similar_cases = await _find_similar_cases(state)

        logger.info("explainability_agent_done", explanation_length=len(explanation))
        return {**state, "explanation_text": explanation, "similar_cases": similar_cases}

    except Exception as exc:
        logger.warning("explainability_agent_error", error=str(exc))
        errors.append(f"ExplainabilityAgent: {exc}")
        return {**state, "explanation_text": _fallback_explanation(state), "errors": errors}


def _fallback_explanation(state: AgentState) -> str:
    pred = state.get("prediction", {})
    feats = state.get("top_features", [])
    feat_str = ", ".join(f['feature'] for f in feats[:3])
    return (
        f"Risk level {pred.get('risk_level', 'UNKNOWN')} predicted with "
        f"{round((pred.get('confidence', 0)) * 100, 1)}% confidence. "
        f"Top contributing factors: {feat_str or 'insufficient data'}."
    )


async def _find_similar_cases(state: AgentState) -> list[dict]:
    from backend.infrastructure.database.connection import get_session_factory
    from backend.infrastructure.database.repositories.prediction_repository import SQLPredictionRepository
    try:
        pred = state.get("prediction", {})
        session_factory = get_session_factory()
        async with session_factory() as session:
            repo = SQLPredictionRepository(session)
            similar = await repo.find_similar(
                {"predicted_risk_level": pred.get("risk_level"), "crime_type": pred.get("crime_type")},
                top_k=3,
            )
        return [
            {
                "date": s.predicted_for.isoformat(),
                "area_name": str(s.area_id),
                "outcome": s.risk_level.value,
                "similarity_score": 0.85,
            }
            for s in similar
        ]
    except Exception:
        return []


# =============================================================================
# Recommendation Agent — LLM generates prioritized actions
# =============================================================================

def recommendation_node(state: AgentState) -> AgentState:
    return asyncio.get_event_loop().run_until_complete(_recommend_async(state))


async def _recommend_async(state: AgentState) -> AgentState:
    errors = list(state.get("errors", []))
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import HumanMessage
        from backend.core.config import get_settings
        import json

        settings = get_settings()
        if not settings.gemini_api_key:
            return {**state, "recommendations": _fallback_recommendations(state)}

        pred = state.get("prediction", {})
        iot = state.get("iot_data", {})
        weather = state.get("weather_data", {})

        prompt = f"""You are a crime prevention AI for a Smart City Safety Platform.
Given:
- Risk Level: {pred.get('risk_level')} (Score: {pred.get('risk_score')}/100)
- Crime Type: {pred.get('crime_type')}
- Streetlight operational: {iot.get('streetlight_pct')}%
- CCTV alerts active: {iot.get('cctv_alert_count')}
- Weather: {weather.get('condition')}

Generate exactly 3 actionable recommendations as a JSON array:
[{{"action": "...", "category": "patrol|infrastructure|alert|traffic|cctv", "priority": "CRITICAL|HIGH|MEDIUM|LOW", "priority_score": 1-100, "reason": "...", "estimated_impact": "HIGH|MEDIUM|LOW"}}]
Return ONLY the JSON array. No explanation."""

        llm = ChatGoogleGenerativeAI(model=settings.gemini_model, google_api_key=settings.gemini_api_key)
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        text = response.content.strip().strip("```json").strip("```").strip()
        recommendations = json.loads(text)
        logger.info("recommendation_agent_done", count=len(recommendations))
        return {**state, "recommendations": recommendations}

    except Exception as exc:
        logger.warning("recommendation_agent_error", error=str(exc))
        errors.append(f"RecommendationAgent: {exc}")
        return {**state, "recommendations": _fallback_recommendations(state), "errors": errors}


def _fallback_recommendations(state: AgentState) -> list[dict]:
    risk_level = state.get("prediction", {}).get("risk_level", "MEDIUM")
    return [
        {"action": "Increase police patrol frequency in the area", "category": "patrol",
         "priority": "HIGH" if risk_level in ("HIGH", "CRITICAL") else "MEDIUM",
         "priority_score": 80, "reason": f"Area risk level is {risk_level}", "estimated_impact": "HIGH"},
        {"action": "Verify all CCTV cameras are operational", "category": "cctv",
         "priority": "MEDIUM", "priority_score": 60, "reason": "Preventive monitoring", "estimated_impact": "MEDIUM"},
        {"action": "Issue public safety notification for residents", "category": "alert",
         "priority": "MEDIUM", "priority_score": 50, "reason": "Community awareness reduces risk", "estimated_impact": "LOW"},
    ]


# =============================================================================
# Dashboard Update Agent — pushes via Redis pub/sub → WebSocket
# =============================================================================

def dashboard_update_node(state: AgentState) -> AgentState:
    return asyncio.get_event_loop().run_until_complete(_dashboard_async(state))


async def _dashboard_async(state: AgentState) -> AgentState:
    import json
    errors = list(state.get("errors", []))
    try:
        from backend.infrastructure.cache.redis_client import publish, cache_set

        payload = {
            "event": "prediction_update",
            "area_id": state.get("area_id"),
            "prediction": state.get("prediction", {}),
            "recommendations": state.get("recommendations", []),
            "quality_score": state.get("quality_report", {}).get("quality_score"),
            "agent_run_id": state.get("agent_run_id"),
        }
        message = json.dumps(payload)
        await publish("dashboard:updates", message)
        # Cache latest prediction for fast reads
        await cache_set(f"prediction:area:{state.get('area_id')}", message)
        logger.info("dashboard_update_agent_done", area_id=state.get("area_id"))
    except Exception as exc:
        logger.warning("dashboard_update_error", error=str(exc))
        errors.append(f"DashboardUpdateAgent: {exc}")
    return {**state, "errors": errors}
