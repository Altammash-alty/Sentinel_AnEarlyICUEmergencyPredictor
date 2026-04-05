"""
SENTINEL — PostgreSQL + TimescaleDB Database Layer

Handles connection pooling, table creation, and all DB queries.
Uses asyncpg for async operations in FastAPI context.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncpg
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("sentinel.database")

# ──────────────────────────────────────────────────────────────────────────────
# Connection pool (set on startup)
# ──────────────────────────────────────────────────────────────────────────────

_pool: Optional[asyncpg.Pool] = None

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sentinel:sentinel123@localhost:5432/sentinel",
)


async def create_pool() -> asyncpg.Pool:
    global _pool
    _pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=2,
        max_size=10,
        command_timeout=60,
    )
    logger.info("Database connection pool created.")
    return _pool


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        await create_pool()
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed.")


# ──────────────────────────────────────────────────────────────────────────────
# DDL — Create tables
# ──────────────────────────────────────────────────────────────────────────────

CREATE_TABLES_SQL = """
-- Try to enable TimescaleDB extension (ignore error if already installed or unavailable)
DO $$ BEGIN
    CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'TimescaleDB extension not available, continuing without it.';
END $$;

CREATE TABLE IF NOT EXISTS patients (
    id               TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    age              INTEGER NOT NULL,
    ward             TEXT NOT NULL,
    baseline_vitals  JSONB NOT NULL,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vital_readings (
    time             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    patient_id       TEXT NOT NULL,
    hr               FLOAT,
    bp               FLOAT,
    spo2             FLOAT,
    rr               FLOAT,
    temp             FLOAT,
    risk_score       FLOAT,
    risk_level       TEXT,
    lstm_confidence  FLOAT,
    news2_score      INTEGER
);

-- Convert to hypertable only if TimescaleDB is available AND table is not already one
DO $$ BEGIN
    PERFORM create_hypertable('vital_readings', 'time', if_not_exists => TRUE);
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Could not create hypertable (TimescaleDB may not be available). Using plain table.';
END $$;

CREATE INDEX IF NOT EXISTS idx_vital_patient_time
    ON vital_readings (patient_id, time DESC);

CREATE TABLE IF NOT EXISTS alerts (
    id              SERIAL PRIMARY KEY,
    patient_id      TEXT NOT NULL,
    patient_name    TEXT NOT NULL,
    ward            TEXT NOT NULL,
    triggered_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    severity        TEXT NOT NULL,
    vitals          JSONB NOT NULL,
    risk_score      FLOAT NOT NULL,
    acknowledged    BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_alerts_patient
    ON alerts (patient_id, triggered_at DESC);

CREATE TABLE IF NOT EXISTS timeline_events (
    id              SERIAL PRIMARY KEY,
    patient_id      TEXT NOT NULL,
    event_time      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type      TEXT NOT NULL,
    detail          TEXT NOT NULL,
    risk_level      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_timeline_patient
    ON timeline_events (patient_id, event_time DESC);

CREATE TABLE IF NOT EXISTS telemetry_log (
    time                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_hex             TEXT,
    decoded_patient_id  TEXT,
    resolved_patient_id TEXT,
    was_corrected       BOOLEAN,
    confidence_score    FLOAT
);

CREATE INDEX IF NOT EXISTS idx_telemetry_time
    ON telemetry_log (time DESC);
"""


async def create_tables():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(CREATE_TABLES_SQL)
    logger.info("Database tables verified / created.")


# ──────────────────────────────────────────────────────────────────────────────
# Patient operations
# ──────────────────────────────────────────────────────────────────────────────

async def upsert_patient(patient: Dict[str, Any]):
    pool = await get_pool()
    baseline = {
        "hr": patient["hr"], "bp": patient["bp"],
        "spo2": patient["spo2"], "rr": patient["rr"],
        "temp": patient["temp"],
    }
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO patients (id, name, age, ward, baseline_vitals)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO UPDATE
              SET name = EXCLUDED.name,
                  age  = EXCLUDED.age,
                  ward = EXCLUDED.ward,
                  baseline_vitals = EXCLUDED.baseline_vitals
            """,
            patient["id"], patient["name"], patient["age"],
            patient["ward"], json.dumps(baseline),
        )


async def get_all_patients() -> List[Dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM patients ORDER BY id")
    return [dict(r) for r in rows]


async def get_patient_by_id(patient_id: str) -> Optional[Dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM patients WHERE id = $1", patient_id
        )
    return dict(row) if row else None


# ──────────────────────────────────────────────────────────────────────────────
# Vital readings operations
# ──────────────────────────────────────────────────────────────────────────────

async def insert_vital_reading(v: Dict[str, Any]):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO vital_readings
              (time, patient_id, hr, bp, spo2, rr, temp,
               risk_score, risk_level, lstm_confidence, news2_score)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            """,
            v["timestamp"], v["patient_id"],
            v["hr"], v["bp"], v["spo2"], v["rr"], v["temp"],
            v["risk_score"], v["risk_level"],
            v["lstm_confidence"], v["news2_score"],
        )


async def get_patient_vitals_history(
    patient_id: str,
    limit: int = 60,
    offset: int = 0,
) -> List[Dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM vital_readings
            WHERE patient_id = $1
            ORDER BY time DESC
            LIMIT $2 OFFSET $3
            """,
            patient_id, limit, offset,
        )
    return [dict(r) for r in rows]


async def get_patient_vitals_last_hour(patient_id: str) -> List[Dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM vital_readings
            WHERE patient_id = $1
              AND time >= NOW() - INTERVAL '1 hour'
            ORDER BY time ASC
            """,
            patient_id,
        )
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────────────────────────────────────
# Alert operations
# ──────────────────────────────────────────────────────────────────────────────

async def insert_alert(a: Dict[str, Any]) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO alerts
              (patient_id, patient_name, ward, triggered_at,
               severity, vitals, risk_score, acknowledged)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
            RETURNING id
            """,
            a["patient_id"], a["patient_name"], a["ward"],
            a["triggered_at"], a["severity"],
            json.dumps(a["vitals"]), a["risk_score"], False,
        )
    return row["id"]


async def get_alerts(
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = 100,
) -> List[Dict]:
    pool = await get_pool()
    conditions = []
    params: list = []
    idx = 1

    if severity:
        conditions.append(f"severity = ${idx}")
        params.append(severity)
        idx += 1
    if acknowledged is not None:
        conditions.append(f"acknowledged = ${idx}")
        params.append(acknowledged)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(limit)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM alerts {where} ORDER BY triggered_at DESC LIMIT ${idx}",
            *params,
        )
    return [dict(r) for r in rows]


async def acknowledge_alert(alert_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE alerts SET acknowledged = TRUE WHERE id = $1",
            alert_id,
        )
    return result == "UPDATE 1"


async def count_unacked_alerts() -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) AS cnt FROM alerts WHERE acknowledged = FALSE"
        )
    return row["cnt"] if row else 0


