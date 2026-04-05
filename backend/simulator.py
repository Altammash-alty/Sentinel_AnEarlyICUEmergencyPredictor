"""
SENTINEL — Live ICU Telemetry Simulator

Simulates 5 live ICU patients, generating vital sign packets every 2 seconds.
- Vitals encoded as hex
- 5% chance of patient ID swap (identity collision simulation)
- Random deterioration events every ~90 seconds
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sentinel.simulator")

# ──────────────────────────────────────────────────────────────────────────────
# Patient definitions
# ──────────────────────────────────────────────────────────────────────────────

PATIENTS = [
    {
        "id":   "P001",
        "name": "James Thornton",
        "age":  67,
        "ward": "ICU-A",
        "hr":   72.0, "bp": 120.0, "spo2": 98.0, "rr": 14.0, "temp": 36.6,
    },
    {
        "id":   "P002",
        "name": "Margaret Chen",
        "age":  74,
        "ward": "ICU-A",
        "hr":   76.0, "bp": 135.0, "spo2": 95.0, "rr": 18.0, "temp": 36.8,
    },
    {
        "id":   "P003",
        "name": "David Okafor",
        "age":  55,
        "ward": "ICU-B",
        "hr":   88.0, "bp": 110.0, "spo2": 96.0, "rr": 20.0, "temp": 37.2,
    },
    {
        "id":   "P004",
        "name": "Sofia Reyes",
        "age":  48,
        "ward": "ICU-B",
        "hr":   95.0, "bp": 105.0, "spo2": 94.0, "rr": 22.0, "temp": 38.5,
    },
    {
        "id":   "P005",
        "name": "Robert Kim",
        "age":  61,
        "ward": "ICU-C",
        "hr":   82.0, "bp": 145.0, "spo2": 96.0, "rr": 16.0, "temp": 37.0,
    },
]

PATIENT_IDS = [p["id"] for p in PATIENTS]
COLLISION_PROBABILITY = 0.05   # 5% chance of ID swap


# ──────────────────────────────────────────────────────────────────────────────
# Physiological clipping ranges
# ──────────────────────────────────────────────────────────────────────────────

VITALS_CLIP = {
    "hr":   (20.0, 220.0),
    "bp":   (50.0, 250.0),
    "spo2": (70.0, 100.0),
    "rr":   (4.0, 60.0),
    "temp": (34.0, 42.0),
}


def clip_vital(name: str, value: float) -> float:
    lo, hi = VITALS_CLIP[name]
    return max(lo, min(hi, value))


# ──────────────────────────────────────────────────────────────────────────────
# Deterioration event state
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class DeteriorationEvent:
    patient_id:  str
    started_at:  float                      # time.time()
    duration_s:  float                      # how long the event lasts
    hr_delta:    float
    bp_delta:    float
    spo2_delta:  float
    rr_delta:    float
    temp_delta:  float


# ──────────────────────────────────────────────────────────────────────────────
# Simulator class
# ──────────────────────────────────────────────────────────────────────────────

class ICUSimulator:
    """
    Generates realistic hex-encoded vital-sign packets for 5 ICU patients.
    Every 2 seconds per patient → ~2.5 packets/sec total.
    """

    def __init__(self, output_queue: asyncio.Queue):
        self._queue             = output_queue
        self._running           = False
        self._start_time        = 0.0
        self._packet_count      = 0
        self._collision_count   = 0
        self._active_events: Dict[str, DeteriorationEvent] = {}
        self._last_event_check  = 0.0
        self._patient_map       = {p["id"]: p for p in PATIENTS}

    # ─── Vital generation ───────────────────────────────────────────────────

    def _current_vitals(self, patient_id: str) -> Dict[str, float]:
        """
        Generate current vitals for a patient:
          baseline + small jitter (±2% baseline)
          plus any active deterioration delta.
        """
        p = self._patient_map[patient_id]
        now = time.time()

        # Base noise (small jitter)
        vitals = {
            "hr":   p["hr"]   + random.gauss(0, 2.0),
            "bp":   p["bp"]   + random.gauss(0, 3.0),
            "spo2": p["spo2"] + random.gauss(0, 0.5),
            "rr":   p["rr"]   + random.gauss(0, 1.0),
            "temp": p["temp"] + random.gauss(0, 0.1),
        }

        # Apply deterioration event deltas if active
        evt = self._active_events.get(patient_id)
        if evt:
            elapsed = now - evt.started_at
            if elapsed < evt.duration_s:
                # Ramp: first 20% → ramp up, then sustain
                ramp = min(1.0, elapsed / (evt.duration_s * 0.2))
                vitals["hr"]   += evt.hr_delta   * ramp
                vitals["bp"]   += evt.bp_delta   * ramp
                vitals["spo2"] += evt.spo2_delta * ramp
                vitals["rr"]   += evt.rr_delta   * ramp
                vitals["temp"] += evt.temp_delta * ramp
            else:
                # Event over → gradual recovery
                del self._active_events[patient_id]

        # Clip to valid ranges
        return {k: round(clip_vital(k, v), 2) for k, v in vitals.items()}

    # ─── Deterioration trigger ──────────────────────────────────────────────

    def trigger_deterioration(self, patient_id: Optional[str] = None, severity: str = "severe") -> Optional[str]:
        now = time.time()
        
        target = patient_id
        if not target:
            candidates = [
                pid for pid in PATIENT_IDS
                if pid not in self._active_events
            ]
            if not candidates:
                return None
            target = random.choice(candidates)

        if severity == "severe":
            evt = DeteriorationEvent(
                patient_id  = target,
                started_at  = now,
                duration_s  = random.uniform(60, 120),
                hr_delta    = random.uniform(40, 60),
                bp_delta    = random.uniform(-50, -30),
                spo2_delta  = random.uniform(-15, -8),
                rr_delta    = random.uniform(10, 15),
                temp_delta  = random.uniform(1.5, 2.5),
            )
        else:
            evt = DeteriorationEvent(
                patient_id  = target,
                started_at  = now,
                duration_s  = random.uniform(60, 120),
                hr_delta    = random.uniform(10, 25),
                bp_delta    = random.uniform(-20, -10),
                spo2_delta  = random.uniform(-5, -2),
                rr_delta    = random.uniform(3, 6),
                temp_delta  = random.uniform(0.3, 0.8),
            )

        self._active_events[target] = evt
        logger.info(
            f"Deterioration event triggered manually on {target} "
            f"(severity={severity}, duration={evt.duration_s:.0f}s)"
        )
        return target

    def trigger_collision(self, patient_id: Optional[str] = None) -> Optional[str]:
        # Forces a collision on the next packet for given patient. Tracked via a flag.
        if not hasattr(self, "_forced_collision"):
            self._forced_collision = set()
        
        target = patient_id
        if not target:
            target = random.choice(PATIENT_IDS)
            
        self._forced_collision.add(target)
        return target

    def _maybe_trigger_deterioration(self):
        now = time.time()
        if now - self._last_event_check < 90.0:
            return
        self._last_event_check = now
        
        # We don't auto trigger if there's already active ones (to keep it clean)
        self.trigger_deterioration(severity=random.choice(["mild", "severe"]))

    # ─── Hex encoding ───────────────────────────────────────────────────────

    @staticmethod
    def _encode_packet(patient_id: str, vitals: Dict[str, float]) -> str:
        payload = {
            "patient_id": patient_id,
            "hr":   vitals["hr"],
            "bp":   vitals["bp"],
            "spo2": vitals["spo2"],
            "rr":   vitals["rr"],
            "temp": vitals["temp"],
            "ts":   datetime.now(timezone.utc).isoformat(),
        }
        raw_bytes = json.dumps(payload).encode("utf-8")
        return raw_bytes.hex()

    # ─── Identity collision simulation ──────────────────────────────────────

    def _maybe_swap_id(self, true_id: str) -> str:
        """With 5% probability, or if forced, swap the patient ID to simulate collision."""
        forced = hasattr(self, "_forced_collision") and true_id in self._forced_collision
        if forced or random.random() < COLLISION_PROBABILITY:
            if forced:
                self._forced_collision.remove(true_id)
            others = [pid for pid in PATIENT_IDS if pid != true_id]
            return random.choice(others)
        return true_id

    # ─── Per-patient loop ───────────────────────────────────────────────────

    async def _patient_loop(self, patient: Dict[str, Any]):
        """Generate and enqueue one packet every 2 seconds for this patient."""
        patient_id = patient["id"]
        interval   = 2.0

        while self._running:
            try:
                self._maybe_trigger_deterioration()
                vitals        = self._current_vitals(patient_id)
                claimed_id    = self._maybe_swap_id(patient_id)
                raw_hex       = self._encode_packet(claimed_id, vitals)

                packet = {
                    "true_patient_id":   patient_id,
                    "claimed_patient_id": claimed_id,
                    "raw_hex":           raw_hex,
                    "vitals":            vitals,
                    "timestamp":         datetime.now(timezone.utc).isoformat(),
                }

                await self._queue.put(packet)
                self._packet_count += 1
                if claimed_id != patient_id:
                    self._collision_count += 1

            except Exception as exc:
                logger.error(f"Simulator error for {patient_id}: {exc}")

            await asyncio.sleep(interval)

    # ─── Public API ─────────────────────────────────────────────────────────

    async def start(self):
        self._running    = True
        self._start_time = time.time()
        logger.info(f"ICU Simulator starting for {len(PATIENTS)} patients ...")
        tasks = [
            asyncio.create_task(self._patient_loop(p), name=f"sim_{p['id']}")
            for p in PATIENTS
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    def stop(self):
        self._running = False

    def stats(self) -> Dict[str, Any]:
        elapsed = time.time() - self._start_time if self._start_time else 1
        return {
            "packets_total":    self._packet_count,
            "packets_per_sec":  round(self._packet_count / elapsed, 2),
            "collisions_total": self._collision_count,
            "collision_rate":   round(
                self._collision_count / max(1, self._packet_count), 4
            ),
            "uptime_seconds":   round(elapsed, 1),
            "active_events":    list(self._active_events.keys()),
        }
