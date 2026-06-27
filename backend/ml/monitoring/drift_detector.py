"""
CrimePatrol — Model Monitoring
Detects data drift (PSI) and accuracy decay.
Alerts administrator if retraining is recommended.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from scipy import stats

from backend.core.config import get_settings
from backend.core.observability.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


# ─── Population Stability Index ──────────────────────────────────────────────

def compute_psi(baseline: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """
    Compute PSI between baseline and current distributions.
    PSI < 0.1  → No significant change
    PSI 0.1–0.2 → Moderate change, monitor
    PSI > 0.2  → Significant drift, retrain recommended
    """
    # Clip to avoid log(0)
    eps = 1e-6
    baseline_counts, bin_edges = np.histogram(baseline, bins=bins, range=(baseline.min(), baseline.max()))
    current_counts, _ = np.histogram(current, bins=bin_edges)

    baseline_pct = baseline_counts / (len(baseline) + eps) + eps
    current_pct = current_counts / (len(current) + eps) + eps

    psi = float(np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct)))
    return round(psi, 4)


def compute_feature_drift(
    baseline_features: dict[str, list[float]],
    current_features: dict[str, list[float]],
) -> dict[str, float]:
    """
    Compute PSI per feature. Returns {feature_name: psi_score}.
    """
    drift_scores: dict[str, float] = {}
    for feature_name, baseline_vals in baseline_features.items():
        current_vals = current_features.get(feature_name, [])
        if len(baseline_vals) < 10 or len(current_vals) < 10:
            drift_scores[feature_name] = 0.0
            continue
        drift_scores[feature_name] = compute_psi(
            np.array(baseline_vals), np.array(current_vals)
        )
    return drift_scores


# ─── Monitoring Pipeline ──────────────────────────────────────────────────────

async def trigger_monitoring() -> dict[str, Any]:
    """
    Runs the model monitoring pipeline:
    1. Loads the active model's baseline metrics from registry.
    2. Computes current accuracy from recent predictions.
    3. Computes feature drift (PSI) comparing baseline vs recent features.
    4. Saves monitoring report.
    5. Triggers alert if retraining is recommended.

    Called daily by APScheduler.
    """
    from backend.infrastructure.database.connection import get_session_factory
    from backend.infrastructure.database.models.all_models import (
        ModelRegistryModel,
        ModelMonitoringModel,
        PredictionModel,
        FeatureVectorModel,
    )
    from sqlalchemy import select, and_, desc
    import uuid

    logger.info("monitoring_started")
    session_factory = get_session_factory()

    async with session_factory() as session:
        # ── 1. Get active model ───────────────────────────────────────────────
        stmt = (
            select(ModelRegistryModel)
            .where(ModelRegistryModel.status == "active")
            .order_by(desc(ModelRegistryModel.trained_at))
            .limit(1)
        )
        result = await session.execute(stmt)
        active_model = result.scalars().first()

        if not active_model:
            logger.warning("monitoring_no_active_model")
            return {"success": False, "reason": "No active model found."}

        baseline_accuracy = active_model.accuracy or 0.0
        baseline_f1 = active_model.f1_score or 0.0

        # ── 2. Data freshness ─────────────────────────────────────────────────
        stmt2 = (
            select(FeatureVectorModel.created_at)
            .order_by(desc(FeatureVectorModel.created_at))
            .limit(1)
        )
        r2 = await session.execute(stmt2)
        last_ingest = r2.scalars().first()
        data_freshness_hrs = None
        if last_ingest:
            data_freshness_hrs = round(
                (datetime.now(timezone.utc) - last_ingest).total_seconds() / 3600, 2
            )

        # ── 3. Feature drift (last 24h vs baseline window) ───────────────────
        now = datetime.now(timezone.utc)
        recent_cutoff = now - timedelta(hours=24)
        baseline_cutoff = now - timedelta(days=30)

        stmt3 = select(FeatureVectorModel.features).where(
            FeatureVectorModel.created_at >= recent_cutoff
        )
        stmt4 = select(FeatureVectorModel.features).where(
            and_(
                FeatureVectorModel.created_at >= baseline_cutoff,
                FeatureVectorModel.created_at < recent_cutoff,
            )
        )
        recent_rows = (await session.execute(stmt3)).scalars().all()
        baseline_rows = (await session.execute(stmt4)).scalars().all()

        overall_psi = 0.0
        feature_drift: dict[str, float] = {}

        if recent_rows and baseline_rows:
            from backend.ml.features.feature_definitions import FEATURE_NAMES
            baseline_feat = {f: [r.get(f, 0) for r in baseline_rows] for f in FEATURE_NAMES}
            current_feat = {f: [r.get(f, 0) for r in recent_rows] for f in FEATURE_NAMES}
            feature_drift = compute_feature_drift(baseline_feat, current_feat)
            overall_psi = round(float(np.mean(list(feature_drift.values()))), 4)

        # ── 4. Accuracy decay (approximate from risk_score distribution) ─────
        # True accuracy requires ground truth labels — here we use a proxy:
        # significant change in confidence distribution signals degradation
        stmt5 = select(PredictionModel.confidence).where(
            PredictionModel.created_at >= recent_cutoff
        )
        confs = (await session.execute(stmt5)).scalars().all()
        accuracy_current = round(float(np.mean(confs)), 4) if confs else baseline_accuracy
        accuracy_decay = round(baseline_accuracy - accuracy_current, 4)

        # ── 5. Determine if retraining is needed ─────────────────────────────
        drift_flag = overall_psi > settings.drift_alert_threshold
        decay_flag = accuracy_decay > settings.accuracy_decay_threshold
        freshness_flag = data_freshness_hrs is not None and data_freshness_hrs > 48
        retraining_recommended = drift_flag or decay_flag or freshness_flag

        reasons = []
        if drift_flag:
            reasons.append(f"Feature drift PSI={overall_psi} > threshold={settings.drift_alert_threshold}")
        if decay_flag:
            reasons.append(f"Accuracy decay={accuracy_decay} > threshold={settings.accuracy_decay_threshold}")
        if freshness_flag:
            reasons.append(f"Data stale: {data_freshness_hrs}h since last ingest (threshold: 48h)")

        # ── 6. Save monitoring record ─────────────────────────────────────────
        monitoring_record = ModelMonitoringModel(
            model_version_id=active_model.id,
            accuracy_current=accuracy_current,
            accuracy_baseline=baseline_accuracy,
            accuracy_decay=accuracy_decay,
            psi_score=overall_psi,
            feature_drift=feature_drift,
            data_freshness_hrs=data_freshness_hrs,
            retraining_recommended=retraining_recommended,
            alert_sent=False,
            report_json={
                "reasons": reasons,
                "drift_flag": drift_flag,
                "decay_flag": decay_flag,
                "freshness_flag": freshness_flag,
            },
        )
        session.add(monitoring_record)
        await session.commit()

    if retraining_recommended:
        logger.warning(
            "retraining_recommended",
            psi=overall_psi,
            accuracy_decay=accuracy_decay,
            reasons=reasons,
        )
    else:
        logger.info(
            "monitoring_passed",
            psi=overall_psi,
            accuracy_decay=accuracy_decay,
            data_freshness_hrs=data_freshness_hrs,
        )

    return {
        "success": True,
        "model_version": active_model.version,
        "psi_score": overall_psi,
        "accuracy_current": accuracy_current,
        "accuracy_baseline": baseline_accuracy,
        "accuracy_decay": accuracy_decay,
        "data_freshness_hrs": data_freshness_hrs,
        "retraining_recommended": retraining_recommended,
        "reasons": reasons,
    }
