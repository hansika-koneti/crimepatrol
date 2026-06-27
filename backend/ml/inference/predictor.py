"""
CrimePatrol — ML Inference (Prediction Engine)
Loads the active model from the registry and runs inference.
Never uses an LLM for prediction — pure ML only.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from backend.core.config import get_settings
from backend.core.exceptions import ModelNotAvailableError
from backend.core.observability.logger import get_logger
from backend.domain.entities.prediction import Prediction, TopFeature
from backend.domain.entities.risk_level import RiskLevel
from backend.ml.features.feature_definitions import (
    FEATURE_DEFAULTS,
    FEATURE_NAMES,
    RISK_LEVEL_CLASSES,
    RISK_LEVEL_DECODING,
    RISK_LEVEL_ENCODING,
)
from backend.ml.explainability.shap_explainer import explain_prediction

logger = get_logger(__name__)
settings = get_settings()

_cached_pipeline: Any = None
_cached_metadata: dict = {}
_cached_version: str = ""


def _load_active_model() -> tuple[Any, dict, str]:
    """Load the most recently saved active model from disk."""
    global _cached_pipeline, _cached_metadata, _cached_version

    registry_path = Path(settings.model_registry_path)
    if not registry_path.exists():
        raise ModelNotAvailableError("Model registry path does not exist. Run training first.")

    # Find the latest model directory (sorted by name = timestamp-based)
    model_dirs = sorted(
        [d for d in registry_path.iterdir() if d.is_dir()],
        reverse=True,
    )
    if not model_dirs:
        raise ModelNotAvailableError("No trained models found. Run the training pipeline first.")

    latest_dir = model_dirs[0]
    version = latest_dir.name

    if version == _cached_version and _cached_pipeline is not None:
        return _cached_pipeline, _cached_metadata, _cached_version  # cache hit

    model_path = latest_dir / "model.pkl"
    metadata_path = latest_dir / "metadata.json"

    if not model_path.exists():
        raise ModelNotAvailableError(f"model.pkl not found in {latest_dir}")

    _cached_pipeline = joblib.load(model_path)
    _cached_metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
    _cached_version = version

    logger.info("model_loaded", version=version, algorithm=_cached_metadata.get("algorithm"))
    return _cached_pipeline, _cached_metadata, _cached_version


def _build_feature_array(feature_vector: dict[str, Any]) -> np.ndarray:
    """Convert feature dict to numpy array in the correct feature order."""
    row = [feature_vector.get(name, FEATURE_DEFAULTS.get(name, 0)) for name in FEATURE_NAMES]
    return np.array([row], dtype=np.float32)


def predict(
    feature_vector: dict[str, Any],
    area_id: uuid.UUID,
    predicted_for: datetime | None = None,
    window_hours: int = 3,
) -> Prediction:
    """
    Run inference for a single feature vector.

    Args:
        feature_vector: Dict mapping feature names to values.
        area_id:        UUID of the geographic area.
        predicted_for:  Time window start (defaults to now).
        window_hours:   Time window length in hours.

    Returns:
        Prediction domain entity (without LLM explanation — added by ExplainabilityAgent).

    Raises:
        ModelNotAvailableError: If no trained model exists.
    """
    pipeline, metadata, version = _load_active_model()

    X = _build_feature_array(feature_vector)

    # Apply scaler
    scaler = pipeline.named_steps.get("scaler")
    X_scaled = scaler.transform(X) if scaler else X
    clf = pipeline.named_steps["clf"]

    # Probabilities for all 4 classes
    proba = clf.predict_proba(X_scaled)[0]
    predicted_idx = int(np.argmax(proba))
    predicted_label = RISK_LEVEL_DECODING[predicted_idx]
    confidence = float(proba[predicted_idx])

    # Risk score: weighted sum (0–100)
    risk_score = float(
        proba[0] * 10 + proba[1] * 35 + proba[2] * 65 + proba[3] * 90
    )

    prob_dist = {RISK_LEVEL_CLASSES[i]: round(float(proba[i]), 4) for i in range(len(proba))}

    # SHAP explainability
    shap_result = explain_prediction(
        pipeline=pipeline,
        model_version=version,
        feature_vector=feature_vector,
        predicted_class_idx=predicted_idx,
        top_n=5,
    )

    top_features = [
        TopFeature(
            feature=tf["feature"],
            contribution=tf["contribution"],
            direction=tf["direction"],
        )
        for tf in shap_result["top_features"]
    ]

    # Most probable crime type from feature vector
    crime_type = _infer_crime_type(feature_vector)

    prediction = Prediction(
        id=uuid.uuid4(),
        area_id=area_id,
        predicted_for=predicted_for or datetime.now(timezone.utc),
        window_hours=window_hours,
        risk_score=round(risk_score, 2),
        risk_level=RiskLevel(predicted_label),
        crime_type=crime_type,
        confidence=round(confidence, 4),
        model_version=version,
        probability_dist=prob_dist,
        shap_values=shap_result["shap_values"],
        top_features=top_features,
        explanation_text="",       # filled by ExplainabilityAgent
    )

    logger.info(
        "prediction_made",
        area_id=str(area_id),
        risk_level=predicted_label,
        risk_score=risk_score,
        confidence=confidence,
        model_version=version,
    )
    return prediction


def _infer_crime_type(feature_vector: dict[str, Any]) -> str:
    """Infer most probable crime type from historical feature ratios."""
    theft_pct = feature_vector.get("theft_pct_7d", 0)
    violent_pct = feature_vector.get("violent_pct_7d", 0)
    if theft_pct > 0.4:
        return "theft"
    if violent_pct > 0.3:
        return "violent_crime"
    if feature_vector.get("is_night", 0):
        return "vandalism"
    return "theft"   # default — most common urban crime type
