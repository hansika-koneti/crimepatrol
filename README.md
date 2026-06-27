# ⚡ CrimePatrol — AI-Powered Smart City Safety Analytics Platform

[![CrimePatrol CI](https://github.com/your-org/crimepatrol/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/crimepatrol/actions)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.0-3178c6?logo=typescript)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61dafb?logo=react)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

CrimePatrol is a full-stack, city-agnostic AI platform that predicts crime risk for geographic areas using machine learning (XGBoost + SHAP), orchestrates multi-agent pipelines via LangGraph, and presents results through a real-time React dashboard with Leaflet maps and Recharts analytics.

---

## Architecture

```mermaid
graph TB
    subgraph Frontend ["Frontend (React 19 + Vite)"]
        A[Dashboard Page] --> B[Leaflet Map]
        A --> C[Recharts Charts]
        A --> D[XAI Panel]
        A --> E[Recommendation Panel]
        F[Zustand Store] --- A
        G[WebSocket Hook] --> F
    end

    subgraph Backend ["Backend (FastAPI + Python 3.11)"]
        H[REST API v1] --> I[Application Layer]
        I --> J[Domain Layer]
        I --> K[ML Engine]
        K --> L[XGBoost Model]
        K --> M[SHAP Explainer]
        I --> N[LangGraph Agents]
        N --> O[ETL Agent]
        N --> P[Prediction Agent]
        N --> Q[Report Agent]
        H --> R[WebSocket /ws]
    end

    subgraph Infra ["Infrastructure"]
        S[(PostgreSQL + PostGIS)]
        T[(Redis)]
        U[APScheduler]
    end

    Frontend -->|REST + WS| Backend
    Backend --> S
    Backend --> T
    U --> N
```

---

## Feature Summary

| Module | Description |
|--------|-------------|
| **ETL Pipeline** | Multi-source data ingestion (city open data, weather, events, traffic) with quality scoring |
| **ML Engine** | XGBoost risk scorer with SHAP explainability + feature engineering |
| **LangGraph Agents** | Orchestrated agents: ETL → Predict → Explain → Recommend → Report |
| **Gemini LLM** | Natural-language prediction explanations and daily briefing synthesis |
| **REST API** | FastAPI v1 endpoints with JWT auth, pagination, structured error responses |
| **WebSocket** | Live dashboard stream — real-time prediction push to connected clients |
| **React Dashboard** | 5-page SPA: Dashboard, Live Map, Predict Workbench, Reports, System Health |
| **Leaflet Map** | Interactive crime risk map with heatmap overlay and area markers |
| **Recharts** | AreaChart trends, BarChart crime types, RadarChart probability distribution |
| **Framer Motion** | Smooth page transitions, stagger animations, animated metric counters |
| **Data Quality** | Drift detection (KS test), duplicate removal, quality score reporting |
| **CI/CD** | GitHub Actions: lint (Ruff/oxlint), type-check (mypy/tsc), test, docker validate, build |

---

## Prerequisites

| Tool | Version |
|------|---------|
| [Docker Desktop](https://www.docker.com/) | ≥ 24 |
| [Docker Compose](https://docs.docker.com/compose/) | ≥ 2.20 (bundled with Docker Desktop) |
| [Node.js](https://nodejs.org/) | 20 LTS (for local frontend dev) |
| [Python](https://www.python.org/) | 3.11 (for local backend dev) |
| [Git](https://git-scm.com/) | Any |

---

## Quick Start (Docker Compose)

```bash
# 1. Clone
git clone https://github.com/your-org/crimepatrol.git
cd crimepatrol

# 2. Configure environment
cp .env.example .env
# Edit .env and set at minimum:
#   APP_SECRET_KEY  (≥32 chars)
#   GEMINI_API_KEY  (Google AI Studio)

# 3. Launch all services
docker compose up -d

# 4. Open
# Frontend:  http://localhost:5173
# API docs:  http://localhost:8000/api/docs
# Health:    http://localhost:8000/health
```

Default admin credentials: `admin@crimepatrol.local` / `changeme123` (set via `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env`).

---

## Local Development

### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Start services (Postgres + Redis only)
docker compose up postgres redis -d

# Run FastAPI dev server
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install
npm install

# Dev server (proxies /api → localhost:8000)
npm run dev

# Type check
npm run type-check

# Run tests
npm test

# Build for production
npm run build
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_SECRET_KEY` | ✅ | — | JWT signing key (≥32 chars) |
| `DATABASE_URL` | ✅ | — | `postgresql+asyncpg://user:pass@host/db` |
| `REDIS_URL` | ✅ | — | `redis://localhost:6379/0` |
| `GEMINI_API_KEY` | ✅ | — | Google Gemini API key |
| `APP_ENV` | ❌ | `development` | `development` or `production` |
| `ADMIN_EMAIL` | ❌ | `admin@crimepatrol.local` | Dashboard admin email |
| `ADMIN_PASSWORD` | ❌ | `changeme123` | Dashboard admin password |
| `CITY_NAME` | ❌ | `Chicago` | Display city name |
| `CITY_ADAPTER` | ❌ | `chicago` | Data source adapter (`chicago`, `nyc`, etc.) |
| `TOMTOM_API_KEY` | ❌ | — | Traffic data (optional enrichment) |
| `TICKETMASTER_API_KEY` | ❌ | — | Events data (optional enrichment) |
| `ETL_CRON` | ❌ | `0 */6 * * *` | ETL pipeline schedule |
| `MONITORING_CRON` | ❌ | `0 2 * * *` | Model drift monitoring schedule |
| `DAILY_REPORT_CRON` | ❌ | `0 7 * * *` | Daily briefing generation schedule |

See [`.env.example`](.env.example) for the full list.

---

## API Reference

Full interactive docs are available at **`/api/docs`** (Swagger UI) when the backend is running.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/login` | Obtain JWT token |
| `GET` | `/health` | System health status |
| `GET` | `/api/v1/areas` | List all monitored areas |
| `GET` | `/api/v1/areas/{id}/prediction` | Latest prediction for an area |
| `POST` | `/api/v1/predictions/run` | Run prediction for an area |
| `GET` | `/api/v1/predictions/history` | Prediction history |
| `GET` | `/api/v1/analytics/high-risk` | Top-N high-risk areas |
| `GET` | `/api/v1/analytics/heatmap` | GeoJSON heatmap data |
| `GET` | `/api/v1/reports/daily` | Daily briefing reports |
| `GET` | `/api/v1/agents/status` | Agent pipeline run logs |
| `GET` | `/api/v1/quality/reports` | Data quality reports |
| `POST` | `/api/v1/etl/trigger` | Manually trigger ETL |
| `WS` | `/ws/dashboard` | Live push stream |

---

## Project Structure

```
crimepatrol/
├── backend/
│   ├── api/v1/
│   │   ├── controllers/        # FastAPI routers
│   │   ├── schemas/            # Pydantic request/response models
│   │   └── websockets/         # WebSocket handlers
│   ├── agents/                 # LangGraph agent graphs
│   ├── application/            # Use-case orchestration
│   ├── core/                   # Config, exceptions, middleware, security
│   ├── domain/                 # Entities, value objects, ports (pure Python)
│   ├── infrastructure/         # DB, Redis, external API adapters
│   ├── ml/                     # Feature engineering, XGBoost, SHAP
│   ├── tests/
│   │   ├── fixtures/           # Shared pytest fixtures
│   │   ├── unit/               # Domain + core unit tests
│   │   └── integration/        # API integration tests
│   ├── main.py                 # FastAPI app factory
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── charts/         # RiskTrendChart, CrimeTypeChart, ProbabilityRadar
│   │   │   ├── layout/         # Sidebar, TopBar
│   │   │   └── panels/         # MetricCard, XAIPanel, RecommendationPanel
│   │   ├── hooks/              # useWebSocket
│   │   ├── pages/              # Dashboard, Map, Predict, Reports, Health
│   │   ├── services/           # API client (fetch wrappers)
│   │   ├── store/              # Zustand global state
│   │   └── utils/              # constants, helpers
│   ├── package.json
│   └── vite.config.ts
│
├── docker/
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   ├── nginx.conf
│   └── postgres/init.sql
│
├── .github/workflows/ci.yml   # GitHub Actions CI
├── docker-compose.yml
└── .env.example
```

---

## Running Tests

### Backend

```bash
cd backend

# All tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# With coverage report
pytest tests/ --cov=. --cov-report=html
# Open htmlcov/index.html
```

### Frontend

```bash
cd frontend

# Run all tests
npm test

# Watch mode
npm run test:watch

# Type check only
npm run type-check
```

---

## CI/CD Pipeline

GitHub Actions runs on every push to `main` / `develop` and all PRs:

1. **`docker-validate`** — Validates `docker-compose.yml` syntax
2. **`backend`** — Ruff lint → MyPy type check → pytest with live Postgres + Redis services
3. **`frontend`** — `tsc --noEmit` → oxlint → Vitest → `vite build`

---

## Modules Built

| # | Module | Status |
|---|--------|--------|
| 1 | Project scaffold & architecture | ✅ |
| 2 | Domain entities (Area, Prediction, Recommendation) | ✅ |
| 3 | Infrastructure: PostgreSQL + PostGIS schema | ✅ |
| 4 | Infrastructure: Redis cache | ✅ |
| 5 | ETL pipeline + city data adapters | ✅ |
| 6 | ML engine: XGBoost + SHAP | ✅ |
| 7 | LangGraph agent orchestration | ✅ |
| 8 | Gemini LLM integration (explanations + briefings) | ✅ |
| 9 | FastAPI REST controllers + WebSocket | ✅ |
| 10 | Data quality monitoring + drift detection | ✅ |
| 11 | **Frontend React dashboard (this module)** | ✅ |
| 12 | **Docker Compose validation + CI fixes** | ✅ |
| 13 | **Tests + README** | ✅ |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, TypeScript 6, Vite 8, Tailwind CSS 4 |
| **State** | Zustand 5 |
| **Map** | Leaflet 1.9 + react-leaflet 5 |
| **Charts** | Recharts 3 |
| **Animations** | Framer Motion 12 |
| **Backend** | FastAPI 0.111, Python 3.11 |
| **Database** | PostgreSQL 16 + PostGIS 3.4 via SQLAlchemy 2.0 (asyncpg) |
| **Cache** | Redis 7.2 (hiredis) |
| **ML** | XGBoost 2, scikit-learn 1.4, SHAP 0.45, pandas 2.2 |
| **AI** | LangGraph 0.1, LangChain-Google-GenAI, Gemini |
| **Auth** | JWT (python-jose), bcrypt (passlib) |
| **Scheduler** | APScheduler 3.10 |
| **Observability** | structlog |
| **CI/CD** | GitHub Actions, Docker Compose |
| **Testing** | pytest, pytest-asyncio, Vitest, @testing-library/react |

---

## License

MIT © 2025 CrimePatrol Contributors
