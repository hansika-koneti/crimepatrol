-- =============================================================================
-- CrimePatrol — PostgreSQL + PostGIS Initialization Script
-- Runs automatically when the Docker container first starts.
-- =============================================================================

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";    -- for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- for text similarity searches

-- =============================================================================
-- ENUM TYPES
-- =============================================================================

CREATE TYPE risk_level_enum AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
CREATE TYPE recommendation_priority AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
CREATE TYPE recommendation_category AS ENUM ('patrol', 'infrastructure', 'alert', 'traffic', 'cctv');
CREATE TYPE data_source_enum AS ENUM ('historical_csv', 'scraper', 'api', 'manual');
CREATE TYPE model_status_enum AS ENUM ('training', 'active', 'archived', 'failed');

-- =============================================================================
-- AREAS (city zones / neighborhoods)
-- =============================================================================

CREATE TABLE areas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    city            TEXT NOT NULL,
    country_code    CHAR(2) NOT NULL DEFAULT 'US',
    geom            GEOMETRY(MULTIPOLYGON, 4326),        -- PostGIS polygon boundary
    centroid        GEOMETRY(POINT, 4326),               -- computed centroid for fast queries
    population      INTEGER,
    area_km2        NUMERIC(10, 4),
    district_code   TEXT,                                -- city-specific district identifier
    metadata        JSONB DEFAULT '{}',                  -- city-specific extra fields
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_areas_geom     ON areas USING GIST(geom);
CREATE INDEX idx_areas_centroid ON areas USING GIST(centroid);
CREATE INDEX idx_areas_city     ON areas (city);
CREATE UNIQUE INDEX idx_areas_name_city ON areas (name, city);

-- =============================================================================
-- CRIME INCIDENTS (raw — historical + scraped + api)
-- =============================================================================

CREATE TABLE crime_incidents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    area_id         UUID REFERENCES areas(id) ON DELETE SET NULL,
    crime_type      TEXT NOT NULL,
    crime_category  TEXT,                                -- normalized grouping (e.g. 'theft', 'assault')
    severity        SMALLINT CHECK (severity BETWEEN 1 AND 5),
    location        GEOMETRY(POINT, 4326) NOT NULL,
    address         TEXT,
    occurred_at     TIMESTAMPTZ NOT NULL,
    reported_at     TIMESTAMPTZ,
    source          data_source_enum NOT NULL,
    source_url      TEXT,
    source_id       TEXT,                                -- original ID from source system
    raw_text        TEXT,
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    is_duplicate    BOOLEAN NOT NULL DEFAULT FALSE,
    city            TEXT NOT NULL,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_incidents_location       ON crime_incidents USING GIST(location);
CREATE INDEX idx_incidents_area_time      ON crime_incidents (area_id, occurred_at DESC);
CREATE INDEX idx_incidents_type           ON crime_incidents (crime_type);
CREATE INDEX idx_incidents_category       ON crime_incidents (crime_category);
CREATE INDEX idx_incidents_city_time      ON crime_incidents (city, occurred_at DESC);
CREATE INDEX idx_incidents_occurred_at    ON crime_incidents (occurred_at DESC);
CREATE UNIQUE INDEX idx_incidents_source_dedup ON crime_incidents (source, source_id)
    WHERE source_id IS NOT NULL;

-- =============================================================================
-- FEATURE STORE (precomputed ML feature vectors)
-- =============================================================================

