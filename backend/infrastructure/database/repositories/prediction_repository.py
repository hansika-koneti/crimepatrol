"""
CrimePatrol — Prediction Repository (Concrete Implementation)
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.prediction import Prediction, SimilarCase, TopFeature
from backend.domain.entities.risk_level import RiskLevel
from backend.domain.ports.repositories import PredictionRepository
from backend.infrastructure.database.models.all_models import PredictionModel


def _to_entity(m: PredictionModel) -> Prediction:
    top_features = [
        TopFeature(**f) for f in (m.top_features or [])
    ]
    similar_cases = [
        SimilarCase(
            date=datetime.fromisoformat(s["date"]),
            area_name=s["area_name"],
            outcome=RiskLevel(s["outcome"]),
            similarity_score=s["similarity_score"],
        )
        for s in (m.similar_cases or [])
    ]
    return Prediction(
        id=m.id,
        area_id=m.area_id,
        predicted_for=m.predicted_for,
        window_hours=m.window_hours,
        risk_score=m.risk_score or 0.0,
        risk_level=RiskLevel(m.risk_level),
        crime_type=m.crime_type or "",
        confidence=m.confidence or 0.0,
        model_version=str(m.model_version_id or ""),
        probability_dist=m.probability_dist or {},
        shap_values=m.shap_values or {},
        top_features=top_features,
        explanation_text=m.explanation_text or "",
        similar_cases=similar_cases,
        feature_vector_id=m.feature_vector_id,
        agent_run_id=m.agent_run_id,
        created_at=m.created_at,
    )


def _features_to_jsonb(features: list[TopFeature]) -> list[dict]:
    return [
        {"feature": f.feature, "contribution": f.contribution, "direction": f.direction}
        for f in features
    ]


def _cases_to_jsonb(cases: list[SimilarCase]) -> list[dict]:
    return [
        {
            "date": c.date.isoformat(),
            "area_name": c.area_name,
            "outcome": c.outcome.value,
            "similarity_score": c.similarity_score,
        }
        for c in cases
    ]


class SQLPredictionRepository(PredictionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, prediction: Prediction) -> Prediction:
        model = PredictionModel(
            id=prediction.id,
            area_id=prediction.area_id,
            predicted_for=prediction.predicted_for,
            window_hours=prediction.window_hours,
            risk_score=prediction.risk_score,
            risk_level=prediction.risk_level.value,
            crime_type=prediction.crime_type,
            confidence=prediction.confidence,
            probability_dist=prediction.probability_dist,
            shap_values=prediction.shap_values,
            top_features=_features_to_jsonb(prediction.top_features),
            explanation_text=prediction.explanation_text,
            similar_cases=_cases_to_jsonb(prediction.similar_cases),
            feature_vector_id=prediction.feature_vector_id,
            agent_run_id=prediction.agent_run_id,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_entity(model)

    async def find_by_id(self, prediction_id: UUID) -> Prediction | None:
        result = await self._session.get(PredictionModel, prediction_id)
        return _to_entity(result) if result else None

    async def find_latest_by_area(self, area_id: UUID) -> Prediction | None:
        stmt = (
            select(PredictionModel)
            .where(PredictionModel.area_id == area_id)
            .order_by(desc(PredictionModel.predicted_for))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalars().first()
        return _to_entity(row) if row else None

    async def find_history(
        self,
        area_id: UUID | None = None,
        risk_level: RiskLevel | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Prediction]:
        stmt = select(PredictionModel).order_by(desc(PredictionModel.predicted_for))
        if area_id:
            stmt = stmt.where(PredictionModel.area_id == area_id)
        if risk_level:
            stmt = stmt.where(PredictionModel.risk_level == risk_level.value)
        stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def find_high_risk_areas(
        self, city: str, window_start: datetime, top_n: int = 10
    ) -> list[Prediction]:
        from backend.infrastructure.database.models.all_models import AreaModel
        stmt = (
            select(PredictionModel)
            .join(AreaModel, PredictionModel.area_id == AreaModel.id)
            .where(
                and_(
                    AreaModel.city == city,
                    PredictionModel.predicted_for >= window_start,
                    PredictionModel.risk_level.in_(["HIGH", "CRITICAL"]),
                )
            )
            .order_by(desc(PredictionModel.risk_score))
            .limit(top_n)
        )
        result = await self._session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def find_similar(
        self, feature_vector: dict, top_k: int = 5
    ) -> list[Prediction]:
        """
        Simple similarity: find predictions with matching risk_level and crime_type
        as a fallback when vector similarity isn't available.
        Full vector similarity requires pgvector extension (future enhancement).
        """
        target_level = feature_vector.get("predicted_risk_level", "MEDIUM")
        target_crime = feature_vector.get("crime_type", "")
        stmt = (
            select(PredictionModel)
            .where(
                and_(
                    PredictionModel.risk_level == target_level,
                    PredictionModel.crime_type == target_crime,
                )
            )
            .order_by(desc(PredictionModel.created_at))
            .limit(top_k)
        )
        result = await self._session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]
