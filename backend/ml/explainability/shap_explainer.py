"""
CrimePatrol — SHAP Explainability Engine
Computes SHAP values for every prediction and returns:
  - Per-feature SHAP contributions
  - Top-N contributing features (with direction)
  - Summary for LLM narration
"""
import json
from pathlib import Path
from typing import Any

import numpy as np
import shap

from backend.core.config import get_settings
from backend.core.observability.logger import get_logger
from backend.ml.features.feature_definitions import FEATURE_NAMES, RISK_LEVEL_DECODING

logger = get_logger(__name__)
settings = get_settings()

_explainer: shap.Explainer | None = None
_loaded_version: str | None = None


def _load_explainer(pipeline: Any) -> shap.Explainer:
    """
    Build the right SHAP explainer based on model type.
    TreeExplainer is exact and fast for tree-based models.
    """
    clf = pipeline.named_steps["clf"]
    clf_type = type(clf).__name__

    if "XGB" in clf_type or "Forest" in clf_type or "Gradient" in clf_type:
        # Use the scaler-transformed data as background
        return shap.TreeExplainer(clf)
    return shap.KernelExplainer(clf.predict_proba, shap.sample(np.zeros((1, len(FEATURE_NAMES))), 50))


def get_explainer(pipeline: Any, version: str) -> shap.Explainer:
    """Return cached explainer or rebuild if model version changed."""
    global _explainer, _loaded_version
    if _explainer is None or _loaded_version != version:
        _explainer = _load_explainer(pipeline)
        _loaded_version = version
        logger.info("shap_explainer_built", version=version)
    return _explainer


def explain_prediction(
    pipeline: Any,
    model_version: str,
    feature_vector: dict[str, Any],
    predicted_class_idx: int,
    top_n: int = 5,
) -> dict[str, Any]:
    """
    Compute SHAP values for a single prediction.

    Args:
        pipeline:           Trained sklearn Pipeline.
        model_version:      Model version string (for cache invalidation).
        feature_vector:     Dict of feature_name → value.
        predicted_class_idx: Index of the predicted risk level (0–3).
        top_n:              Number of top features to return.

    Returns:
        {
            "shap_values": {feature: shap_value},
            "top_features": [{feature, contribution, direction}],
            "feature_importance_summary": str (for LLM input)
        }
    """
    # Build input array
    X = np.array([[feature_vector.get(f, 0) for f in FEATURE_NAMES]], dtype=np.float32)

    # Apply scaler step if present
    scaler = pipeline.named_steps.get("scaler")
    X_scaled = scaler.transform(X) if scaler else X

    explainer = get_explainer(pipeline, model_version)

    try:
        shap_values = explainer.shap_values(X_scaled)
        # shap_values shape: (n_classes, n_samples, n_features) for TreeExplainer
        if isinstance(shap_values, list):
            values_for_class = shap_values[predicted_class_idx][0]
        else:
            values_for_class = shap_values[0]
    except Exception as exc:
        logger.warning("shap_computation_failed", error=str(exc))
        # Fallback: uniform zero contributions
        values_for_class = np.zeros(len(FEATURE_NAMES))

    # Build feature → SHAP value dict
    shap_dict = {
        feat: round(float(val), 4)
        for feat, val in zip(FEATURE_NAMES, values_for_class)
    }

    # Sort by absolute contribution
    sorted_features = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)
    top_features = [
        {
            "feature": feat,
            "contribution": abs(val),
            "direction": "increases_risk" if val > 0 else "reduces_risk",
        }
        for feat, val in sorted_features[:top_n]
    ]

    # Human-readable summary for LLM prompt
    summary_parts = []
    for tf in top_features:
        actual_value = feature_vector.get(tf["feature"], "N/A")
        direction = "↑ increases" if tf["direction"] == "increases_risk" else "↓ reduces"
        summary_parts.append(
            f"• {tf['feature']} = {actual_value} ({direction} risk, weight={tf['contribution']:.3f})"
        )
    summary = "\n".join(summary_parts)

    return {
        "shap_values": shap_dict,
        "top_features": top_features,
        "feature_importance_summary": summary,
    }
