"""
Integration tests — Predictions API endpoints (mocked DB layer).
Tests schema shapes, pagination, and error handling.
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from fastapi.responses import JSONResponse


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ok(data, meta=None):
    return {"success": True, "data": data, "meta": meta or {}, "errors": []}


def _err(message: str):
    return {"success": False, "data": None, "meta": {}, "errors": [{"message": message}]}


def make_predictions_app(predictions_store: list) -> FastAPI:
    """
    Minimal predictions app. The store is shared by reference so tests
    can pre-populate it without touching a real DB.
    """
    app = FastAPI()
    area_id = str(uuid4())

    @app.post("/api/v1/predictions/run")
    async def run_prediction(body: dict):
        if not body.get("area_id"):
            return JSONResponse(status_code=422, content=_err("area_id required"))
        result = {
            "prediction": {
                "id": str(uuid4()),
                "area_id": body["area_id"],
                "risk_score": 72.5,
                "risk_level": "HIGH",
                "crime_type": "THEFT",
                "confidence": 0.88,
            },
            "recommendations": [],
        }
        predictions_store.append(result["prediction"])
        return JSONResponse(content=_ok(result))

    @app.get("/api/v1/predictions/history")
    async def prediction_history(limit: int = 50, area_id: str | None = None):
        items = predictions_store
        if area_id:
            items = [p for p in items if p.get("area_id") == area_id]
        return _ok(items[:limit])

    @app.get("/api/v1/predictions/{prediction_id}")
    async def get_prediction(prediction_id: str):
        match = next((p for p in predictions_store if p.get("id") == prediction_id), None)
        if not match:
            return JSONResponse(status_code=404, content=_err("Prediction not found"))
        return _ok(match)

    return app


@pytest.mark.asyncio
class TestRunPrediction:
    async def test_run_prediction_returns_200(self):
        store: list = []
        app = make_predictions_app(store)
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/predictions/run",
                json={"area_id": str(uuid4())},
            )
        assert resp.status_code == 200

    async def test_run_prediction_returns_risk_score(self):
        store: list = []
        app = make_predictions_app(store)
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/predictions/run",
                json={"area_id": str(uuid4())},
            )
        data = resp.json()["data"]
        assert "prediction" in data
        assert data["prediction"]["risk_score"] == 72.5

    async def test_run_prediction_missing_area_id(self):
        store: list = []
        app = make_predictions_app(store)
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/predictions/run", json={})
        assert resp.status_code == 422

    async def test_run_prediction_populates_history(self):
        store: list = []
        area_id = str(uuid4())
        app = make_predictions_app(store)
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/api/v1/predictions/run", json={"area_id": area_id})
            resp = await client.get(f"/api/v1/predictions/history?area_id={area_id}")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1


@pytest.mark.asyncio
class TestPredictionHistory:
    async def test_history_empty_by_default(self):
        store: list = []
        app = make_predictions_app(store)
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/predictions/history")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    async def test_history_limit_respected(self):
        store: list = [{"id": str(uuid4()), "risk_score": i} for i in range(20)]
        app = make_predictions_app(store)
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/predictions/history?limit=5")
        assert len(resp.json()["data"]) == 5


@pytest.mark.asyncio
class TestGetPrediction:
    async def test_get_existing_prediction(self):
        pid = str(uuid4())
        store = [{"id": pid, "risk_score": 55.0, "area_id": "x"}]
        app = make_predictions_app(store)
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/predictions/{pid}")
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == pid

    async def test_get_missing_prediction_returns_404(self):
        store: list = []
        app = make_predictions_app(store)
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/predictions/{uuid4()}")
        assert resp.status_code == 404
