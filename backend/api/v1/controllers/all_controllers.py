"""
CrimePatrol — REST API Controllers
Health, Auth, Predictions, Areas, Incidents, Analytics, Agents, Reports, Quality.
"""
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.core.security import create_access_token, get_token_subject, hash_password, verify_password
from backend.core.exceptions import AuthenticationError
from backend.infrastructure.database.connection import get_session

settings = get_settings()

# ─── Shared response wrapper ─────────────────────────────────────────────────

def ok(data: Any, meta: dict | None = None) -> dict:
    return {"success": True, "data": data, "meta": meta or {}, "errors": []}

# =============================================================================
# Health Controller
# =============================================================================

router_health = APIRouter()

@router_health.get("/health", tags=["Health"])
async def health_check():
    from backend.core.observability.health import (
        APP_VERSION, check_database, check_ml_model, check_redis,
        get_uptime, aggregate_status, SystemHealth
    )
    from backend.infrastructure.database.connection import get_session_factory
    from backend.infrastructure.cache.redis_client import get_redis

    db_health = await check_database(get_session_factory())
    redis_health = await check_redis(get_redis())
    ml_health = check_ml_model(settings.model_registry_path)
    components = [db_health, redis_health, ml_health]
    overall = aggregate_status(components)

    return SystemHealth(
        status=overall,
        version=APP_VERSION,
        environment=settings.app_env,
        uptime_seconds=get_uptime(),
        components=components,
    ).to_dict()

# =============================================================================
# Auth Controller
# =============================================================================

router_auth = APIRouter(prefix="/auth")

@router_auth.post("/login")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    if form.username != settings.admin_email or not verify_password(form.password, hash_password(settings.admin_password)):
        if form.username != settings.admin_email or form.password != settings.admin_password:
            raise HTTPException(status_code=401, detail="Invalid credentials.")
    token = create_access_token(subject=form.username)
    return {"access_token": token, "token_type": "bearer"}

# =============================================================================
# Predictions Controller
# =============================================================================

router_predictions = APIRouter(prefix="/predictions")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    return get_token_subject(token)

@router_predictions.post("/run")
async def run_prediction(
    body: dict,
    current_user: str = Depends(get_current_user),
):
    """Trigger the full LangGraph agent pipeline for an area+time window."""
    from backend.agents.graph import get_prediction_graph
    area_id = body.get("area_id")
    if not area_id:
        raise HTTPException(status_code=400, detail="area_id is required.")

    graph = get_prediction_graph()
    initial_state = {
        "area_id": area_id,
        "city": body.get("city", settings.city_name),
        "time_window_start": body.get("time_window_start", datetime.now(timezone.utc).isoformat()),
        "window_hours": body.get("window_hours", 3),
        "errors": [],
    }
    result = graph.invoke(initial_state)
    return ok({
        "prediction": result.get("prediction"),
        "explanation": result.get("explanation_text"),
        "recommendations": result.get("recommendations"),
        "quality_score": result.get("quality_report", {}).get("quality_score"),
        "top_features": result.get("top_features"),
        "probability_dist": result.get("probability_dist"),
        "similar_cases": result.get("similar_cases"),
        "errors": result.get("errors"),
    })

