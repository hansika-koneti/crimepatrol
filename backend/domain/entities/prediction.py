"""
CrimePatrol Domain — Prediction Entity
"""
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from backend.domain.entities.risk_level import RiskLevel


@dataclass
class TopFeature:
    feature: str
    contribution: float        # SHAP value magnitude
    direction: str             # 'increases_risk' | 'reduces_risk'


@dataclass
class SimilarCase:
    date: datetime
    area_name: str
    outcome: RiskLevel
    similarity_score: float    # cosine similarity, 0–1


@dataclass
class Prediction:
    """
    Full prediction result including ML output, SHAP, and LLM narration.
    Stored in the predictions table after each agent pipeline run.
    """
    id: UUID
    area_id: UUID
    predicted_for: datetime
    window_hours: int
    risk_score: float                          # 0–100
    risk_level: RiskLevel
    crime_type: str                            # most probable crime type
    confidence: float                          # 0.0–1.0
    model_version: str

    # Explainability
    probability_dist: dict[str, float] = field(default_factory=dict)
    shap_values: dict[str, float] = field(default_factory=dict)
    top_features: list[TopFeature] = field(default_factory=list)
    explanation_text: str = ""
    similar_cases: list[SimilarCase] = field(default_factory=list)

    # Metadata
    feature_vector_id: UUID | None = None
    agent_run_id: UUID | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if not (0.0 <= self.risk_score <= 100.0):
            raise ValueError(f"risk_score must be 0–100, got {self.risk_score}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be 0–1, got {self.confidence}")
