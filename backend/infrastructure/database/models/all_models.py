"""
CrimePatrol — ORM Models (SQLAlchemy + GeoAlchemy2)
Maps PostgreSQL tables to Python classes.
"""
import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.infrastructure.database.connection import Base

# PostgreSQL enum types that already exist in the DB — create_type=False
# prevents SQLAlchemy from trying to CREATE TYPE on startup.
RiskLevelEnum = Enum(
    "LOW", "MEDIUM", "HIGH", "CRITICAL",
    name="risk_level_enum", create_type=False
)
DataSourceEnum = Enum(
    "historical_csv", "scraper", "api", "manual",
    name="data_source_enum", create_type=False
)


class AreaModel(Base):
    __tablename__ = "areas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    city = Column(Text, nullable=False)
    country_code = Column(String(2), nullable=False, default="US")
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    centroid = Column(Geometry("POINT", srid=4326))
    population = Column(Integer)
    area_km2 = Column(Float)
    district_code = Column(Text)
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("name", "city", name="uq_areas_name_city"),)

    incidents = relationship("CrimeIncidentModel", back_populates="area", lazy="noload")
    predictions = relationship("PredictionModel", back_populates="area", lazy="noload")


class CrimeIncidentModel(Base):
    __tablename__ = "crime_incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    area_id = Column(UUID(as_uuid=True), ForeignKey("areas.id", ondelete="SET NULL"))
    crime_type = Column(Text, nullable=False)
    crime_category = Column(Text)
    severity = Column(SmallInteger)
    location = Column(Geometry("POINT", srid=4326), nullable=False)
    address = Column(Text)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    reported_at = Column(DateTime(timezone=True))
    source = Column(DataSourceEnum, nullable=False)
    source_url = Column(Text)
    source_id = Column(Text)
    raw_text = Column(Text)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_duplicate = Column(Boolean, default=False, nullable=False)
    city = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    area = relationship("AreaModel", back_populates="incidents", lazy="noload")


class FeatureVectorModel(Base):
    __tablename__ = "feature_vectors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    area_id = Column(UUID(as_uuid=True), ForeignKey("areas.id", ondelete="CASCADE"), nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_hours = Column(SmallInteger, nullable=False, default=3)
    features = Column(JSONB, nullable=False)
    feature_version = Column(Text, nullable=False, default="v1")
    is_training_data = Column(Boolean, nullable=False, default=False)
    label = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("area_id", "window_start", "feature_version", name="uq_fv_area_window_version"),
    )


class ModelRegistryModel(Base):
    __tablename__ = "model_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(Text, nullable=False, unique=True)
    algorithm = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="training")
    accuracy = Column(Float)
    precision_score = Column(Float)
    recall_score = Column(Float)
    f1_score = Column(Float)
    roc_auc = Column(Float)
    feature_version = Column(Text, nullable=False, default="v1")
    training_rows = Column(Integer)
    model_path = Column(Text)
    hyperparameters = Column(JSONB, default=dict)
    trained_at = Column(DateTime(timezone=True))
    city = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    monitoring_records = relationship("ModelMonitoringModel", back_populates="model", lazy="noload")


class PredictionModel(Base):
    __tablename__ = "predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    area_id = Column(UUID(as_uuid=True), ForeignKey("areas.id"), nullable=False)
    model_version_id = Column(UUID(as_uuid=True), ForeignKey("model_registry.id"))
    predicted_for = Column(DateTime(timezone=True), nullable=False)
    window_hours = Column(SmallInteger, nullable=False, default=3)
    risk_score = Column(Float)
    risk_level = Column(RiskLevelEnum, nullable=False)
    crime_type = Column(Text)
    confidence = Column(Float)
    probability_dist = Column(JSONB)
    feature_vector_id = Column(UUID(as_uuid=True), ForeignKey("feature_vectors.id"))
    shap_values = Column(JSONB)
    top_features = Column(JSONB)
    explanation_text = Column(Text)
    similar_cases = Column(JSONB)
    agent_run_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    area = relationship("AreaModel", back_populates="predictions", lazy="noload")
    recommendations = relationship("RecommendationModel", back_populates="prediction", lazy="noload")


