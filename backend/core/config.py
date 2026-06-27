"""
CrimePatrol Backend — Pydantic Settings
All configuration comes from environment variables / .env file.
Business logic must import from here, never from os.environ directly.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    app_env: Literal["development", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_secret_key: str = Field(..., min_length=32)
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # -------------------------------------------------------------------------
    # JWT
    # -------------------------------------------------------------------------
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440

    # -------------------------------------------------------------------------
    # Admin
    # -------------------------------------------------------------------------
    admin_email: str = "admin@crimepatrol.local"
    admin_password: str = "changeme123"

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "crimepatrol"
    postgres_user: str = "crimepatrol"
    postgres_password: str = "crimepatrol_secret"
    database_url: str = "postgresql+asyncpg://crimepatrol:crimepatrol_secret@localhost:5432/crimepatrol"

    # -------------------------------------------------------------------------
    # Redis
    # -------------------------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl_seconds: int = 3600

    # -------------------------------------------------------------------------
    # City Configuration (city-agnostic adapter pattern)
    # -------------------------------------------------------------------------
    city_adapter: str = "chicago"
    city_name: str = "Chicago"
    city_bounding_box: str = "-87.94,41.64,-87.52,42.02"
    city_timezone: str = "America/Chicago"

    @property
    def city_bbox(self) -> tuple[float, float, float, float]:
        """Returns (min_lon, min_lat, max_lon, max_lat)."""
        parts = [float(x) for x in self.city_bounding_box.split(",")]
        return tuple(parts)  # type: ignore

    # -------------------------------------------------------------------------
    # Chicago Open Data
    # -------------------------------------------------------------------------
    chicago_data_portal_url: str = (
        "https://data.cityofchicago.org/resource/ijzp-q8t2.json"
    )
    chicago_data_app_token: str = ""

    # -------------------------------------------------------------------------
    # LLM — Google Gemini
    # -------------------------------------------------------------------------
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # -------------------------------------------------------------------------
    # Weather — Open-Meteo (no key required)
    # -------------------------------------------------------------------------
    open_meteo_base_url: str = "https://api.open-meteo.com/v1/forecast"

    # -------------------------------------------------------------------------
    # Traffic — TomTom
    # -------------------------------------------------------------------------
    tomtom_api_key: str = ""
    tomtom_base_url: str = "https://api.tomtom.com/traffic/services/4"

    # -------------------------------------------------------------------------
    # Events — Ticketmaster
    # -------------------------------------------------------------------------
    ticketmaster_api_key: str = ""
    ticketmaster_base_url: str = "https://app.ticketmaster.com/discovery/v2"

    # -------------------------------------------------------------------------
    # Holidays — Nager.Date (no key required)
    # -------------------------------------------------------------------------
    nager_date_base_url: str = "https://date.nager.at/api/v3"
    holiday_country_code: str = "US"

    # -------------------------------------------------------------------------
    # Scheduler
    # -------------------------------------------------------------------------
    scheduler_backend: Literal["apscheduler", "airflow"] = "apscheduler"
    etl_cron: str = "0 * * * *"
    monitoring_cron: str = "0 6 * * *"
    daily_report_cron: str = "0 7 * * *"

    # -------------------------------------------------------------------------
    # Machine Learning
    # -------------------------------------------------------------------------
    model_registry_path: str = "backend/ml/saved_models"
    feature_schema_version: str = "v1"
    drift_alert_threshold: float = 0.2
    accuracy_decay_threshold: float = 0.05

    # -------------------------------------------------------------------------
    # Observability
    # -------------------------------------------------------------------------
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"
    metrics_enabled: bool = True

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns a cached Settings singleton.
    Use this everywhere instead of instantiating Settings() directly.
    """
    return Settings()
