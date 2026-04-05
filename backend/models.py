"""
SENTINEL — Pydantic Data Models

All shared data contracts used by the backend API, WebSocket
broadcaster, and database layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════════════════
# Enumerations
# ══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class RiskLevel(str, Enum):
    STABLE   = "STABLE"
    WARNING  = "WARNING"
    CRITICAL = "CRITICAL"


class AlertSeverity(str, Enum):
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class EventType(str, Enum):
    ADMISSION           = "ADMISSION"
    STATUS_CHANGE       = "STATUS_CHANGE"
    ALERT_FIRED         = "ALERT_FIRED"
    ALERT_ACKNOWLEDGED  = "ALERT_ACKNOWLEDGED"
    IDENTITY_COLLISION  = "IDENTITY_COLLISION"


# ══════════════════════════════════════════════════════════════════════════════
# Patient baseline
# ══════════════════════════════════════════════════════════════════════════════

class PatientBaseline(BaseModel):
    id:    str
    name:  str
    age:   int
    ward:  str
    hr:    float   = Field(..., description="Heart rate baseline (bpm)")
    bp:    float   = Field(..., description="Systolic blood pressure baseline (mmHg)")
    spo2:  float   = Field(..., description="Oxygen saturation baseline (%)")
    rr:    float   = Field(..., description="Respiratory rate baseline (breaths/min)")
    temp:  float   = Field(..., description="Temperature baseline (°C)")

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
# Vital reading (enriched with risk scores)
# ══════════════════════════════════════════════════════════════════════════════

class VitalReading(BaseModel):
    patient_id:       str
    timestamp:        datetime
    hr:               float
    bp:               float
    spo2:             float
    rr:               float
    temp:             float
    risk_score:       float = Field(..., ge=0.0, le=100.0)
    risk_level:       RiskLevel
    lstm_confidence:  float = Field(..., ge=0.0, le=1.0)
    news2_score:      int

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
# Alert
# ══════════════════════════════════════════════════════════════════════════════

class Alert(BaseModel):
    id:             int
    patient_id:     str
    patient_name:   str
    ward:           str
    triggered_at:   datetime
    severity:       AlertSeverity
    vitals:         VitalReading
    risk_score:     float
    acknowledged:   bool = False

    model_config = {"from_attributes": True}


class AlertAckRequest(BaseModel):
    alert_id: int


# ══════════════════════════════════════════════════════════════════════════════
# Timeline event
# ══════════════════════════════════════════════════════════════════════════════

class TimelineEvent(BaseModel):
    id:           Optional[int] = None
    patient_id:   str
    timestamp:    datetime
    event_type:   EventType
    detail:       str
    risk_level:   RiskLevel

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
# Telemetry packet
# ══════════════════════════════════════════════════════════════════════════════

class TelemetryPacket(BaseModel):
    timestamp:            datetime
    raw_hex:              str
    decoded_patient_id:   str
    resolved_patient_id:  str
    was_corrected:        bool
    confidence_score:     float = Field(..., ge=0.0, le=1.0)

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
# System stats
# ══════════════════════════════════════════════════════════════════════════════

class SystemStats(BaseModel):
    packets_per_sec:      float
    collisions_total:     int
    collisions_rate:      float          # collisions / total packets
    active_alerts:        int
    unacked_alerts:       int
    uptime_seconds:       float
    patients_monitored:   int
    model_loaded:         bool

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
# WebSocket message envelopes
# ══════════════════════════════════════════════════════════════════════════════

class WSMessage(BaseModel):
    type:    str                   # "vital" | "alert" | "timeline" | "telemetry"
    payload: dict

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
# Paginated response helper
# ══════════════════════════════════════════════════════════════════════════════

class PaginatedVitals(BaseModel):
    patient_id:  str
    total:       int
    page:        int
    page_size:   int
    items:       List[VitalReading]

    model_config = {"from_attributes": True}
