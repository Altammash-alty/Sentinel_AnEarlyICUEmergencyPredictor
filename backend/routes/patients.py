"""
SENTINEL — Patient REST Endpoints
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from backend import database as db

logger = logging.getLogger("sentinel.routes.patients")
router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/")
async def list_patients(include_current_vitals: bool = True):
    """Return all monitored patients with their latest vital reading."""
    from backend.main import state  # imported late to avoid circular import

    patients = await db.get_all_patients()
    result = []
    for p in patients:
        entry = {
            "id":   p["id"],
            "name": p["name"],
            "age":  p["age"],
            "ward": p["ward"],
            "baseline_vitals": p["baseline_vitals"],
        }
        if include_current_vitals:
            entry["current_vitals"] = state.latest_vitals.get(p["id"])
        result.append(entry)
    return result


@router.get("/{patient_id}")
async def get_patient_detail(patient_id: str):
    """Return patient detail plus 1-hour vital history."""
    patient = await db.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

    history = await db.get_patient_vitals_last_hour(patient_id)

    from backend.main import state
    return {
        "patient":        patient,
        "current_vitals": state.latest_vitals.get(patient_id),
        "history":        history,
    }


@router.get("/{patient_id}/vitals")
async def get_patient_vitals(
    patient_id: str,
    page:      int = Query(1,   ge=1),
    page_size: int = Query(60,  ge=1, le=500),
):
    """Return paginated vital readings for a patient."""
    patient = await db.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

    offset = (page - 1) * page_size
    items  = await db.get_patient_vitals_history(patient_id, limit=page_size, offset=offset)

    return {
        "patient_id": patient_id,
        "page":       page,
        "page_size":  page_size,
        "total":      len(items),
        "items":      items,
    }
