"""
CrimePatrol — Model Training Pipeline
Trains RandomForest, XGBoost, GradientBoosting.
Compares all three. Saves the best-performing model.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from backend.core.config import get_settings
from backend.core.observability.logger import get_logger
from backend.ml.features.feature_definitions import (
    FEATURE_NAMES,
    RISK_LEVEL_CLASSES,
    RISK_LEVEL_ENCODING,
    TARGET_COLUMN,
)

logger = get_logger(__name__)
settings = get_settings()

MODEL_REGISTRY_PATH = Path(settings.model_registry_path)


# ─── Model Definitions ────────────────────────────────────────────────────────

def _build_models() -> dict[str, Pipeline]:
    """Returns all three candidate models wrapped in sklearn Pipelines."""
    return {
        "random_forest": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(
                n_estimators=300,
                max_depth=12,
                min_samples_leaf=5,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )),
        ]),
        "xgboost": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", XGBClassifier(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                use_label_encoder=False,
                eval_metric="mlogloss",
                random_state=42,
                n_jobs=-1,
            )),
        ]),
        "gradient_boosting": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.08,
                subsample=0.8,
                random_state=42,
            )),
        ]),
    }


# ─── Evaluation ───────────────────────────────────────────────────────────────

def _evaluate(model: Pipeline, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
    """Full evaluation: cross-val F1 + hold-out metrics."""
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_f1 = cross_val_score(model, X, y, cv=cv, scoring="f1_weighted", n_jobs=-1)

    # Hold-out split (last 20%)
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)

    metrics = {
        "accuracy":        round(accuracy_score(y_test, y_pred), 4),
        "precision":       round(precision_score(y_test, y_pred, average="weighted", zero_division=0), 4),
        "recall":          round(recall_score(y_test, y_pred, average="weighted", zero_division=0), 4),
        "f1_weighted":     round(f1_score(y_test, y_pred, average="weighted", zero_division=0), 4),
        "f1_cv_mean":      round(float(cv_f1.mean()), 4),
        "f1_cv_std":       round(float(cv_f1.std()), 4),
        "roc_auc":         round(roc_auc_score(y_test, y_prob, multi_class="ovr", average="weighted"), 4),
    }
    return metrics


# ─── Training Entrypoint ──────────────────────────────────────────────────────

async def run_training(city: str | None = None) -> dict[str, Any]:
    """
    Loads features from Feature Store, trains all three models,
    compares them, saves the winner to the model registry.

    Returns:
        dict with winner algorithm, metrics, and model version.
    """
    from backend.infrastructure.database.connection import get_session_factory
    from backend.infrastructure.database.models.all_models import (
        FeatureVectorModel, ModelRegistryModel
    )
    from sqlalchemy import select, and_

    city = city or settings.city_name
    logger.info("training_started", city=city)

    # ── 1. Load feature vectors from Feature Store ────────────────────────────
    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = (
            select(FeatureVectorModel)
            .where(
                and_(
                    FeatureVectorModel.is_training_data.is_(True),
                    FeatureVectorModel.label.isnot(None),
                    FeatureVectorModel.feature_version == settings.feature_schema_version,
                )
            )
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()

    if len(rows) < 100:
        logger.warning("training_insufficient_data", count=len(rows))
        return {"success": False, "reason": f"Only {len(rows)} labeled feature vectors. Need >= 100."}

    # ── 2. Build X, y matrices ────────────────────────────────────────────────
    records = []
    labels = []
    for row in rows:
        feat = row.features
        records.append([feat.get(name, 0) for name in FEATURE_NAMES])
        labels.append(RISK_LEVEL_ENCODING.get(row.label, 1))

    X = np.array(records, dtype=np.float32)
    y = np.array(labels, dtype=np.int32)
    logger.info("training_data_loaded", rows=len(X), features=X.shape[1])

    # ── 3. Train and compare all models ──────────────────────────────────────
    models = _build_models()
    results: dict[str, dict] = {}

    for name, pipeline in models.items():
        logger.info("training_model", algorithm=name)
        try:
            metrics = _evaluate(pipeline, X, y)
            results[name] = {"metrics": metrics, "pipeline": pipeline}
            logger.info("model_evaluated", algorithm=name, f1=metrics["f1_weighted"], roc_auc=metrics["roc_auc"])
        except Exception as exc:
            logger.error("model_training_failed", algorithm=name, error=str(exc))

    if not results:
        return {"success": False, "reason": "All model training attempts failed."}

    # ── 4. Select best model (by f1_weighted) ────────────────────────────────
    best_name = max(results, key=lambda n: results[n]["metrics"]["f1_weighted"])
    best_result = results[best_name]
    best_pipeline = best_result["pipeline"]
    best_metrics = best_result["metrics"]

    logger.info(
        "best_model_selected",
        algorithm=best_name,
        f1=best_metrics["f1_weighted"],
        roc_auc=best_metrics["roc_auc"],
    )

    # Comparison table log
    for name, res in results.items():
        m = res["metrics"]
        winner = " ← WINNER" if name == best_name else ""
        logger.info(
            "model_comparison",
            algorithm=name,
            accuracy=m["accuracy"],
            f1=m["f1_weighted"],
            roc_auc=m["roc_auc"],
            note=winner,
        )

    # ── 5. Retrain winner on full dataset ─────────────────────────────────────
    best_pipeline.fit(X, y)

    # ── 6. Save model to registry ─────────────────────────────────────────────
    version = f"v{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{best_name[:3].upper()}"
    model_dir = MODEL_REGISTRY_PATH / version
    model_dir.mkdir(parents=True, exist_ok=True)

    model_path = model_dir / "model.pkl"
    joblib.dump(best_pipeline, model_path)

    metadata = {
        "version": version,
        "algorithm": best_name,
        "feature_names": FEATURE_NAMES,
        "feature_version": settings.feature_schema_version,
        "classes": RISK_LEVEL_CLASSES,
        "training_rows": len(X),
        "metrics": best_metrics,
        "all_model_metrics": {n: r["metrics"] for n, r in results.items()},
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "city": city,
    }
    with open(model_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # ── 7. Persist to model_registry table ───────────────────────────────────
    async with session_factory() as session:
        # Mark previous active models as archived
        from sqlalchemy import update
        await session.execute(
            update(ModelRegistryModel)
            .where(ModelRegistryModel.status == "active")
            .values(status="archived")
        )
        registry_entry = ModelRegistryModel(
            id=uuid.uuid4(),
            version=version,
            algorithm=best_name,
            status="active",
            accuracy=best_metrics["accuracy"],
            precision_score=best_metrics["precision"],
            recall_score=best_metrics["recall"],
            f1_score=best_metrics["f1_weighted"],
            roc_auc=best_metrics["roc_auc"],
            feature_version=settings.feature_schema_version,
            training_rows=len(X),
            model_path=str(model_path),
            hyperparameters=metadata,
            trained_at=datetime.now(timezone.utc),
            city=city,
        )
        session.add(registry_entry)
        await session.commit()

    logger.info("model_saved", version=version, path=str(model_path))
    return {
        "success": True,
        "version": version,
        "algorithm": best_name,
        "metrics": best_metrics,
        "all_metrics": {n: r["metrics"] for n, r in results.items()},
        "training_rows": len(X),
    }
