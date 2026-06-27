"""
CrimePatrol — ETL Pipeline (Application Use Case)
Orchestrates: Fetch → Clean → Validate → Deduplicate → Persist → Feature Store

Called by:
  - APScheduler (hourly cron)
  - POST /api/v1/etl/trigger (manual)
  - DataCollectionAgent in the LangGraph pipeline

Architecture: ETL is strictly separated from Prediction.
              Output lands in the Feature Store table, not directly in predictions.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.core.config import get_settings
from backend.core.observability.logger import get_logger
from backend.domain.entities.crime_incident import CrimeIncident, DataSource, GeoPoint
from backend.infrastructure.database.connection import get_session_factory
from backend.infrastructure.database.repositories.area_repository import SQLAreaRepository
from backend.infrastructure.database.repositories.crime_repository import SQLCrimeIncidentRepository
from backend.infrastructure.database.models.all_models import DataQualityReportModel

logger = get_logger(__name__)
settings = get_settings()


# ─── Adapter registry ─────────────────────────────────────────────────────────

def _get_crime_adapter():
    adapter_name = settings.city_adapter.lower()
    if adapter_name == "chicago":
        from backend.infrastructure.adapters.chicago_adapter import ChicagoCrimeAdapter
        return ChicagoCrimeAdapter()
    elif adapter_name == "generic_csv":
        from backend.infrastructure.adapters.generic_csv_adapter import GenericCSVAdapter
        return GenericCSVAdapter()
    raise ValueError(f"Unknown CITY_ADAPTER: '{adapter_name}'. Supported: chicago, generic_csv")


# ─── Data Quality Checks ───────────────────────────────────────────────────────

def _validate_raw_records(raw_records: list[Any], city_bbox: tuple) -> tuple[list, dict]:
    """
    Validates raw incident records and returns (valid_records, quality_stats).
    Checks: coordinate bounds, required fields, timestamp sanity.
    """
    min_lon, min_lat, max_lon, max_lat = city_bbox
    now = datetime.now(timezone.utc)
    cutoff_old = now - timedelta(days=365 * 10)   # no records older than 10 years

    valid, invalid_coords, missing_fields, future_dates, outliers = [], 0, 0, 0, 0

    for rec in raw_records:
        # Required fields
        if not rec.source_id or not rec.crime_type:
            missing_fields += 1
            continue

        # Coordinate validation against city bounding box
        if not (min_lon <= rec.longitude <= max_lon and min_lat <= rec.latitude <= max_lat):
            invalid_coords += 1
            continue

        # Timestamp sanity
        if rec.occurred_at > now + timedelta(hours=1):
            future_dates += 1
            continue
        if rec.occurred_at < cutoff_old:
            outliers += 1
            continue

        valid.append(rec)

    total = len(raw_records)
    quality_score = round((len(valid) / max(total, 1)) * 100, 2)

    stats = {
        "total_records": total,
        "valid_records": len(valid),
        "invalid_coords": invalid_coords,
        "missing_fields": missing_fields,
        "future_dates": future_dates,
        "outliers_detected": outliers,
        "quality_score": quality_score,
    }
    return valid, stats


# ─── ETL Pipeline ─────────────────────────────────────────────────────────────

async def run_etl_pipeline(hours_back: int = 24, limit: int = 2000) -> dict:
    """
    Main ETL entrypoint. Fetches, validates, deduplicates, and persists incidents.

    Returns:
        dict with ETL run statistics.
    """
    run_start = datetime.now(timezone.utc)
    logger.info("etl_pipeline_started", hours_back=hours_back, city=settings.city_name)

    adapter = _get_crime_adapter()
    city_bbox = settings.city_bbox

    # ── 1. Fetch ──────────────────────────────────────────────────────────────
    try:
        raw_records = await adapter.fetch_recent(hours_back=hours_back, limit=limit)
    except Exception as exc:
        logger.error("etl_fetch_failed", error=str(exc))
        return {"success": False, "error": str(exc)}

    # ── 2. Validate + Clean ───────────────────────────────────────────────────
    valid_records, quality_stats = _validate_raw_records(raw_records, city_bbox)
    logger.info("etl_validation_done", **quality_stats)

    # ── 3. Convert to Domain Entities ─────────────────────────────────────────
    incidents: list[CrimeIncident] = []
    for rec in valid_records:
        incidents.append(
            CrimeIncident(
                id=uuid.uuid4(),
                crime_type=rec.crime_type,
                crime_category=rec.crime_category,
                location=GeoPoint(longitude=rec.longitude, latitude=rec.latitude),
                occurred_at=rec.occurred_at,
                source=DataSource.HISTORICAL_CSV if hours_back > 48 else DataSource.API,
                city=adapter.city_name,
                severity=rec.severity,
                address=rec.address,
                source_id=rec.source_id,
                raw_text=rec.raw_text,
                metadata=rec.extra or {},
            )
        )

    # ── 4. Persist (deduplicate on insert) ────────────────────────────────────
    session_factory = get_session_factory()
    async with session_factory() as session:
        crime_repo = SQLCrimeIncidentRepository(session)
        area_repo = SQLAreaRepository(session)

        # Assign area_id via PostGIS spatial lookup
        for incident in incidents:
            area = await area_repo.find_by_point(
                incident.location.longitude, incident.location.latitude
            )
            if area:
                incident.area_id = area.id

        saved_count = await crime_repo.save_batch(incidents)

        # ── 5. Save Data Quality Report ───────────────────────────────────────
        dq_report = DataQualityReportModel(
            source=adapter.city_name,
            city=adapter.city_name,
            total_records=quality_stats["total_records"],
            duplicates_removed=quality_stats["total_records"] - quality_stats["valid_records"] - saved_count,
            nulls_filled=quality_stats["missing_fields"],
            invalid_coords=quality_stats["invalid_coords"],
            corrupted_records=0,
            outliers_detected=quality_stats["outliers_detected"],
            quality_score=quality_stats["quality_score"],
            report_json=quality_stats,
            triggered_by="scheduler",
        )
        session.add(dq_report)
        await session.commit()

    duration_s = round((datetime.now(timezone.utc) - run_start).total_seconds(), 2)
    result = {
        "success": True,
        "city": adapter.city_name,
        "fetched": len(raw_records),
        "valid": len(valid_records),
        "saved": saved_count,
        "quality_score": quality_stats["quality_score"],
        "duration_seconds": duration_s,
    }
    logger.info("etl_pipeline_completed", **result)
    return result
