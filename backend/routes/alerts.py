"""
SENTINEL — Alert REST Endpoints
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend import database as db

logger = logging.getLogger("sentinel.routes.alerts")
router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/")
async def list_alerts(
    severity:     Optional[str]  = Query(None, description="Filter by severity: MEDIUM|HIGH|CRITICAL"),
    acknowledged: Optional[bool] = Query(None, description="Filter by ack status"),
    limit:        int             = Query(100, ge=1, le=500),
):
    """Return alerts with optional severity / acknowledged filters."""
    alerts = await db.get_alerts(severity=severity, acknowledged=acknowledged, limit=limit)
    return alerts


@router.post("/{alert_id}/ack")
async def acknowledge_alert(alert_id: int):
    """Acknowledge an alert by ID."""
    success = await db.acknowledge_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    # Emit timeline event for acknowledgement
    try:
        from backend.main import state
        from backend import database as db2
        import datetime, pytz

        alert_rows = await db2.get_alerts(limit=500)
        # Find the specific alert
        alert = next((a for a in alert_rows if a["id"] == alert_id), None)
        if alert:
            await db2.insert_timeline_event({
                "patient_id": alert["patient_id"],
                "timestamp":  datetime.datetime.now(datetime.timezone.utc),
                "event_type": "ALERT_ACKNOWLEDGED",
                "detail":     f"Alert #{alert_id} acknowledged by operator",
                "risk_level": "STABLE",
            })
    except Exception as exc:
        logger.warning(f"Could not create timeline event for ack: {exc}")

    return {"acknowledged": True, "alert_id": alert_id}


@router.get("/export/csv")
async def export_alerts_csv(
    severity:     Optional[str]  = Query(None),
    acknowledged: Optional[bool] = Query(None),
):
    """Download all matching alerts as a CSV file."""
    alerts = await db.get_alerts(severity=severity, acknowledged=acknowledged, limit=10000)

    output = io.StringIO()
    if alerts:
        fieldnames = [k for k in alerts[0].keys() if k != "vitals"]
        writer     = csv.DictWriter(output, fieldnames=fieldnames + ["vitals_json"])
        writer.writeheader()
        for a in alerts:
            row = {k: v for k, v in a.items() if k != "vitals"}
            row["vitals_json"] = str(a.get("vitals", ""))
            writer.writerow(row)
    else:
        output.write("No alerts found\n")

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sentinel_alerts.csv"},
    )


@router.get("/stats/summary")
async def alert_stats():
    """Return alert count statistics."""
    all_alerts    = await db.get_alerts(limit=10000)
    unacked_count = await db.count_unacked_alerts()

    by_severity = {}
    for a in all_alerts:
        sev = a.get("severity", "UNKNOWN")
        by_severity[sev] = by_severity.get(sev, 0) + 1

    return {
        "total":          len(all_alerts),
        "unacknowledged": unacked_count,
        "by_severity":    by_severity,
    }
