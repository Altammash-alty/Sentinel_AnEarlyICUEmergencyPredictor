/**
 * SENTINEL — Alert Feed
 * Real-time scrollable alert feed with filter, ACK, and CSV export.
 */
import { useState, useCallback } from "react";
import {
  severityColor, riskColor, hrColor, bpColor,
  spo2Color, rrColor, tempColor, timeElapsed, COLORS,
} from "../utils/riskColors";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const FILTERS  = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "ACKNOWLEDGED"];

function AlertFeed({ alerts, unackedCount }) {
  const [filter,  setFilter]  = useState("ALL");
  const [acking,  setAcking]  = useState({});

  const filtered = alerts.filter((a) => {
    if (filter === "ALL")          return true;
    if (filter === "ACKNOWLEDGED") return a.acknowledged;
    return a.severity === filter && !a.acknowledged;
  });

  const handleAck = useCallback(async (alertId) => {
    setAcking((p) => ({ ...p, [alertId]: true }));
    try {
      await fetch(`${API_BASE}/alerts/${alertId}/ack`, { method: "POST" });
    } catch (_) {}
    setAcking((p) => ({ ...p, [alertId]: false }));
  }, []);

  const handleExport = () => {
    const params = new URLSearchParams();
    if (filter === "ACKNOWLEDGED") params.set("acknowledged", "true");
    else if (filter !== "ALL") params.set("severity", filter);
    window.open(`${API_BASE}/alerts/export/csv?${params}`, "_blank");
  };

  return (
    <div className="panel alert-panel">
      <div className="panel-header">
        <div className="panel-title-row">
          <span className="panel-title">🚨 Alert Feed</span>
          {unackedCount > 0 && (
            <span className="unacked-badge">{unackedCount}</span>
          )}
        </div>
        <button className="icon-btn" onClick={handleExport} title="Export CSV">⬇</button>
      </div>

      {/* Filter tabs */}
      <div className="alert-filters">
        {FILTERS.map((f) => (
          <button
            key={f}
            className={`filter-tab ${filter === f ? "active" : ""}`}
            onClick={() => setFilter(f)}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Alert list */}
      <div className="alert-list">
        {filtered.length === 0 ? (
          <div className="empty-state">No alerts matching filter</div>
        ) : (
          filtered.map((alert, i) => (
            <AlertCard
              key={alert.id ?? i}
              alert={alert}
              onAck={() => handleAck(alert.id)}
              isAcking={!!acking[alert.id]}
            />
          ))
        )}
      </div>
    </div>
  );
}

function AlertCard({ alert, onAck, isAcking }) {
  const color     = severityColor(alert.severity);
  const isCrit    = alert.severity === "CRITICAL";
  const vitals    = alert.vitals || {};

  return (
    <div
      className={`alert-card ${isCrit && !alert.acknowledged ? "alert-pulsing" : ""} ${alert.acknowledged ? "alert-acked" : ""}`}
      style={{ borderLeft: (alert.severity === 'HIGH' || isCrit) ? `3px solid ${color}` : undefined }}
    >
      {/* Header */}
      <div className="alert-header">
        <span className="alert-severity-badge" style={{ background: `${color}1A`, color, border: `1px solid ${color}40`, padding: '2px 8px', borderRadius: '4px' }}>
          {alert.severity}
        </span>
        <span className="alert-patient">{alert.patient_name}</span>
        <span className="alert-ward">{alert.ward}</span>
        <span className="alert-time">{timeElapsed(alert.triggered_at)}</span>
      </div>

      {/* Risk score */}
      <div className="alert-risk-row">
        <span className="alert-risk-label">Risk Score</span>
        <span className="alert-risk-val" style={{ color }}>
          {alert.risk_score?.toFixed(1)}
        </span>
      </div>

      {/* Abnormal vitals */}
      {vitals && (
        <div className="alert-vitals">
          <AbnormalVital label="HR"   value={vitals.hr}   color={hrColor(vitals.hr)}   fmt={(x) => `${Math.round(x)} bpm`}  />
          <AbnormalVital label="BP"   value={vitals.bp}   color={bpColor(vitals.bp)}   fmt={(x) => `${Math.round(x)} mmHg`} />
          <AbnormalVital label="SpO₂" value={vitals.spo2} color={spo2Color(vitals.spo2)} fmt={(x) => `${x?.toFixed(1)}%`}  />
          <AbnormalVital label="RR"   value={vitals.rr}   color={rrColor(vitals.rr)}   fmt={(x) => `${Math.round(x)} br/m`} />
          <AbnormalVital label="Temp" value={vitals.temp} color={tempColor(vitals.temp)} fmt={(x) => `${x?.toFixed(1)}°C`} />
        </div>
      )}

      {/* ACK button */}
      {!alert.acknowledged && (
        <button
          className="ack-btn"
          onClick={onAck}
          disabled={isAcking}
        >
          {isAcking ? "…" : "✓ Acknowledge"}
        </button>
      )}
      {alert.acknowledged && (
        <div className="acked-label">✓ Acknowledged</div>
      )}
    </div>
  );
}

function AbnormalVital({ label, value, color, fmt }) {
  const isAbnormal = color !== COLORS.text;
  if (!isAbnormal || value == null) return null;
  return (
    <span className="alert-vital-chip" style={{ background: '#141b2d', color, border: '1px solid #1e2a3a', borderRadius: '4px', padding: '2px 8px', fontSize: '11px' }}>
      {label}: {fmt(value)}
    </span>
  );
}

export default AlertFeed;
