"""
SENTINEL — Timeline REST Endpoints
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend import database as db

logger = logging.getLogger("sentinel.routes.timeline")
router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("/")
async def get_full_timeline(limit: int = Query(200, ge=1, le=1000)):
    """Return timeline events for all patients ordered by time ascending."""
    events = await db.get_timeline(patient_id=None, limit=limit)
    return events


@router.get("/{patient_id}")
async def get_patient_timeline(
    patient_id: str,
    limit: int = Query(100, ge=1, le=500),
):
    """Return timeline events for a single patient."""
    # Verify patient exists
    patient = await db.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

    events = await db.get_timeline(patient_id=patient_id, limit=limit)
    return {
        "patient_id": patient_id,
        "events":     events,
    }
