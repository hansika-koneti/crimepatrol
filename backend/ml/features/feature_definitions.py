"""
CrimePatrol — Feature Definitions (Feature Store Schema v1)
Single source of truth for all ML features.
Both training and inference must use this module — never hardcode feature names elsewhere.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any


class FeatureType(str, Enum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    BINARY = "binary"


@dataclass(frozen=True)
class FeatureDef:
    name: str
    dtype: FeatureType
    description: str
    default: Any = 0


# =============================================================================
# FEATURE SCHEMA v1
# =============================================================================

FEATURE_SCHEMA_VERSION = "v1"

FEATURES: list[FeatureDef] = [
    # ── Temporal ────────────────────────────────────────────────────────────
    FeatureDef("hour_of_day",        FeatureType.NUMERIC,      "Hour of day (0–23)",                     0),
    FeatureDef("day_of_week",        FeatureType.NUMERIC,      "Day of week (0=Mon, 6=Sun)",              0),
    FeatureDef("month",              FeatureType.NUMERIC,      "Month (1–12)",                            1),
    FeatureDef("is_weekend",         FeatureType.BINARY,       "1 if Saturday or Sunday",                 0),
    FeatureDef("is_holiday",         FeatureType.BINARY,       "1 if public holiday",                     0),
    FeatureDef("is_night",           FeatureType.BINARY,       "1 if hour >= 22 or hour < 5",             0),
    FeatureDef("season",             FeatureType.NUMERIC,      "Season (0=winter 1=spring 2=summer 3=fall)", 0),

    # ── Crime History ────────────────────────────────────────────────────────
    FeatureDef("incident_count_24h", FeatureType.NUMERIC,      "Incidents in this area in last 24 hours", 0),
    FeatureDef("incident_count_7d",  FeatureType.NUMERIC,      "Incidents in this area in last 7 days",   0),
    FeatureDef("incident_count_30d", FeatureType.NUMERIC,      "Incidents in this area in last 30 days",  0),
    FeatureDef("theft_pct_7d",       FeatureType.NUMERIC,      "% theft incidents in last 7 days",        0.0),
    FeatureDef("violent_pct_7d",     FeatureType.NUMERIC,      "% violent incidents in last 7 days",      0.0),
    FeatureDef("rolling_avg_daily",  FeatureType.NUMERIC,      "Rolling 7-day avg daily incidents",       0.0),

    # ── Weather ─────────────────────────────────────────────────────────────
    FeatureDef("temperature_c",      FeatureType.NUMERIC,      "Temperature in Celsius",                  15.0),
    FeatureDef("humidity_pct",       FeatureType.NUMERIC,      "Relative humidity percentage",            50),
    FeatureDef("wind_kmh",           FeatureType.NUMERIC,      "Wind speed km/h",                         10.0),
    FeatureDef("precipitation_mm",   FeatureType.NUMERIC,      "Precipitation in mm",                     0.0),
    FeatureDef("visibility_km",      FeatureType.NUMERIC,      "Visibility in km",                        10.0),
    FeatureDef("is_rainy",           FeatureType.BINARY,       "1 if condition is rain or storm",         0),
    FeatureDef("is_foggy",           FeatureType.BINARY,       "1 if condition is fog",                   0),

    # ── Traffic ─────────────────────────────────────────────────────────────
    FeatureDef("congestion_pct",     FeatureType.NUMERIC,      "Traffic congestion percentage",           20),
    FeatureDef("traffic_incidents",  FeatureType.NUMERIC,      "Number of traffic incidents nearby",      0),
    FeatureDef("road_closures",      FeatureType.NUMERIC,      "Number of road closures",                 0),

    # ── Events ──────────────────────────────────────────────────────────────
    FeatureDef("has_event",          FeatureType.BINARY,       "1 if public event in this area",          0),
    FeatureDef("event_crowd_size",   FeatureType.NUMERIC,      "Expected crowd size (0 if no event)",     0),
    FeatureDef("event_crowd_bucket", FeatureType.NUMERIC,      "0=none 1=small 2=medium 3=large 4=massive", 0),

    # ── IoT / Infrastructure ─────────────────────────────────────────────────
    FeatureDef("streetlight_pct",    FeatureType.NUMERIC,      "% of streetlights operational",           92),
    FeatureDef("cctv_alert_count",   FeatureType.NUMERIC,      "Number of active CCTV alerts",            0),
    FeatureDef("cctv_operational",   FeatureType.NUMERIC,      "Number of operational CCTV cameras",      8),
    FeatureDef("crowd_density",      FeatureType.NUMERIC,      "People per 100m² (crowd density sensor)", 1.0),
    FeatureDef("iot_anomaly",        FeatureType.BINARY,       "1 if IoT anomaly detected",               0),

    # ── Area / Spatial ───────────────────────────────────────────────────────
    FeatureDef("population_density", FeatureType.NUMERIC,      "Population per km²",                      5000.0),
]

# Feature names list (used by sklearn Pipeline and SHAP)
FEATURE_NAMES: list[str] = [f.name for f in FEATURES]

# Defaults dict for missing value imputation
FEATURE_DEFAULTS: dict[str, Any] = {f.name: f.default for f in FEATURES}

# Categorical features that need encoding (currently none — all numeric/binary)
CATEGORICAL_FEATURES: list[str] = [
    f.name for f in FEATURES if f.dtype == FeatureType.CATEGORICAL
]

# Numeric features for scaling
NUMERIC_FEATURES: list[str] = [
    f.name for f in FEATURES if f.dtype in (FeatureType.NUMERIC, FeatureType.BINARY)
]

TARGET_COLUMN = "risk_level"
RISK_LEVEL_CLASSES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
RISK_LEVEL_ENCODING = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
RISK_LEVEL_DECODING = {v: k for k, v in RISK_LEVEL_ENCODING.items()}
