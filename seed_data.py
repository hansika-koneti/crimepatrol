"""
CrimePatrol — Seed Script
Populates the database with realistic Chicago-based data.
Run inside the backend container:
    docker exec -it crimepatrol_backend python seed_data.py
"""

import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# ── Config ─────────────────────────────────────────────────────────────────
DATABASE_URL = "postgresql+asyncpg://crimepatrol:crimepatrol_secret@postgres:5432/crimepatrol"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ── Constants ───────────────────────────────────────────────────────────────
CITY = "Chicago"
NOW = datetime.now(timezone.utc)

CHICAGO_AREAS = [
    {"name": "Loop",           "district": "D01", "pop": 42298,  "km2": 5.7,  "lat": 41.8827, "lon": -87.6233},
    {"name": "Lincoln Park",   "district": "D18", "pop": 67694,  "km2": 9.5,  "lat": 41.9230, "lon": -87.6472},
    {"name": "Wicker Park",    "district": "D14", "pop": 28991,  "km2": 3.2,  "lat": 41.9085, "lon": -87.6789},
    {"name": "Hyde Park",      "district": "D21", "pop": 30156,  "km2": 5.9,  "lat": 41.7943, "lon": -87.5907},
    {"name": "Englewood",      "district": "D07", "pop": 24369,  "km2": 6.3,  "lat": 41.7788, "lon": -87.6448},
    {"name": "Rogers Park",    "district": "D24", "pop": 54991,  "km2": 4.0,  "lat": 42.0096, "lon": -87.6694},
    {"name": "Austin",         "district": "D15", "pop": 97256,  "km2": 11.7, "lat": 41.8949, "lon": -87.7712},
    {"name": "River North",    "district": "D18", "pop": 19418,  "km2": 2.4,  "lat": 41.8919, "lon": -87.6341},
    {"name": "Pilsen",         "district": "D12", "pop": 40814,  "km2": 4.8,  "lat": 41.8563, "lon": -87.6582},
    {"name": "Lakeview",       "district": "D19", "pop": 98514,  "km2": 9.2,  "lat": 41.9427, "lon": -87.6571},
]

# (crime_type, crime_category, severity 1-5)
CRIME_TYPES = [
    ("THEFT",               "PROPERTY", 2),
    ("BATTERY",             "VIOLENT",  4),
    ("ASSAULT",             "VIOLENT",  4),
    ("BURGLARY",            "PROPERTY", 3),
    ("MOTOR VEHICLE THEFT", "PROPERTY", 3),
    ("ROBBERY",             "VIOLENT",  5),
    ("NARCOTICS",           "DRUG",     3),
    ("CRIMINAL DAMAGE",     "PROPERTY", 2),
    ("DECEPTIVE PRACTICE",  "FINANCIAL",2),
    ("OTHER OFFENSE",       "OTHER",    1),
    ("WEAPONS VIOLATION",   "VIOLENT",  5),
    ("PUBLIC PEACE",        "ORDER",    2),
]

ADDRESSES = [
    "100 N STATE ST", "200 W MADISON ST", "3500 N CLARK ST",
    "6300 S COTTAGE GROVE AVE", "1800 W 63RD ST", "7200 N SHERIDAN RD",
    "5800 W CHICAGO AVE", "400 N WELLS ST", "2200 S HALSTED ST",
    "3300 N BROADWAY", "1200 N LAKE SHORE DR", "4500 W ARMITAGE AVE",
    "800 E 79TH ST", "2700 W DEVON AVE", "1000 W NORTH AVE",
]

WEATHER_CONDITIONS = ["Clear", "Cloudy", "Rainy", "Partly Cloudy", "Foggy", "Snowy"]


def random_point_near(lat, lon, radius_deg=0.02):
    return (
        lat + random.uniform(-radius_deg, radius_deg),
        lon + random.uniform(-radius_deg, radius_deg),
    )


def risk_for_area(area_name: str) -> tuple[float, str]:
    """Returns (risk_score 0-100, risk_level enum)."""
    high_crime = {"Englewood", "Austin"}
    med_crime  = {"Rogers Park", "Pilsen", "Hyde Park"}
    if area_name in high_crime:
        score = random.uniform(65, 95)
        level = "CRITICAL" if score > 80 else "HIGH"
    elif area_name in med_crime:
        score = random.uniform(40, 70)
        level = "HIGH" if score > 60 else "MEDIUM"
    else:
        score = random.uniform(15, 50)
        level = "MEDIUM" if score > 35 else "LOW"
    return round(score, 2), level