class RecommendationModel(Base):
    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prediction_id = Column(UUID(as_uuid=True), ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False)
    action = Column(Text, nullable=False)
    category = Column(Text, nullable=False)
    priority = Column(Text, nullable=False)
    priority_score = Column(SmallInteger)
    reason = Column(Text)
    estimated_impact = Column(Text)
    is_actioned = Column(Boolean, default=False, nullable=False)
    actioned_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    prediction = relationship("PredictionModel", back_populates="recommendations", lazy="noload")


class WeatherSnapshotModel(Base):
    __tablename__ = "weather_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    area_id = Column(UUID(as_uuid=True), ForeignKey("areas.id"), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    temperature_c = Column(Float)
    feels_like_c = Column(Float)
    humidity_pct = Column(SmallInteger)
    condition = Column(Text)
    wind_kmh = Column(Float)
    visibility_km = Column(Float)
    uv_index = Column(SmallInteger)
    precipitation_mm = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("area_id", "recorded_at", name="uq_weather_area_time"),)


class TrafficSnapshotModel(Base):
    __tablename__ = "traffic_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    area_id = Column(UUID(as_uuid=True), ForeignKey("areas.id"), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    congestion_pct = Column(SmallInteger)
    incident_count = Column(SmallInteger)
    flow_speed_kmh = Column(Float)
    free_flow_speed = Column(Float)
    road_closures = Column(SmallInteger, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("area_id", "recorded_at", name="uq_traffic_area_time"),)


class IoTSnapshotModel(Base):
    __tablename__ = "iot_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    area_id = Column(UUID(as_uuid=True), ForeignKey("areas.id"), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    streetlight_pct = Column(SmallInteger)
    cctv_alert_count = Column(SmallInteger, default=0)
    cctv_operational = Column(SmallInteger)
    crowd_density = Column(Float)
    anomaly_detected = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("area_id", "recorded_at", name="uq_iot_area_time"),)


class ModelMonitoringModel(Base):
    __tablename__ = "model_monitoring"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_version_id = Column(UUID(as_uuid=True), ForeignKey("model_registry.id"), nullable=False)
    monitored_at = Column(DateTime(timezone=True), server_default=func.now())
    accuracy_current = Column(Float)
    accuracy_baseline = Column(Float)
    accuracy_decay = Column(Float)
    psi_score = Column(Float)
    feature_drift = Column(JSONB)
    data_freshness_hrs = Column(Float)
    retraining_recommended = Column(Boolean, nullable=False, default=False)
    alert_sent = Column(Boolean, nullable=False, default=False)
    report_json = Column(JSONB)

    model = relationship("ModelRegistryModel", back_populates="monitoring_records", lazy="noload")


class DataQualityReportModel(Base):
    __tablename__ = "data_quality_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_at = Column(DateTime(timezone=True), server_default=func.now())
    source = Column(Text, nullable=False)
    city = Column(Text)
    total_records = Column(Integer)
    duplicates_removed = Column(Integer, default=0)
    nulls_filled = Column(Integer, default=0)
    invalid_coords = Column(Integer, default=0)
    corrupted_records = Column(Integer, default=0)
    outliers_detected = Column(Integer, default=0)
    api_failures = Column(Integer, default=0)
    scraper_failures = Column(Integer, default=0)
    data_freshness_hrs = Column(Float)
    quality_score = Column(Float)
    report_json = Column(JSONB)
    triggered_by = Column(Text, default="scheduler")


class AgentExecutionLogModel(Base):
    __tablename__ = "agent_execution_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(UUID(as_uuid=True), nullable=False)
    agent_name = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)
    area_id = Column(UUID(as_uuid=True), ForeignKey("areas.id"))
    input_summary = Column(JSONB)
    output_summary = Column(JSONB)
    error_message = Column(Text)
    metadata_ = Column("metadata", JSONB, default=dict)


class DailyBriefingModel(Base):
    __tablename__ = "daily_briefings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    city = Column(Text, nullable=False)
    briefing_date = Column(DateTime(timezone=True), nullable=False)
    highest_risk_area = Column(Text)
    highest_risk_score = Column(Float)
    primary_crime_type = Column(Text)
    overall_risk_level = Column(RiskLevelEnum)
    avg_risk_score = Column(Float)
    avg_confidence = Column(Float)
    summary_text = Column(Text, nullable=False)
    top_recommendations = Column(JSONB)
    stats = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
