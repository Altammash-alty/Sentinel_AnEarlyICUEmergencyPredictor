/**
 * SENTINEL — Patient Grid
 * 5 patient cards with live vitals, risk score gauge, and pulse animations.
 */
import { useMemo } from "react";
import {
  riskColor, riskGlow, hrColor, bpColor, spo2Color, rrColor, tempColor,
  scoreColor, PATIENT_COLORS, COLORS,
} from "../utils/riskColors";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function PatientGrid({ patients }) {
  return (
    <div className="patient-grid">
      {patients.map((p) => (
        <PatientCard key={p.id} patient={p} />
      ))}
    </div>
  );
}

function PatientCard({ patient }) {
  const v         = patient.currentVitals;
  const level     = v?.risk_level ?? "STABLE";
  const score     = v?.risk_score ?? 0;
  const isCrit    = level === "CRITICAL";
  const isWarn    = level === "WARNING";
  const color     = riskColor(level);
  const glow      = riskGlow(level);
  const patColor  = PATIENT_COLORS[patient.id] || "#60a5fa";

  const updatedAt = v?.timestamp
    ? new Date(v.timestamp).toLocaleTimeString("en-US", { hour12: false })
    : null;

  return (
    <div
      className={`patient-card ${isCrit ? "card-critical" : isWarn ? "card-warning" : "card-stable"}`}
      style={{ borderLeft: `3px solid ${color}`, boxShadow: glow }}
    >
      {/* Pulse ring on CRITICAL */}
      {isCrit && <div className="pulse-ring" style={{ borderColor: color }} />}

      {/* Card header */}
      <div className="card-header">
        <div className="card-id-badge" style={{ background: `${patColor}22`, color: patColor }}>
          {patient.id}
        </div>
        <div className="card-ward">{patient.ward}</div>
        <button 
          title="Trigger Crisis for this patient"
          onClick={(e) => {
            e.stopPropagation();
            fetch(`${API_BASE}/system/trigger/deterioration?patient_id=${patient.id}`, { method: "POST" }).catch(console.error);
          }}
          style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid #ef4444', borderRadius: '4px', color: '#ef4444', cursor: 'pointer', fontSize: '10px', padding: '2px 6px', marginLeft: 'auto', marginRight: '4px', zIndex: 10 }}
        >
          ⚕ Trigger
        </button>
        <RiskLevelBadge level={level} color={color} />
      </div>

      {/* Patient name */}
      <div className="card-name">{patient.name}</div>
      <div className="card-age">Age {patient.age}</div>

      {/* Vital badges */}
      <div className="vitals-grid">
        <VitalBadge label="HR"   value={v?.hr}   unit="bpm"  color={hrColor(v?.hr)}   fmt={(x) => Math.round(x)} />
        <VitalBadge label="BP"   value={v?.bp}   unit="mmHg" color={bpColor(v?.bp)}   fmt={(x) => Math.round(x)} />
        <VitalBadge label="SpO₂" value={v?.spo2} unit="%"    color={spo2Color(v?.spo2)} fmt={(x) => x?.toFixed(1)} />
        <VitalBadge label="RR"   value={v?.rr}   unit="br/m" color={rrColor(v?.rr)}   fmt={(x) => Math.round(x)} />
        <VitalBadge label="Temp" value={v?.temp} unit="°C"   color={tempColor(v?.temp)} fmt={(x) => x?.toFixed(1)} />
      </div>

      {/* Risk Gauge */}
      <div className="gauge-row">
        <RiskGauge score={score} color={color} />
        <div className="gauge-info">
          <span className="gauge-score" style={{ color }}>
            {v != null ? score.toFixed(1) : "—"}
          </span>
          <span className="gauge-label">Risk Score</span>
          {v != null && (
            <span className="lstm-confidence">
              LSTM {(v.lstm_confidence * 100).toFixed(0)}%
            </span>
          )}
        </div>
      </div>

      {/* NEWS2 score */}
      {v != null && (
        <div className="news2-row">
          <span className="news2-label">NEWS2</span>
          <span className="news2-val" style={{ color: scoreColor(v.news2_score * 5) }}>
            {v.news2_score}
          </span>
        </div>
      )}

      {/* Timestamp */}
      {updatedAt && (
        <div className="card-timestamp">Updated {updatedAt}</div>
      )}

      {!v && (
        <div className="card-awaiting">Awaiting data…</div>
      )}
    </div>
  );
}

function VitalBadge({ label, value, unit, color, fmt }) {
  const display = value != null ? `${fmt(value)} ${unit}` : "—";
  return (
    <div className="vital-badge">
      <span className="vital-label">{label}</span>
      <span className="vital-value" style={{ color }}>
        {display}
      </span>
    </div>
  );
}

function RiskLevelBadge({ level, color }) {
  const isCrit = level === "CRITICAL";
  return (
    <div
      className={`risk-level-badge ${isCrit ? 'pulse' : ''}`}
      style={{ background: `${color}1A`, color, border: `1px solid ${color}40`, letterSpacing: '0.1em' }}
    >
      {level}
    </div>
  );
}

function RiskGauge({ score, color }) {
  const radius = 28;
  const stroke = 5;
  const norm   = score / 100;
  const circ   = 2 * Math.PI * radius;
  const dash   = norm * circ;

  return (
    <svg width="72" height="72" viewBox="0 0 72 72" className="gauge-svg">
      {/* Background track */}
      <circle
        cx="36" cy="36" r={radius}
        fill="none"
        stroke="#1a2e52"
        strokeWidth={stroke}
      />
      {/* Progress arc */}
      <circle
        cx="36" cy="36" r={radius}
        fill="none"
        stroke={color}
        strokeWidth={stroke}
        strokeDasharray={`${dash} ${circ - dash}`}
        strokeDashoffset={circ * 0.25}
        strokeLinecap="round"
        style={{ transition: "stroke-dasharray 0.6s ease" }}
      />
    </svg>
  );
}

export default PatientGrid;