async def seed():
    async with AsyncSessionLocal() as session:
        print("🌱  Seeding CrimePatrol database …")

        # ── 1. Areas ──────────────────────────────────────────────────────
        print("   Creating areas …")
        for a in CHICAGO_AREAS:
            area_id = uuid.uuid4()
            lat, lon = a["lat"], a["lon"]
            await session.execute(text("""
                INSERT INTO areas (id, name, city, country_code, centroid, population, area_km2, district_code, metadata)
                VALUES (
                    :id, :name, :city, 'US',
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                    :pop, :km2, :district,
                    CAST(:meta AS jsonb)
                )
                ON CONFLICT (name, city) DO NOTHING
            """), {
                "id": area_id, "name": a["name"], "city": CITY,
                "lon": lon, "lat": lat,
                "pop": a["pop"], "km2": a["km2"], "district": a["district"],
                "meta": '{"source": "seed"}'
            })

        await session.commit()

        # Re-fetch actual UUIDs (handles ON CONFLICT DO NOTHING)
        # Only keep the areas we seeded (filter out pre-existing unrelated areas)
        our_area_names = {a["name"] for a in CHICAGO_AREAS}
        rows = await session.execute(text("SELECT id, name FROM areas WHERE city = :city"), {"city": CITY})
        area_ids: dict[str, uuid.UUID] = {row.name: row.id for row in rows if row.name in our_area_names}
        print(f"   ✓ {len(area_ids)} areas ready")

        # ── 2. Crime Incidents ─────────────────────────────────────────────
        print("   Inserting crime incidents …")
        incident_count = 0
        for area_name, area_id in area_ids.items():
            a_info = next(x for x in CHICAGO_AREAS if x["name"] == area_name)
            n = 80 if area_name in ("Englewood", "Austin") else \
                50 if area_name in ("Rogers Park", "Pilsen", "Hyde Park") else 30

            for _ in range(n):
                crime_type, crime_cat, base_sev = random.choice(CRIME_TYPES)
                # severity is 1-5 (CHECK constraint)
                severity = max(1, min(5, base_sev + random.randint(-1, 1)))
                days_ago = random.randint(0, 30)
                hours_ago = random.randint(0, 23)
                occurred = NOW - timedelta(days=days_ago, hours=hours_ago)
                reported = occurred + timedelta(hours=random.randint(0, 6))
                plat, plon = random_point_near(a_info["lat"], a_info["lon"])

                await session.execute(text("""
                    INSERT INTO crime_incidents (
                        id, area_id, crime_type, crime_category, severity,
                        location, address, occurred_at, reported_at,
                        source, source_id, is_verified, city, metadata
                    ) VALUES (
                        :id, :area_id, :crime_type, :crime_cat, :severity,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                        :address, :occurred_at, :reported_at,
                        CAST('manual' AS data_source_enum), :source_id, true, :city,
                        CAST(:meta AS jsonb)
                    )
                """), {
                    "id": uuid.uuid4(), "area_id": area_id,
                    "crime_type": crime_type, "crime_cat": crime_cat, "severity": severity,
                    "lon": plon, "lat": plat,
                    "address": random.choice(ADDRESSES),
                    "occurred_at": occurred, "reported_at": reported,
                    "source_id": f"SEED-{uuid.uuid4().hex[:8].upper()}",
                    "city": CITY,
                    "meta": '{"seeded": true}'
                })
                incident_count += 1

        await session.commit()
        print(f"   ✓ {incident_count} crime incidents inserted")

        # ── 3. Model Registry ─────────────────────────────────────────────
        print("   Creating model registry entry …")
        model_id = uuid.uuid4()
        await session.execute(text("""
            INSERT INTO model_registry (
                id, version, algorithm, status,
                accuracy, precision_score, recall_score, f1_score, roc_auc,
                feature_version, training_rows, city, trained_at, notes
            ) VALUES (
                :id, 'v1.0.0-seed', 'XGBoost', 'active',
                0.847, 0.812, 0.798, 0.805, 0.921,
                'v1', :rows, :city, :trained_at,
                'Seeded demo model for Chicago crime prediction'
            )
            ON CONFLICT (version) DO NOTHING
        """), {
            "id": model_id, "rows": incident_count,
            "city": CITY, "trained_at": NOW - timedelta(days=2)
        })
        await session.commit()

        # Re-fetch model id
        row = await session.execute(text("SELECT id FROM model_registry WHERE version = 'v1.0.0-seed'"))
        model_id = row.scalar()
        print(f"   ✓ Model registry entry ready (id={model_id})")

        # ── 4. Predictions ────────────────────────────────────────────────
        print("   Generating predictions …")
        pred_count = 0
        for area_name, area_id in area_ids.items():
            for day in range(7, -1, -1):
                for window_h in [0, 6, 12, 18]:
                    pred_time = (NOW - timedelta(days=day)).replace(
                        hour=window_h, minute=0, second=0, microsecond=0
                    )
                    risk_score, risk_level = risk_for_area(area_name)
                    # Slightly vary score per window
                    risk_score = max(1.0, min(99.0, risk_score + random.uniform(-5, 5)))
                    if risk_score > 80:
                        risk_level = "CRITICAL"
                    elif risk_score > 60:
                        risk_level = "HIGH"
                    elif risk_score > 35:
                        risk_level = "MEDIUM"
                    else:
                        risk_level = "LOW"

                    crime_type, _, _ = random.choice(CRIME_TYPES)
                    confidence = round(random.uniform(0.70, 0.99), 3)

                    shap = {
                        "hour_of_day": round(random.uniform(0.05, 0.25), 3),
                        "day_of_week": round(random.uniform(0.02, 0.15), 3),
                        "historical_crime_rate": round(random.uniform(0.10, 0.40), 3),
                        "weather_condition": round(random.uniform(0.01, 0.08), 3),
                        "population_density": round(random.uniform(0.03, 0.12), 3),
                    }
                    top_feats = ["historical_crime_rate", "hour_of_day", "day_of_week"]

                    await session.execute(text("""
                        INSERT INTO predictions (
                            id, area_id, model_version_id, predicted_for,
                            window_hours, risk_score, risk_level, crime_type,
                            confidence, shap_values, top_features, explanation_text
                        ) VALUES (
                            :id, :area_id, :model_id, :predicted_for,
                            6, :risk_score, CAST(:risk_level AS risk_level_enum), :crime_type,
                            :confidence, CAST(:shap AS jsonb),
                            CAST(:top_features AS jsonb), :explanation
                        )
                    """), {
                        "id": uuid.uuid4(), "area_id": area_id, "model_id": model_id,
                        "predicted_for": pred_time,
                        "risk_score": round(risk_score, 2),
                        "risk_level": risk_level,
                        "crime_type": crime_type,
                        "confidence": confidence,
                        "shap": json.dumps(shap),
                        "top_features": json.dumps(top_feats),
                        "explanation": (
                            f"{area_name} shows {risk_level.lower()} risk for "
                            f"{crime_type.lower()} during this 6-hour window. "
                            f"Historical crime rate is the primary driver."
                        )
                    })
                    pred_count += 1

        await session.commit()
        print(f"   ✓ {pred_count} predictions inserted")

        # ── 5. Weather Snapshots ──────────────────────────────────────────
        print("   Creating weather snapshots …")
        weather_count = 0
        for area_name, area_id in area_ids.items():
            for day in range(7):
                for hour in [0, 6, 12, 18]:
                    ts = (NOW - timedelta(days=day)).replace(
                        hour=hour, minute=0, second=0, microsecond=0
                    )
                    temp = round(random.uniform(5, 28), 1)
                    await session.execute(text("""
                        INSERT INTO weather_snapshots (
                            id, area_id, recorded_at, temperature_c, feels_like_c,
                            humidity_pct, condition, wind_kmh, visibility_km,
                            uv_index, precipitation_mm
                        ) VALUES (
                            :id, :area_id, :ts, :temp, :feels,
                            :humidity, :condition, :wind, :vis, :uv, :precip
                        )
                        ON CONFLICT (area_id, recorded_at) DO NOTHING
                    """), {
                        "id": uuid.uuid4(), "area_id": area_id, "ts": ts,
                        "temp": temp,
                        "feels": round(temp - random.uniform(1, 4), 1),
                        "humidity": random.randint(40, 90),
                        "condition": random.choice(WEATHER_CONDITIONS),
                        "wind": round(random.uniform(5, 35), 1),
                        "vis": round(random.uniform(5, 15), 1),
                        "uv": random.randint(0, 8),
                        "precip": round(random.uniform(0, 5), 2),
                    })
                    weather_count += 1

        await session.commit()
        print(f"   ✓ {weather_count} weather snapshots inserted")

        # ── 6. Traffic Snapshots ──────────────────────────────────────────
        print("   Creating traffic snapshots …")
        traffic_count = 0
        for area_name, area_id in area_ids.items():
            for day in range(7):
                for hour in [0, 6, 9, 12, 15, 18, 21]:
                    ts = (NOW - timedelta(days=day)).replace(
                        hour=hour, minute=0, second=0, microsecond=0
                    )
                    base_cong = 70 if hour in (9, 15, 18) else 30
                    await session.execute(text("""
                        INSERT INTO traffic_snapshots (
                            id, area_id, recorded_at, congestion_pct,
                            incident_count, flow_speed_kmh, free_flow_speed, road_closures
                        ) VALUES (
                            :id, :area_id, :ts, :cong,
                            :inc, :flow, :free_flow, :closures
                        )
                        ON CONFLICT (area_id, recorded_at) DO NOTHING
                    """), {
                        "id": uuid.uuid4(), "area_id": area_id, "ts": ts,
                        "cong": min(100, base_cong + random.randint(-15, 15)),
                        "inc": random.randint(0, 5),
                        "flow": round(random.uniform(15, 55), 1),
                        "free_flow": round(random.uniform(50, 65), 1),
                        "closures": random.randint(0, 2),
                    })
                    traffic_count += 1

        await session.commit()
        print(f"   ✓ {traffic_count} traffic snapshots inserted")

        # ── 7. IoT Snapshots ──────────────────────────────────────────────
        print("   Creating IoT snapshots …")
        iot_count = 0
        for area_name, area_id in area_ids.items():
            for day in range(7):
                for hour in [0, 6, 12, 18]:
                    ts = (NOW - timedelta(days=day)).replace(
                        hour=hour, minute=0, second=0, microsecond=0
                    )
                    base_light = 60 if area_name in ("Englewood", "Austin") else 85
                    anomaly = random.random() < (0.25 if area_name in ("Englewood", "Austin") else 0.05)
                    await session.execute(text("""
                        INSERT INTO iot_snapshots (
                            id, area_id, recorded_at, streetlight_pct,
                            cctv_alert_count, cctv_operational, crowd_density, anomaly_detected
                        ) VALUES (
                            :id, :area_id, :ts, :light,
                            :alerts, :cctv_op, :crowd, :anomaly
                        )
                        ON CONFLICT (area_id, recorded_at) DO NOTHING
                    """), {
                        "id": uuid.uuid4(), "area_id": area_id, "ts": ts,
                        "light": min(100, base_light + random.randint(-10, 10)),
                        "alerts": random.randint(0, 8) if anomaly else random.randint(0, 2),
                        "cctv_op": random.randint(5, 20),
                        "crowd": round(random.uniform(0.1, 0.9), 2),
                        "anomaly": anomaly,
                    })
                    iot_count += 1

        await session.commit()
        print(f"   ✓ {iot_count} IoT snapshots inserted")

        # ── 8. Daily Briefing ─────────────────────────────────────────────
        print("   Creating daily briefing …")
        await session.execute(text("""
            INSERT INTO daily_briefings (
                id, city, briefing_date, highest_risk_area, highest_risk_score,
                primary_crime_type, overall_risk_level, avg_risk_score,
                avg_confidence, summary_text, top_recommendations, stats
            ) VALUES (
                :id, :city, :date, 'Englewood', 87.3,
                'BATTERY', 'HIGH', 52.4, 0.84,
                :summary,
                CAST(:recs AS jsonb), CAST(:stats AS jsonb)
            )
        """), {
            "id": uuid.uuid4(), "city": CITY,
            "date": NOW.replace(hour=7, minute=0, second=0, microsecond=0),
            "summary": (
                "Chicago daily safety briefing: Englewood and Austin remain the highest-risk areas "
                "with elevated BATTERY and ASSAULT incidents. Loop and River North show LOW risk. "
                "Weather is partly cloudy with moderate winds — conditions may slightly elevate "
                "outdoor incidents in the evening. 3 active patrol advisories issued."
            ),
            "recs": json.dumps([
                {"action": "Increase foot patrols in Englewood between 20:00-02:00", "priority": "HIGH"},
                {"action": "Deploy mobile unit to Austin W Chicago Ave corridor", "priority": "HIGH"},
                {"action": "Monitor Rogers Park for escalating narcotics activity", "priority": "MEDIUM"},
            ]),
            "stats": json.dumps({
                "total_incidents_24h": 47, "critical_areas": 2, "high_areas": 3,
                "arrests_made": 12, "ongoing_investigations": 8
            })
        })
        await session.commit()
        print("   ✓ Daily briefing created")

        print("\n✅  Seed complete!")
        print(f"   Areas:            {len(area_ids)}")
        print(f"   Crime incidents:  {incident_count}")
        print(f"   Predictions:      {pred_count}")
        print(f"   Weather snaps:    {weather_count}")
        print(f"   Traffic snaps:    {traffic_count}")
        print(f"   IoT snaps:        {iot_count}")
        print(f"\n   🔗 Dashboard:  http://localhost:5173")
        print(f"   🔑 Login:       admin@crimepatrol.local / changeme123")


if __name__ == "__main__":
    asyncio.run(seed())
