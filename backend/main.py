"""
SENTINEL — FastAPI Application Entry Point

Wires together:
  simulator → identity_resolver → risk_engine → alert_engine
  → database writes → WebSocket broadcast → REST endpoints
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

# Fix import path so backend sub-modules resolve correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend import database as db
from backend.simulator import ICUSimulator, PATIENTS, PATIENT_IDS
from backend.identity_resolver import IdentityResolver
from backend.risk_engine import RiskEngine
from backend.alert_engine import AlertEngine
from backend.routes.patients import router as patients_router
from backend.routes.alerts   import router as alerts_router
from backend.routes.timeline import router as timeline_router

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sentinel.main")

# ──────────────────────────────────────────────────────────────────────────────
# Shared application state
# ──────────────────────────────────────────────────────────────────────────────

class AppState:
    def __init__(self):
        self.simulator:        Optional[ICUSimulator]    = None
        self.resolver:         Optional[IdentityResolver] = None
        self.risk_engine:      Optional[RiskEngine]       = None
        self.alert_engine:     Optional[AlertEngine]       = None
        self.packet_queue:     asyncio.Queue              = asyncio.Queue(maxsize=500)
        self.start_time:       float                       = 0.0

        # Latest vitals keyed by patient_id
        self.latest_vitals:    Dict[str, Dict]            = {}
        # Last 60 readings per patient for chart history
        self.vitals_history:   Dict[str, List[Dict]]      = {pid: [] for pid in PATIENT_IDS}
        # Recent alerts (in-memory, max 200)
        self.recent_alerts:    List[Dict]                 = []
        # Timeline events (in-memory cache)
        self.timeline_events:  List[Dict]                 = []
        # Recent telemetry packets (in-memory, max 200)
        self.telemetry_feed:   List[Dict]                 = []

        # Patient info map
        self.patient_map:      Dict[str, Dict]            = {p["id"]: p for p in PATIENTS}

        # Previous risk levels for transition detection
        self.prev_risk_levels: Dict[str, str]             = {}

        # Pipeline metrics
        self.packets_processed: int  = 0
        self.collisions_total:  int  = 0

        # Processing background task handle
        self._pipeline_task: Optional[asyncio.Task] = None

state = AppState()

# ──────────────────────────────────────────────────────────────────────────────
# WebSocket connection managers
# ──────────────────────────────────────────────────────────────────────────────

class WSManager:
    """Manages a pool of WebSocket connections for one endpoint."""

    def __init__(self, name: str):
        self.name  = name
        self._sockets: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._sockets.add(ws)
        logger.debug(f"WS [{self.name}] connected (total={len(self._sockets)})")

    def disconnect(self, ws: WebSocket):
        self._sockets.discard(ws)
        logger.debug(f"WS [{self.name}] disconnected (total={len(self._sockets)})")

    async def broadcast(self, data: Any):
        if not self._sockets:
            return
        message = data if isinstance(data, str) else json.dumps(data, default=str)
        dead = set()
        for ws in list(self._sockets):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._sockets.discard(ws)

    @property
    def count(self) -> int:
        return len(self._sockets)


ws_vitals    = WSManager("vitals")
ws_alerts    = WSManager("alerts")
ws_timeline  = WSManager("timeline")
ws_telemetry = WSManager("telemetry")


# ──────────────────────────────────────────────────────────────────────────────
# Timeline helper
# ──────────────────────────────────────────────────────────────────────────────

async def emit_timeline_event(
    patient_id: str,
    event_type: str,
    detail: str,
    risk_level: str,
):
    evt = {
        "patient_id": patient_id,
        "timestamp":  datetime.now(timezone.utc),
        "event_type": event_type,
        "detail":     detail,
        "risk_level": risk_level,
    }
    try:
        evt_id = await db.insert_timeline_event(evt)
        evt["id"] = evt_id
    except Exception as exc:
        logger.warning(f"Timeline DB insert failed: {exc}")
        evt["id"] = None

    event_json = {**evt, "timestamp": evt["timestamp"].isoformat()}
    state.timeline_events.append(event_json)
    if len(state.timeline_events) > 500:
        state.timeline_events = state.timeline_events[-500:]

    await ws_timeline.broadcast({"type": "timeline", "payload": event_json})


# ──────────────────────────────────────────────────────────────────────────────
# Alert broadcast callback
# ──────────────────────────────────────────────────────────────────────────────

async def on_alert_fired(alert: Dict[str, Any]):
    """Called by AlertEngine when a new alert fires."""
    alert_json = {**alert}
    if isinstance(alert_json.get("triggered_at"), datetime):
        alert_json["triggered_at"] = alert_json["triggered_at"].isoformat()

    state.recent_alerts.append(alert_json)
    if len(state.recent_alerts) > 200:
        state.recent_alerts = state.recent_alerts[-200:]

    await ws_alerts.broadcast({"type": "alert", "payload": alert_json})

    # Also emit a timeline event for the alert
    await emit_timeline_event(
        patient_id  = alert["patient_id"],
        event_type  = "ALERT_FIRED",
        detail      = (
            f"{alert['severity']} alert — "
            f"risk score {alert['risk_score']:.1f}"
        ),
        risk_level  = alert.get("vitals", {}).get("risk_level", "WARNING"),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Processing pipeline
# ──────────────────────────────────────────────────────────────────────────────

async def processing_pipeline():
    """
    Consumes packets from the simulator queue:
      raw packet → identity resolver → risk engine → alert engine
      → DB write → WS broadcast
    """
    logger.info("Processing pipeline started.")

    while True:
        try:
            packet = await asyncio.wait_for(state.packet_queue.get(), timeout=5.0)
        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            break

        try:
            true_id    = packet["true_patient_id"]
            claimed_id = packet["claimed_patient_id"]
            raw_hex    = packet["raw_hex"]
            vitals     = packet["vitals"]
            ts         = datetime.fromisoformat(packet["timestamp"])

            # ── 1. Identity Resolution ──────────────────────────────────────
            resolved_id, was_corrected, confidence = state.resolver.resolve(
                claimed_patient_id = claimed_id,
                true_patient_id    = true_id,
                vitals             = vitals,
            )

            if was_corrected:
                state.collisions_total += 1

            # ── 2. Telemetry logging ────────────────────────────────────────
            tel = {
                "timestamp":            ts,
                "raw_hex":              raw_hex[:80],  # truncate for storage
                "decoded_patient_id":   claimed_id,
                "resolved_patient_id":  resolved_id,
                "was_corrected":        was_corrected,
                "confidence_score":     confidence,
            }
            try:
                await db.insert_telemetry(tel)
            except Exception:
                pass  # non-critical

            tel_json = {**tel, "timestamp": ts.isoformat()}
            state.telemetry_feed.append(tel_json)
            if len(state.telemetry_feed) > 200:
                state.telemetry_feed = state.telemetry_feed[-200:]

            await ws_telemetry.broadcast({"type": "telemetry", "payload": tel_json})

            if was_corrected:
                await emit_timeline_event(
                    patient_id  = resolved_id,
                    event_type  = "IDENTITY_COLLISION",
                    detail      = (
                        f"ID collision resolved: claimed={claimed_id} → "
                        f"actual={resolved_id} (conf={confidence:.2f})"
                    ),
                    risk_level  = "WARNING",
                )

            # ── 3. Risk scoring ─────────────────────────────────────────────
            reading = state.risk_engine.score(resolved_id, vitals, ts)

            # ── 4. Vital history update ─────────────────────────────────────
            reading_json = {
                **reading,
                "timestamp": reading["timestamp"].isoformat()
                    if isinstance(reading["timestamp"], datetime)
                    else reading["timestamp"],
            }
            state.latest_vitals[resolved_id] = reading_json

            history = state.vitals_history.setdefault(resolved_id, [])
            history.append(reading_json)
            if len(history) > 60:
                state.vitals_history[resolved_id] = history[-60:]

            await ws_vitals.broadcast({"type": "vital", "payload": reading_json})

            # ── 5. DB write (vital reading) ─────────────────────────────────
            try:
                await db.insert_vital_reading(reading)
            except Exception as exc:
                logger.debug(f"Vital reading DB insert error: {exc}")

            # ── 6. Risk level transition → timeline event ───────────────────
            prev_level = state.prev_risk_levels.get(resolved_id)
            curr_level = reading["risk_level"]

            if prev_level and prev_level != curr_level:
                await emit_timeline_event(
                    patient_id  = resolved_id,
                    event_type  = "STATUS_CHANGE",
                    detail      = (
                        f"Status changed: {prev_level} → {curr_level} "
                        f"(score={reading['risk_score']:.1f})"
                    ),
                    risk_level  = curr_level,
                )

            state.prev_risk_levels[resolved_id] = curr_level

            # ── 7. Alert evaluation ─────────────────────────────────────────
            patient_info = state.patient_map.get(resolved_id, {
                "name": resolved_id, "ward": "Unknown",
            })
            await state.alert_engine.process(
                reading      = reading,
                patient_info = patient_info,
                db_insert_fn = db.insert_alert,
            )

            state.packets_processed += 1

        except Exception as exc:
            logger.error(f"Pipeline processing error: {exc}", exc_info=True)


# ──────────────────────────────────────────────────────────────────────────────
# Startup / Shutdown (lifespan)
# ──────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise all services before serving requests."""
    state.start_time = time.time()
    logger.info("═" * 60)
    logger.info("SENTINEL ICU Early Warning System — Starting Up")
    logger.info("═" * 60)

    # 1. Database
    try:
        await db.create_pool()
        await db.create_tables()
        logger.info("✓ Database ready")
    except Exception as exc:
        logger.warning(f"Database unavailable: {exc}. Running in DB-less mode.")

    # 2. Seed patients
    for p in PATIENTS:
        try:
            await db.upsert_patient(p)
            # Admission timeline event (only once)
            await db.insert_timeline_event({
                "patient_id": p["id"],
                "timestamp":  datetime.now(timezone.utc),
                "event_type": "ADMISSION",
                "detail":     f"{p['name']} admitted to {p['ward']}",
                "risk_level": "STABLE",
            })
        except Exception:
            pass

    # 3. Risk engine
    state.risk_engine = RiskEngine()
    state.risk_engine.load_model()
    logger.info(f"✓ Risk engine ready (model_loaded={state.risk_engine.model_loaded})")

    # 4. Identity resolver
    state.resolver = IdentityResolver(PATIENT_IDS)
    logger.info("✓ Identity resolver ready")

    # 5. Alert engine
    state.alert_engine = AlertEngine()
    state.alert_engine.set_alert_callback(on_alert_fired)
    logger.info("✓ Alert engine ready")

    # 6. Simulator
    state.simulator = ICUSimulator(state.packet_queue)

    # 7. Start background tasks
    sim_task      = asyncio.create_task(state.simulator.start(),    name="simulator")
    pipeline_task = asyncio.create_task(processing_pipeline(),      name="pipeline")
    state._pipeline_task = pipeline_task

    logger.info("✓ Simulator + pipeline running")
    logger.info("═" * 60)
    logger.info("SENTINEL is LIVE — http://0.0.0.0:8000")
    logger.info("═" * 60)

    yield   # ← application serves requests here

    # Shutdown
    logger.info("SENTINEL shutting down ...")
    state.simulator.stop()
    sim_task.cancel()
    pipeline_task.cancel()
    await db.close_pool()
    logger.info("Goodbye.")


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI app
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "SENTINEL ICU Early Warning System",
    description = "Real-time ICU patient monitoring with LSTM risk prediction",
    version     = "1.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# Include domain routers