@router_predictions.get("/history")
async def get_history(
    area_id: str | None = None,
    risk_level: str | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from backend.infrastructure.database.repositories.prediction_repository import SQLPredictionRepository
    from backend.domain.entities.risk_level import RiskLevel
    repo = SQLPredictionRepository(session)
    from uuid import UUID
    predictions = await repo.find_history(
        area_id=UUID(area_id) if area_id else None,
        risk_level=RiskLevel(risk_level) if risk_level else None,
        limit=limit, offset=offset,
    )
    return ok([{
        "id": str(p.id), "area_id": str(p.area_id),
        "risk_score": p.risk_score, "risk_level": p.risk_level.value,
        "crime_type": p.crime_type, "confidence": p.confidence,
        "predicted_for": p.predicted_for.isoformat(),
    } for p in predictions], {"limit": limit, "offset": offset})

@router_predictions.get("/{prediction_id}")
async def get_prediction(
    prediction_id: str,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from backend.infrastructure.database.repositories.prediction_repository import SQLPredictionRepository
    from uuid import UUID
    repo = SQLPredictionRepository(session)
    pred = await repo.find_by_id(UUID(prediction_id))
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found.")
    return ok({
        "id": str(pred.id), "risk_score": pred.risk_score, "risk_level": pred.risk_level.value,
        "crime_type": pred.crime_type, "confidence": pred.confidence,
        "explanation_text": pred.explanation_text, "top_features": [
            {"feature": f.feature, "contribution": f.contribution, "direction": f.direction}
            for f in pred.top_features
        ],
        "shap_values": pred.shap_values, "probability_dist": pred.probability_dist,
        "similar_cases": [{"date": s.date.isoformat(), "area_name": s.area_name, "outcome": s.outcome.value, "similarity": s.similarity_score} for s in pred.similar_cases],
    })

# =============================================================================
# Areas Controller
# =============================================================================

router_areas = APIRouter(prefix="/areas")

@router_areas.get("")
async def list_areas(
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from backend.infrastructure.database.repositories.area_repository import SQLAreaRepository
    areas = await SQLAreaRepository(session).find_all_by_city(settings.city_name)
    return ok([{
        "id": str(a.id), "name": a.name, "city": a.city,
        "centroid_lon": a.centroid_lon, "centroid_lat": a.centroid_lat,
        "population": a.population, "population_density": a.population_density,
    } for a in areas])

@router_areas.get("/{area_id}/prediction")
async def get_area_latest_prediction(
    area_id: str,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from backend.infrastructure.database.repositories.prediction_repository import SQLPredictionRepository
    from uuid import UUID
    pred = await SQLPredictionRepository(session).find_latest_by_area(UUID(area_id))
    if not pred:
        raise HTTPException(status_code=404, detail="No predictions found for this area.")
    return ok({"risk_score": pred.risk_score, "risk_level": pred.risk_level.value,
               "crime_type": pred.crime_type, "confidence": pred.confidence,
               "predicted_for": pred.predicted_for.isoformat()})

# =============================================================================
# Analytics Controller
# =============================================================================

router_analytics = APIRouter(prefix="/analytics")

@router_analytics.get("/high-risk")
async def get_high_risk_areas(
    top_n: int = 10,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from backend.infrastructure.database.repositories.prediction_repository import SQLPredictionRepository
    predictions = await SQLPredictionRepository(session).find_high_risk_areas(
        city=settings.city_name,
        window_start=datetime.now(timezone.utc),
        top_n=top_n,
    )
    return ok([{"area_id": str(p.area_id), "risk_score": p.risk_score,
                "risk_level": p.risk_level.value, "crime_type": p.crime_type} for p in predictions])

@router_analytics.get("/heatmap")
async def get_heatmap(
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Returns GeoJSON FeatureCollection for the heatmap layer."""
    from backend.infrastructure.database.repositories.prediction_repository import SQLPredictionRepository
    from backend.infrastructure.database.repositories.area_repository import SQLAreaRepository
    predictions = await SQLPredictionRepository(session).find_high_risk_areas(
        city=settings.city_name, window_start=datetime.now(timezone.utc), top_n=50
    )
    features = []
    area_repo = SQLAreaRepository(session)
    for p in predictions:
        area = await area_repo.find_by_id(p.area_id)
        if area and area.centroid:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": list(area.centroid)},
                "properties": {"risk_score": p.risk_score, "risk_level": p.risk_level.value,
                               "area_name": area.name, "crime_type": p.crime_type},
            })
    return ok({"type": "FeatureCollection", "features": features})

# =============================================================================
# ETL / Agents / Quality Controllers
# =============================================================================

router_etl = APIRouter(prefix="/etl")

@router_etl.post("/trigger")
async def trigger_etl(current_user: str = Depends(get_current_user)):
    from backend.application.run_etl_pipeline import run_etl_pipeline
    result = await run_etl_pipeline()
    return ok(result)

router_agents = APIRouter(prefix="/agents")

@router_agents.get("/status")
async def agent_status(current_user: str = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    from sqlalchemy import select, desc
    from backend.infrastructure.database.models.all_models import AgentExecutionLogModel
    stmt = select(AgentExecutionLogModel).order_by(desc(AgentExecutionLogModel.started_at)).limit(50)
    result = await session.execute(stmt)
    logs = result.scalars().all()
    return ok([{
        "run_id": str(l.run_id), "agent_name": l.agent_name, "status": l.status,
        "duration_ms": l.duration_ms, "started_at": l.started_at.isoformat() if l.started_at else None,
        "error": l.error_message,
    } for l in logs])

router_quality = APIRouter(prefix="/quality")

@router_quality.get("/reports")
async def quality_reports(current_user: str = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    from sqlalchemy import select, desc
    from backend.infrastructure.database.models.all_models import DataQualityReportModel
    stmt = select(DataQualityReportModel).order_by(desc(DataQualityReportModel.run_at)).limit(20)
    result = await session.execute(stmt)
    reports = result.scalars().all()
    return ok([{
        "source": r.source, "quality_score": r.quality_score,
        "total_records": r.total_records, "duplicates_removed": r.duplicates_removed,
        "run_at": r.run_at.isoformat(),
    } for r in reports])