CREATE TABLE feature_vectors (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    area_id          UUID NOT NULL REFERENCES areas(id) ON DELETE CASCADE,
    window_start     TIMESTAMPTZ NOT NULL,
    window_hours     SMALLINT NOT NULL DEFAULT 3,
    features         JSONB NOT NULL,                     -- full feature dict
    feature_version  TEXT NOT NULL DEFAULT 'v1',         -- schema version for compatibility
    is_training_data BOOLEAN NOT NULL DEFAULT FALSE,
    label            TEXT,                               -- risk_level if labeled (for training)
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_fv_area_window_version
    ON feature_vectors (area_id, window_start, feature_version);
CREATE INDEX idx_fv_window_start ON feature_vectors (window_start DESC);
CREATE INDEX idx_fv_training     ON feature_vectors (is_training_data) WHERE is_training_data = TRUE;

-- =============================================================================
-- MODEL REGISTRY
-- =============================================================================

CREATE TABLE model_registry (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version         TEXT NOT NULL UNIQUE,               -- e.g. 'v1.0.0-20240627'
    algorithm       TEXT NOT NULL,                      -- 'random_forest' | 'xgboost' | 'gradient_boosting'
    status          model_status_enum NOT NULL DEFAULT 'training',
    accuracy        NUMERIC(6, 4),
    precision_score NUMERIC(6, 4),
    recall_score    NUMERIC(6, 4),
    f1_score        NUMERIC(6, 4),
    roc_auc         NUMERIC(6, 4),
    feature_version TEXT NOT NULL DEFAULT 'v1',
    training_rows   INTEGER,
    model_path      TEXT,                               -- filesystem path to .pkl
    hyperparameters JSONB DEFAULT '{}',
    trained_at      TIMESTAMPTZ,
    city            TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_model_status ON model_registry (status, trained_at DESC);

-- =============================================================================
-- PREDICTIONS
-- =============================================================================

CREATE TABLE predictions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    area_id             UUID NOT NULL REFERENCES areas(id),
    model_version_id    UUID REFERENCES model_registry(id),
    predicted_for       TIMESTAMPTZ NOT NULL,
    window_hours        SMALLINT NOT NULL DEFAULT 3,
    risk_score          NUMERIC(5, 2) CHECK (risk_score BETWEEN 0 AND 100),
    risk_level          risk_level_enum NOT NULL,
    crime_type          TEXT,
    confidence          NUMERIC(4, 3) CHECK (confidence BETWEEN 0 AND 1),
    probability_dist    JSONB,                          -- {"LOW":0.05,"MEDIUM":0.08,"HIGH":0.87,"CRITICAL":0.0}
    feature_vector_id   UUID REFERENCES feature_vectors(id),
    shap_values         JSONB,
    top_features        JSONB,                          -- [{feature, contribution, direction}]
    explanation_text    TEXT,                           -- LLM narrative
    similar_cases       JSONB,                          -- [{date, area, outcome, similarity}]
    agent_run_id        UUID,                           -- LangGraph run identifier
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_predictions_area_time  ON predictions (area_id, predicted_for DESC);
CREATE INDEX idx_predictions_risk       ON predictions (risk_level, predicted_for DESC);
CREATE INDEX idx_predictions_score      ON predictions (risk_score DESC);
CREATE INDEX idx_predictions_agent_run  ON predictions (agent_run_id);

-- =============================================================================
-- RECOMMENDATIONS
-- =============================================================================

CREATE TABLE recommendations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_id   UUID NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
    action          TEXT NOT NULL,
    category        recommendation_category NOT NULL,
    priority        recommendation_priority NOT NULL,
    priority_score  SMALLINT CHECK (priority_score BETWEEN 1 AND 100),
    reason          TEXT,
    estimated_impact TEXT,                              -- 'HIGH' | 'MEDIUM' | 'LOW'
    is_actioned     BOOLEAN NOT NULL DEFAULT FALSE,
    actioned_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_recs_prediction ON recommendations (prediction_id);
CREATE INDEX idx_recs_priority   ON recommendations (priority, priority_score DESC);

-- =============================================================================
-- DAILY BRIEFINGS (AI Report Agent output)
-- =============================================================================

CREATE TABLE daily_briefings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    city                TEXT NOT NULL,
    briefing_date       DATE NOT NULL,
    highest_risk_area   TEXT,
    highest_risk_score  NUMERIC(5, 2),
    primary_crime_type  TEXT,
    overall_risk_level  risk_level_enum,
    avg_risk_score      NUMERIC(5, 2),
    avg_confidence      NUMERIC(4, 3),
    summary_text        TEXT NOT NULL,                  -- LLM-generated briefing
    top_recommendations JSONB,
    stats               JSONB,                          -- prediction counts, area breakdown
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_briefings_city_date ON daily_briefings (city, briefing_date);

-- =============================================================================
-- WEATHER SNAPSHOTS
-- =============================================================================

CREATE TABLE weather_snapshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    area_id         UUID NOT NULL REFERENCES areas(id),
    recorded_at     TIMESTAMPTZ NOT NULL,
    temperature_c   NUMERIC(5, 2),
    feels_like_c    NUMERIC(5, 2),
    humidity_pct    SMALLINT,
    condition       TEXT,                               -- 'clear','rain','storm','fog','snow'
    wind_kmh        NUMERIC(5, 2),
    visibility_km   NUMERIC(5, 2),
    uv_index        SMALLINT,
    precipitation_mm NUMERIC(6, 2),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_weather_area_time ON weather_snapshots (area_id, recorded_at);
CREATE INDEX idx_weather_time ON weather_snapshots (recorded_at DESC);

-- =============================================================================
-- TRAFFIC SNAPSHOTS
-- =============================================================================

CREATE TABLE traffic_snapshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    area_id         UUID NOT NULL REFERENCES areas(id),
    recorded_at     TIMESTAMPTZ NOT NULL,
    congestion_pct  SMALLINT CHECK (congestion_pct BETWEEN 0 AND 100),
    incident_count  SMALLINT,
    flow_speed_kmh  NUMERIC(5, 2),
    free_flow_speed NUMERIC(5, 2),
    road_closures   SMALLINT DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_traffic_area_time ON traffic_snapshots (area_id, recorded_at);
CREATE INDEX idx_traffic_time ON traffic_snapshots (recorded_at DESC);

-- =============================================================================
-- PUBLIC EVENTS
-- =============================================================================

CREATE TABLE public_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    area_id         UUID REFERENCES areas(id),
    city            TEXT NOT NULL,
    name            TEXT NOT NULL,
    category        TEXT,                               -- 'concert','sports','festival','protest','parade'
    venue           TEXT,
    expected_crowd  INTEGER,
    crowd_bucket    TEXT,                               -- 'small'|'medium'|'large'|'massive'
    location        GEOMETRY(POINT, 4326),
    starts_at       TIMESTAMPTZ NOT NULL,
    ends_at         TIMESTAMPTZ NOT NULL,
    source          TEXT,
    source_id       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_events_area_time ON public_events (area_id, starts_at);
CREATE INDEX idx_events_city_time ON public_events (city, starts_at);
CREATE UNIQUE INDEX idx_events_source_dedup ON public_events (source, source_id)
    WHERE source_id IS NOT NULL;

-- =============================================================================
-- SIMULATED IOT SNAPSHOTS
-- =============================================================================

CREATE TABLE iot_snapshots (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    area_id             UUID NOT NULL REFERENCES areas(id),
    recorded_at         TIMESTAMPTZ NOT NULL,
    streetlight_pct     SMALLINT CHECK (streetlight_pct BETWEEN 0 AND 100),
    cctv_alert_count    SMALLINT DEFAULT 0,
    cctv_operational    SMALLINT,                       -- number of working cameras
    crowd_density       NUMERIC(6, 2),                  -- people per 100m²
    anomaly_detected    BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_iot_area_time ON iot_snapshots (area_id, recorded_at);
CREATE INDEX idx_iot_time ON iot_snapshots (recorded_at DESC);

-- =============================================================================
-- MODEL MONITORING
-- =============================================================================

CREATE TABLE model_monitoring (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_version_id    UUID NOT NULL REFERENCES model_registry(id),
    monitored_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accuracy_current    NUMERIC(6, 4),
    accuracy_baseline   NUMERIC(6, 4),
    accuracy_decay      NUMERIC(6, 4),                  -- current - baseline
    psi_score           NUMERIC(6, 4),                  -- Population Stability Index (overall)
    feature_drift       JSONB,                          -- per-feature PSI scores
    data_freshness_hrs  NUMERIC(6, 2),                  -- hours since last successful ingest
    retraining_recommended BOOLEAN NOT NULL DEFAULT FALSE,
    alert_sent          BOOLEAN NOT NULL DEFAULT FALSE,
    report_json         JSONB
);

CREATE INDEX idx_monitoring_model ON model_monitoring (model_version_id, monitored_at DESC);
CREATE INDEX idx_monitoring_alert ON model_monitoring (retraining_recommended) WHERE retraining_recommended = TRUE;

-- =============================================================================
-- DATA QUALITY REPORTS
-- =============================================================================

CREATE TABLE data_quality_reports (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source              TEXT NOT NULL,                  -- which data source was checked
    city                TEXT,
    total_records       INTEGER,
    duplicates_removed  INTEGER DEFAULT 0,
    nulls_filled        INTEGER DEFAULT 0,
    invalid_coords      INTEGER DEFAULT 0,
    corrupted_records   INTEGER DEFAULT 0,
    outliers_detected   INTEGER DEFAULT 0,
    api_failures        INTEGER DEFAULT 0,
    scraper_failures    INTEGER DEFAULT 0,
    data_freshness_hrs  NUMERIC(6, 2),
    quality_score       NUMERIC(5, 2) CHECK (quality_score BETWEEN 0 AND 100),
    report_json         JSONB,
    triggered_by        TEXT DEFAULT 'scheduler'        -- 'scheduler' | 'manual' | 'agent'
);

CREATE INDEX idx_dq_source_time ON data_quality_reports (source, run_at DESC);

-- =============================================================================
-- AGENT EXECUTION LOG (Observability)
-- =============================================================================

CREATE TABLE agent_execution_log (
    id              BIGSERIAL PRIMARY KEY,
    run_id          UUID NOT NULL,                      -- LangGraph run identifier
    agent_name      TEXT NOT NULL,
    status          TEXT NOT NULL,                      -- 'started'|'completed'|'failed'|'skipped'
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    duration_ms     INTEGER,
    area_id         UUID REFERENCES areas(id),
    input_summary   JSONB,
    output_summary  JSONB,
    error_message   TEXT,
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX idx_agent_log_run     ON agent_execution_log (run_id);
CREATE INDEX idx_agent_log_name    ON agent_execution_log (agent_name, started_at DESC);
CREATE INDEX idx_agent_log_failed  ON agent_execution_log (status) WHERE status = 'failed';

-- =============================================================================
-- AUDIT LOG (Security)
-- =============================================================================

CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    action      TEXT NOT NULL,
    entity      TEXT,
    entity_id   UUID,
    user_ip     INET,
    user_agent  TEXT,
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_action ON audit_log (action, created_at DESC);
CREATE INDEX idx_audit_entity ON audit_log (entity, entity_id);

-- =============================================================================
-- UTILITY: auto-update updated_at timestamps
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_areas_updated_at
    BEFORE UPDATE ON areas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- SEED: Default city areas for Chicago (development dataset)
-- Areas match Chicago community area boundaries (77 official areas).
-- These are representative centroids; full polygon data loaded by ETL adapter.
-- =============================================================================

INSERT INTO areas (name, city, country_code, centroid, district_code, metadata) VALUES
    ('Loop',            'Chicago', 'US', ST_SetSRID(ST_MakePoint(-87.6298, 41.8827), 4326), '32', '{"community_area": 32}'),
    ('Near North Side', 'Chicago', 'US', ST_SetSRID(ST_MakePoint(-87.6340, 41.9000), 4326), '08', '{"community_area": 8}'),
    ('West Town',       'Chicago', 'US', ST_SetSRID(ST_MakePoint(-87.6689, 41.8988), 4326), '24', '{"community_area": 24}'),
    ('Austin',          'Chicago', 'US', ST_SetSRID(ST_MakePoint(-87.7678, 41.8953), 4326), '25', '{"community_area": 25}'),
    ('Humboldt Park',   'Chicago', 'US', ST_SetSRID(ST_MakePoint(-87.7228, 41.9000), 4326), '23', '{"community_area": 23}'),
    ('Englewood',       'Chicago', 'US', ST_SetSRID(ST_MakePoint(-87.6447, 41.7789), 4326), '68', '{"community_area": 68}'),
    ('Lakeview',        'Chicago', 'US', ST_SetSRID(ST_MakePoint(-87.6434, 41.9428), 4326), '06', '{"community_area": 6}'),
    ('Rogers Park',     'Chicago', 'US', ST_SetSRID(ST_MakePoint(-87.6637, 41.9983), 4326), '01', '{"community_area": 1}'),
    ('Garfield Park',   'Chicago', 'US', ST_SetSRID(ST_MakePoint(-87.7196, 41.8805), 4326), '26', '{"community_area": 26}'),
    ('South Shore',     'Chicago', 'US', ST_SetSRID(ST_MakePoint(-87.5830, 41.7614), 4326), '43', '{"community_area": 43}')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- GRANTS (in case app user differs from superuser)
-- =============================================================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO crimepatrol;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO crimepatrol;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO crimepatrol;
