"""
SENTINEL — Alert Engine

Monitors vital readings and fires alerts based on:
  - risk_level == CRITICAL
  - risk_level transition STABLE → WARNING
  - Same patient in WARNING for 3+ consecutive readings

Enforces 60-second per-patient cooldown to prevent alert storms.
Broadcasts to WebSocket clients and persists to PostgreSQL.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

logger = logging.getLogger("sentinel.alert_engine")

COOLDOWN_SECONDS        = 60
WARNING_STREAK_THRESHOLD = 3   # consecutive WARNING readings before firing


class AlertEngine:
    """
    Stateful alert engine that processes VitalReading dicts and fires alerts.
    """

    def __init__(self):
        # Per-patient state
        self._last_alert_time: Dict[str, float]   = defaultdict(lambda: 0.0)
        self._last_risk_level: Dict[str, str]     = {}
        self._warning_streak:  Dict[str, int]     = defaultdict(int)
        self._active_critical: Set[str]           = set()

        # Callbacks registered by main.py
        self._on_alert: Optional[Callable[..., Coroutine]] = None

        import time
        self._time = time

    def set_alert_callback(self, callback: Callable[..., Coroutine]):
        """Register the async function to call when an alert fires."""
        self._on_alert = callback

    # ─── Cooldown check ─────────────────────────────────────────────────────

    def _is_on_cooldown(self, patient_id: str) -> bool:
        elapsed = self._time.time() - self._last_alert_time[patient_id]
        return elapsed < COOLDOWN_SECONDS

    def _mark_alerted(self, patient_id: str):
        self._last_alert_time[patient_id] = self._time.time()

    # ─── Alert creation ─────────────────────────────────────────────────────

    def _build_alert(
        self,
        reading: Dict[str, Any],
        patient_info: Dict[str, Any],
        severity: str,
    ) -> Dict[str, Any]:
        return {
            "patient_id":   reading["patient_id"],
            "patient_name": patient_info["name"],
            "ward":         patient_info["ward"],
            "triggered_at": datetime.now(timezone.utc),
            "severity":     severity,
            "vitals": {
                "patient_id":      reading["patient_id"],
                "timestamp":       reading["timestamp"].isoformat()
                    if isinstance(reading["timestamp"], datetime)
                    else reading["timestamp"],
                "hr":              reading["hr"],
                "bp":              reading["bp"],
                "spo2":            reading["spo2"],
                "rr":              reading["rr"],
                "temp":            reading["temp"],
                "risk_score":      reading["risk_score"],
                "risk_level":      reading["risk_level"],
                "lstm_confidence": reading["lstm_confidence"],
                "news2_score":     reading["news2_score"],
            },
            "risk_score":  reading["risk_score"],
            "acknowledged": False,
        }

    # ─── Main processing ────────────────────────────────────────────────────

    async def process(
        self,
        reading: Dict[str, Any],
        patient_info: Dict[str, Any],
        db_insert_fn,        # async callable: insert_alert(dict) → int
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate a VitalReading for alert conditions.
        Returns the alert dict if one was fired, else None.
        """
        pid       = reading["patient_id"]
        level     = reading["risk_level"]
        prev_level = self._last_risk_level.get(pid, "STABLE")

        # Update streak
        if level == "WARNING":
            self._warning_streak[pid] += 1
        else:
            self._warning_streak[pid] = 0

        # Track critical state
        if level == "CRITICAL":
            self._active_critical.add(pid)
        else:
            self._active_critical.discard(pid)

        # ── Determine if we should fire ─────────────────────────────────

        should_fire = False
        severity    = "MEDIUM"

        if level == "CRITICAL" and not self._is_on_cooldown(pid):
            should_fire = True
            severity    = "CRITICAL"

        elif (prev_level == "STABLE" and level == "WARNING"
              and not self._is_on_cooldown(pid)):
            should_fire = True
            severity    = "HIGH"

        elif (self._warning_streak[pid] >= WARNING_STREAK_THRESHOLD
              and level == "WARNING"
              and not self._is_on_cooldown(pid)):
            should_fire = True
            severity    = "HIGH"

        # Update previous level
        self._last_risk_level[pid] = level

        if not should_fire:
            return None

        # ── Fire alert ──────────────────────────────────────────────────

        self._mark_alerted(pid)
        alert = self._build_alert(reading, patient_info, severity)

        try:
            # Persist to DB
            alert["id"] = await db_insert_fn(alert)
        except Exception as exc:
            logger.error(f"Failed to insert alert to DB: {exc}")
            alert["id"] = -1

        logger.warning(
            f"🚨 ALERT [{severity}] patient={pid} "
            f"risk_score={reading['risk_score']:.1f} "
            f"risk_level={level}"
        )

        # Broadcast via callback
        if self._on_alert:
            try:
                await self._on_alert(alert)
            except Exception as exc:
                logger.error(f"Alert callback error: {exc}")

        return alert

    # ─── State getters ───────────────────────────────────────────────────────

    @property
    def active_critical_patients(self) -> Set[str]:
        return self._active_critical

    def warning_streak(self, patient_id: str) -> int:
        return self._warning_streak[patient_id]