app.include_router(patients_router)
app.include_router(alerts_router)
app.include_router(timeline_router)


# ──────────────────────────────────────────────────────────────────────────────
# WebSocket endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws/vitals")
async def ws_vitals_endpoint(ws: WebSocket):
    await ws_vitals.connect(ws)
    # Send current snapshot immediately
    if state.latest_vitals:
        await ws.send_text(json.dumps({
            "type":    "snapshot",
            "payload": {
                "vitals":  list(state.latest_vitals.values()),
                "history": state.vitals_history,
            },
        }, default=str))
    try:
        while True:
            await ws.receive_text()   # keep-alive, ignore ping frames
    except WebSocketDisconnect:
        ws_vitals.disconnect(ws)


@app.websocket("/ws/alerts")
async def ws_alerts_endpoint(ws: WebSocket):
    await ws_alerts.connect(ws)
    if state.recent_alerts:
        await ws.send_text(json.dumps({
            "type": "snapshot", "payload": state.recent_alerts[-50:],
        }, default=str))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_alerts.disconnect(ws)


@app.websocket("/ws/timeline")
async def ws_timeline_endpoint(ws: WebSocket):
    await ws_timeline.connect(ws)
    if state.timeline_events:
        await ws.send_text(json.dumps({
            "type": "snapshot", "payload": state.timeline_events[-100:],
        }, default=str))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_timeline.disconnect(ws)