# ──────────────────────────────────────────────────────────────────────────────
# Timeline operations
# ──────────────────────────────────────────────────────────────────────────────

async def insert_timeline_event(e: Dict[str, Any]) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO timeline_events
              (patient_id, event_time, event_type, detail, risk_level)
            VALUES ($1,$2,$3,$4,$5)
            RETURNING id
            """,
            e["patient_id"], e["timestamp"],
            e["event_type"], e["detail"], e["risk_level"],
        )
    return row["id"]


async def get_timeline(patient_id: Optional[str] = None, limit: int = 200) -> List[Dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        if patient_id:
            rows = await conn.fetch(
                """
                SELECT * FROM timeline_events
                WHERE patient_id = $1
                ORDER BY event_time ASC
                LIMIT $2
                """,
                patient_id, limit,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT * FROM timeline_events
                ORDER BY event_time ASC
                LIMIT $1
                """,
                limit,
            )
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────────────────────────────────────
# Telemetry log operations
# ──────────────────────────────────────────────────────────────────────────────

async def insert_telemetry(t: Dict[str, Any]):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO telemetry_log
              (time, raw_hex, decoded_patient_id,
               resolved_patient_id, was_corrected, confidence_score)
            VALUES ($1,$2,$3,$4,$5,$6)
            """,
            t["timestamp"], t["raw_hex"],
            t["decoded_patient_id"], t["resolved_patient_id"],
            t["was_corrected"], t["confidence_score"],
        )


async def get_recent_telemetry(limit: int = 100) -> List[Dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM telemetry_log
            ORDER BY time DESC
            LIMIT $1
            """,
            limit,
        )
    return [dict(r) for r in rows]


async def get_telemetry_stats() -> Dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
              COUNT(*)                          AS total_packets,
              SUM(CASE WHEN was_corrected THEN 1 ELSE 0 END) AS total_collisions
            FROM telemetry_log
            WHERE time >= NOW() - INTERVAL '5 minutes'
            """
        )
    total    = row["total_packets"] or 0
    collisions = row["total_collisions"] or 0
    return {
        "total_packets":    total,
        "total_collisions": collisions,
        "collision_rate":   (collisions / total) if total > 0 else 0.0,
    }
