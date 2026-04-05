"""
SENTINEL — Identity Collision Detector & Resolver

Maintains a rolling baseline of the last 30 readings per patient.
Detects when an incoming packet's vitals don't match the claimed
patient ID and resolves it to the best-matching patient.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict, deque
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("sentinel.identity_resolver")

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

ROLLING_WINDOW  = 30     # number of recent readings per patient
COLLISION_RATIO = 2.5    # if dist_claimed > 2.5 * dist_nearest → collision
MIN_READINGS    = 5      # need at least this many readings to do resolution

VITAL_KEYS = ["hr", "bp", "spo2", "rr", "temp"]

# Normalisation scales to make vitals comparable in Euclidean space
# (rough physiological range spans for each vital)
VITAL_SCALES = {
    "hr":   200.0,   # max HR range
    "bp":   200.0,
    "spo2":  30.0,
    "rr":    56.0,
    "temp":   8.0,
}


# ──────────────────────────────────────────────────────────────────────────────
# Identity Resolver
# ──────────────────────────────────────────────────────────────────────────────

class IdentityResolver:
    """
    Stateful resolver that tracks per-patient vital baselines and uses
    Euclidean distance comparison to detect and fix identity collisions.
    """

    def __init__(self, patient_ids: list[str]):
        self._patient_ids = list(patient_ids)
        # Rolling window: patient_id → deque of vital dicts
        self._history: Dict[str, deque] = {
            pid: deque(maxlen=ROLLING_WINDOW) for pid in patient_ids
        }
        self._correction_count = 0
        self._total_count      = 0

    # ─── Baseline computation ───────────────────────────────────────────────

    def _get_baseline(self, patient_id: str) -> Optional[Dict[str, float]]:
        """Return the rolling mean vitals for a patient, or None if insufficient data."""
        history = self._history[patient_id]
        if len(history) < MIN_READINGS:
            return None

        baseline = {}
        for key in VITAL_KEYS:
            baseline[key] = sum(r[key] for r in history) / len(history)
        return baseline

    # ─── Euclidean distance ─────────────────────────────────────────────────

    @staticmethod
    def _euclidean_distance(
        vitals: Dict[str, float],
        baseline: Dict[str, float],
    ) -> float:
        """Normalised Euclidean distance between a reading and a baseline."""
        total = 0.0
        for key in VITAL_KEYS:
            diff    = (vitals[key] - baseline[key]) / VITAL_SCALES[key]
            total  += diff * diff
        return math.sqrt(total)

    # ─── Resolve a packet ───────────────────────────────────────────────────

    def resolve(
        self,
        claimed_patient_id: str,
        true_patient_id: str,        # ground truth from simulator (not available in real system)
        vitals: Dict[str, float],
    ) -> Tuple[str, bool, float]:
        """
        Resolve the true patient for an incoming reading.

        Args:
            claimed_patient_id : Patient ID in the packet (may be wrong)
            true_patient_id    : Ground-truth ID (from simulator; for tracking)
            vitals             : Current vital readings

        Returns:
            (resolved_id, was_corrected, confidence_score)
        """
        self._total_count += 1

        # Update rolling history with true patient's vitals
        if true_patient_id in self._history:
            self._history[true_patient_id].append(dict(vitals))

        # Get baseline for claimed patient
        claimed_baseline = self._get_baseline(claimed_patient_id)

        # If insufficient data, trust the claim
        if claimed_baseline is None:
            return claimed_patient_id, False, 1.0

        dist_claimed = self._euclidean_distance(vitals, claimed_baseline)

        # Compute distance to all other patients
        distances: Dict[str, float] = {}
        for pid in self._patient_ids:
            if pid == claimed_patient_id:
                continue
            baseline = self._get_baseline(pid)
            if baseline is None:
                continue
            distances[pid] = self._euclidean_distance(vitals, baseline)

        if not distances:
            return claimed_patient_id, False, 1.0

        # Find nearest alternative patient
        nearest_pid  = min(distances, key=distances.get)
        dist_nearest = distances[nearest_pid]

        # Collision detection logic
        if dist_nearest > 0 and dist_claimed > COLLISION_RATIO * dist_nearest:
            # Likely a collision — reassign
            self._correction_count += 1

            # Confidence = how certain we are that nearest is correct
            # (based on relative distance improvement)
            total_dist = dist_claimed + dist_nearest
            confidence = 1.0 - (dist_nearest / total_dist) if total_dist > 0 else 0.5
            confidence = round(min(1.0, max(0.0, confidence)), 4)

            logger.warning(
                f"Identity collision detected: claimed={claimed_patient_id} "
                f"but vitals match {nearest_pid} better "
                f"(d_claimed={dist_claimed:.3f}, d_nearest={dist_nearest:.3f}). "
                f"Resolved to {nearest_pid} (confidence={confidence:.3f})"
            )
            return nearest_pid, True, confidence

        # No collision — trust the claim
        # Confidence = how well vitals match claimed baseline
        total_dist = dist_claimed + dist_nearest
        match_confidence = 1.0 - (dist_claimed / (total_dist + 1e-9))
        match_confidence = round(min(1.0, max(0.0, match_confidence)), 4)

        return claimed_patient_id, False, match_confidence

    # ─── Stats ──────────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        return {
            "total_packets":    self._total_count,
            "corrections":      self._correction_count,
            "correction_rate":  round(
                self._correction_count / max(1, self._total_count), 4
            ),
            "history_sizes":    {
                pid: len(h) for pid, h in self._history.items()
            },
        }
