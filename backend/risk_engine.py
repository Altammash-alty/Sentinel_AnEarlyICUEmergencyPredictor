"""
SENTINEL — LSTM + NEWS2 Hybrid Risk Engine

Loads the trained LSTM model on startup.
Maintains a 60-step rolling window per patient.
Computes hybrid risk score: 70% LSTM + 30% NEWS2.
"""

from __future__ import annotations

import logging
import os
import sys
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import numpy as np
import torch
import joblib

logger = logging.getLogger("sentinel.risk_engine")

# ──────────────────────────────────────────────────────────────────────────────
# Model paths (from env or defaults)
# ──────────────────────────────────────────────────────────────────────────────

_ML_DIR       = os.path.join(os.path.dirname(__file__), "..", "ml")
MODEL_PATH    = os.getenv(
    "MODEL_PATH",
    os.path.join(_ML_DIR, "saved_model", "sentinel_lstm.pt"),
)
SCALER_PATH   = os.getenv(
    "SCALER_PATH",
    os.path.join(_ML_DIR, "saved_model", "scaler.pkl"),
)

WINDOW_SIZE   = 60
VITAL_KEYS    = ["hr", "bp", "spo2", "rr", "temp"]


# ──────────────────────────────────────────────────────────────────────────────
# NEWS2 scorer  (National Early Warning Score 2)
# ──────────────────────────────────────────────────────────────────────────────

def compute_news2(hr: float, bp: float, spo2: float, rr: float, temp: float) -> int:
    """
    Simplified NEWS2 scoring based on vital sign ranges.
    Returns integer score 0–20.
    """
    score = 0

    # Respiratory Rate (breaths/min)
    if rr <= 8:        score += 3
    elif rr <= 11:     score += 1
    elif rr <= 20:     score += 0
    elif rr <= 24:     score += 2
    else:              score += 3

    # SpO2 Scale 1 (%)
    if spo2 <= 91:     score += 3
    elif spo2 <= 93:   score += 2
    elif spo2 <= 95:   score += 1
    else:              score += 0

    # Systolic BP (mmHg)
    if bp <= 90:       score += 3
    elif bp <= 100:    score += 2
    elif bp <= 110:    score += 1
    elif bp <= 219:    score += 0
    else:              score += 3

    # Heart Rate (bpm)
    if hr <= 40:       score += 3
    elif hr <= 50:     score += 1
    elif hr <= 90:     score += 0
    elif hr <= 110:    score += 1
    elif hr <= 130:    score += 2
    else:              score += 3

    # Temperature (°C)
    if temp <= 35.0:        score += 3
    elif temp <= 36.0:      score += 1
    elif temp <= 38.0:      score += 0
    elif temp <= 39.0:      score += 1
    else:                   score += 2

    return score


# ──────────────────────────────────────────────────────────────────────────────
# Risk level mapping
# ──────────────────────────────────────────────────────────────────────────────

def score_to_level(score: float) -> str:
    if score >= 70.0:
        return "CRITICAL"
    elif score >= 40.0:
        return "WARNING"
    return "STABLE"


# ──────────────────────────────────────────────────────────────────────────────
# Risk Engine
# ──────────────────────────────────────────────────────────────────────────────

