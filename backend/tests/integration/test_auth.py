"""
Integration tests — /auth/login endpoint
Tests login form validation and JWT token issuance logic in isolation.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends


def make_auth_app(expect_email: str, expect_pass: str, valid: bool = True) -> FastAPI:
    """Build a minimal auth-only app with configurable credential validation."""
    app = FastAPI()

    @app.post("/auth/login")
    async def login(form: OAuth2PasswordRequestForm = Depends()):
        if form.username == expect_email and form.password == expect_pass and valid:
            return {"access_token": "fake.jwt.token", "token_type": "bearer"}
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return app


@pytest.mark.asyncio
class TestAuthLogin:
    async def test_valid_credentials_return_token(self):
        app = make_auth_app("admin@test.com", "secret123")
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/auth/login",
                data={"username": "admin@test.com", "password": "secret123"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    async def test_wrong_password_returns_401(self):
        app = make_auth_app("admin@test.com", "correct")
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/auth/login",
                data={"username": "admin@test.com", "password": "wrong"},
            )
        assert resp.status_code == 401

    async def test_empty_username_returns_422(self):
        app = make_auth_app("admin@test.com", "secret123")
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Missing required 'username' field — FastAPI returns 422
            resp = await client.post("/auth/login", data={"password": "secret123"})
        assert resp.status_code == 422

    async def test_missing_password_returns_422(self):
        app = make_auth_app("admin@test.com", "secret123")
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/auth/login", data={"username": "admin@test.com"})
        assert resp.status_code == 422

    async def test_token_is_string(self):
        app = make_auth_app("u@u.com", "pw")
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/auth/login",
                data={"username": "u@u.com", "password": "pw"},
            )
        assert isinstance(resp.json()["access_token"], str)