@app.websocket("/ws/telemetry")
async def ws_telemetry_endpoint(ws: WebSocket):
    await ws_telemetry.connect(ws)
    if state.telemetry_feed:
        await ws.send_text(json.dumps({
            "type": "snapshot", "payload": state.telemetry_feed[-50:],
        }, default=str))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_telemetry.disconnect(ws)


# ──────────────────────────────────────────────────────────────────────────────
# Misc REST endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/telemetry", tags=["telemetry"])
async def get_recent_telemetry(limit: int = Query(100, ge=1, le=500)):
    """Return recent telemetry log (from DB)."""
    return await db.get_recent_telemetry(limit)


@app.get("/system/stats", tags=["system"])
async def get_system_stats():
    """Return live system health metrics."""
    elapsed      = time.time() - state.start_time if state.start_time else 1.0
    unacked      = await db.count_unacked_alerts()
    active_alerts = len([
        a for a in state.recent_alerts
        if not a.get("acknowledged", False)
    ])

    sim_stats = state.simulator.stats() if state.simulator else {}

    return {
        "packets_per_sec":    sim_stats.get("packets_per_sec", 0.0),
        "collisions_total":   state.collisions_total,
        "collisions_rate":    round(
            state.collisions_total / max(1, state.packets_processed), 4
        ),
        "active_alerts":      active_alerts,
        "unacked_alerts":     unacked,
        "uptime_seconds":     round(elapsed, 1),
        "patients_monitored": len(PATIENTS),
        "model_loaded":       state.risk_engine.model_loaded if state.risk_engine else False,
        "ws_connections": {
            "vitals":    ws_vitals.count,
            "alerts":    ws_alerts.count,
            "timeline":  ws_timeline.count,
            "telemetry": ws_telemetry.count,
        },
    }

@app.post("/system/trigger/deterioration", tags=["system"])
async def trigger_deterioration(patient_id: Optional[str] = None):
    """Force a deterioration event on the specified or a random patient."""
    if not state.simulator:
        return {"status": "error", "detail": "Simulator not running"}
    target = state.simulator.trigger_deterioration(patient_id)
    if target:
        return {"status": "success", "patient_id": target, "action": "forced_deterioration"}
    return {"status": "error", "detail": "All patients already deteriorating"}

@app.post("/system/trigger/collision", tags=["system"])
async def trigger_collision(patient_id: Optional[str] = None):
    """Force an identity collision event on the next packet for the specified or a random patient."""
    if not state.simulator:
        return {"status": "error", "detail": "Simulator not running"}
    target = state.simulator.trigger_collision(patient_id)
    return {"status": "success", "patient_id": target, "action": "forced_collision"}


@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok", "service": "SENTINEL", "version": "1.0.0"}