class RiskEngine:
    """
    Maintains per-patient rolling windows and performs LSTM inference.
    Falls back to NEWS2-only when < 60 readings are available.
    """

    def __init__(self):
        self._model             = None
        self._scaler            = None
        self._device            = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._windows: Dict[str, deque] = {}
        self._model_loaded      = False

    # ─── Startup ────────────────────────────────────────────────────────────

    def load_model(self):
        """Load LSTM model and scaler from disk."""
        try:
            # Import here to avoid circular dependency at module load time
            sys.path.insert(0, _ML_DIR)
            from lstm_model import SentinelLSTM  # type: ignore

            checkpoint = torch.load(MODEL_PATH, map_location=self._device)
            model = SentinelLSTM()
            model.load_state_dict(checkpoint["model_state"])
            model.to(self._device)
            model.eval()
            self._model = model

            self._scaler = joblib.load(SCALER_PATH)
            self._model_loaded = True
            logger.info(
                f"✓ LSTM model loaded (epoch {checkpoint['epoch']}, "
                f"val_loss={checkpoint['val_loss']:.4f}) on {self._device}"
            )
        except FileNotFoundError as e:
            logger.warning(
                f"Model files not found ({e}). "
                f"Using NEWS2-only fallback mode."
            )
            self._model_loaded = False

    def _ensure_window(self, patient_id: str):
        if patient_id not in self._windows:
            self._windows[patient_id] = deque(maxlen=WINDOW_SIZE)

    # ─── NEWS2-only score ───────────────────────────────────────────────────

    def _news2_score(self, vitals: Dict[str, float]) -> Dict[str, Any]:
        news2 = compute_news2(
            vitals["hr"], vitals["bp"],
            vitals["spo2"], vitals["rr"], vitals["temp"],
        )
        # NEWS2 max ~ 20 → scale to 0-100
        score = min(100.0, news2 * 5.0)
        return {
            "risk_score":      round(score, 2),
            "risk_level":      score_to_level(score),
            "lstm_confidence": 0.0,
            "news2_score":     news2,
        }

    # ─── LSTM inference ─────────────────────────────────────────────────────

    def _lstm_score(
        self,
        window: deque,
        vitals: Dict[str, float],
    ) -> Dict[str, Any]:
        """Run LSTM on the full 60-step window and compute hybrid score."""
        arr = np.array([[r["hr"], r["bp"], r["spo2"], r["rr"], r["temp"]]
                        for r in window], dtype=np.float32)  # (60, 5)

        # Scale
        arr_2d    = arr.reshape(-1, 5)
        arr_scaled = self._scaler.transform(arr_2d).reshape(1, WINDOW_SIZE, 5)

        x = torch.FloatTensor(arr_scaled).to(self._device)
        with torch.no_grad():
            probs = self._model(x)[0].cpu().numpy()  # [P_stable, P_det, P_crit]

        p_det  = float(probs[1])
        p_crit = float(probs[2])
        confidence = float(max(probs))

        lstm_score = (p_det * 50.0) + (p_crit * 100.0)

        news2      = compute_news2(
            vitals["hr"], vitals["bp"],
            vitals["spo2"], vitals["rr"], vitals["temp"],
        )
        news2_score_scaled = news2 * 4.5   # map NEWS2 0-20 → 0-90

        hybrid = (lstm_score * 0.7) + (news2_score_scaled * 0.3)
        hybrid = round(min(100.0, max(0.0, hybrid)), 2)

        return {
            "risk_score":      hybrid,
            "risk_level":      score_to_level(hybrid),
            "lstm_confidence": round(confidence, 4),
            "news2_score":     news2,
        }

    # ─── Main scoring entry-point ────────────────────────────────────────────

    def score(
        self,
        patient_id: str,
        vitals: Dict[str, float],
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Add vitals to the patient's rolling window and return VitalReading dict.
        """
        self._ensure_window(patient_id)
        window = self._windows[patient_id]
        window.append(dict(vitals))

        ts = timestamp or datetime.now(timezone.utc)

        if self._model_loaded and len(window) >= WINDOW_SIZE:
            scores = self._lstm_score(window, vitals)
        else:
            scores = self._news2_score(vitals)

        return {
            "patient_id":      patient_id,
            "timestamp":       ts,
            "hr":              vitals["hr"],
            "bp":              vitals["bp"],
            "spo2":            vitals["spo2"],
            "rr":              vitals["rr"],
            "temp":            vitals["temp"],
            "risk_score":      scores["risk_score"],
            "risk_level":      scores["risk_level"],
            "lstm_confidence": scores["lstm_confidence"],
            "news2_score":     scores["news2_score"],
        }

    @property
    def model_loaded(self) -> bool:
        return self._model_loaded
