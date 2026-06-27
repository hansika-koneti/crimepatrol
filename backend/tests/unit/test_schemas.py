"""
Unit tests — Pydantic settings validation + core exceptions.
These are pure unit tests with no IO.
"""
import os
import pytest


class TestCoreExceptions:
    """Test the CrimePatrol exception hierarchy."""

    def test_authentication_error_is_crimepatrol_error(self):
        from backend.core.exceptions import AuthenticationError, CrimePatrolError
        err = AuthenticationError("bad token")
        assert isinstance(err, CrimePatrolError)
        assert err.message == "bad token"

    def test_domain_error_with_details(self):
        from backend.core.exceptions import DomainError
        err = DomainError("invalid input", details={"field": "risk_score"})
        assert err.details == {"field": "risk_score"}

    def test_database_error(self):
        from backend.core.exceptions import DatabaseError
        err = DatabaseError("connection refused")
        assert "connection" in err.message.lower()

    def test_external_api_error_has_provider(self):
        from backend.core.exceptions import ExternalAPIError
        err = ExternalAPIError("timeout", provider="TomTom")
        assert err.provider == "TomTom"
        assert err.message == "timeout"


class TestSettingsValidation:
    """Test Settings pydantic model with env var overrides."""

    def test_defaults_loaded_from_env(self, monkeypatch):
        monkeypatch.setenv("APP_SECRET_KEY", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        from importlib import reload
        import backend.core.config as cfg_module
        reload(cfg_module)
        settings = cfg_module.Settings()
        assert settings.app_env == "development"
        assert settings.jwt_algorithm == "HS256"

    def test_secret_key_too_short_raises(self, monkeypatch):
        monkeypatch.setenv("APP_SECRET_KEY", "short")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/d")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        from pydantic import ValidationError
        from importlib import reload
        import backend.core.config as cfg_module
        reload(cfg_module)
        with pytest.raises(ValidationError):
            cfg_module.Settings()

    def test_allowed_origins_parsed_from_comma_string(self, monkeypatch):
        monkeypatch.setenv("APP_SECRET_KEY", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/d")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:5173,https://example.com")
        from importlib import reload
        import backend.core.config as cfg_module
        reload(cfg_module)
        settings = cfg_module.Settings()
        assert "http://localhost:5173" in settings.allowed_origins
        assert "https://example.com" in settings.allowed_origins


class TestSecurityModule:
    """Test JWT token creation and verification."""

    def test_create_and_verify_token(self, monkeypatch):
        monkeypatch.setenv("APP_SECRET_KEY", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/d")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        from backend.core.security import create_access_token, get_token_subject
        token = create_access_token(subject="admin@test.com")
        assert isinstance(token, str)
        subject = get_token_subject(token)
        assert subject == "admin@test.com"

    def test_invalid_token_returns_none(self):
        from backend.core.security import get_token_subject
        result = get_token_subject("not.a.real.token")
        assert result is None
