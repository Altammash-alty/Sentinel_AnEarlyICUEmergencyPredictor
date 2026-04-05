/**
 * SENTINEL — Patient Flow Timeline
 * Horizontal per-patient timeline with event nodes and modal detail view.
 */
import { useState } from "react";
import { riskColor, COLORS, timeElapsed } from "../utils/riskColors";
import { PATIENT_DEFAULTS } from "../hooks/usePatientData";

const EVENT_ICONS = {
  ADMISSION:           "🏥",
  STATUS_CHANGE:       "📈",
  ALERT_FIRED:         "🚨",
  ALERT_ACKNOWLEDGED:  "✅",
  IDENTITY_COLLISION:  "🔄",
};

function Timeline({ timeline }) {
  const [selected, setSelected] = useState(null);

  // Group events by patient
  const byPatient = {};
  PATIENT_DEFAULTS.forEach(({ id }) => { byPatient[id] = []; });
  (timeline || []).forEach((evt) => {
    if (byPatient[evt.patient_id]) byPatient[evt.patient_id].push(evt);
  });

  return (
    <div className="panel timeline-panel">
      <div className="panel-header">
        <span className="panel-title">🗂 Patient Flow Timeline</span>
        <span className="panel-subtitle">Click any event node for details</span>
      </div>

      <div className="timeline-rows">
        {PATIENT_DEFAULTS.map((p) => {
          const events = byPatient[p.id] || [];
          return (
            <TimelineRow
              key={p.id}
              patient={p}
              events={events}
              onSelect={setSelected}
            />
          );
        })}
      </div>

      {/* Modal */}
      {selected && (
        <EventModal event={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

function TimelineRow({ patient, events, onSelect }) {
  return (
    <div className="timeline-row">
      <div className="timeline-patient-label">
        <div className="tl-patient-name">{patient.name.split(" ")[0]}</div>
        <div className="tl-patient-id">{patient.id}</div>
      </div>

      <div className="timeline-track">
        {/* Connecting line */}
        <div className="tl-line" />

        {/* Event nodes */}
        <div className="tl-nodes">
          {events.length === 0 ? (
            <div className="tl-empty">No events recorded</div>
          ) : (
            events.slice(-20).map((evt, i) => (
              <EventNode
                key={evt.id ?? i}
                event={evt}
                onClick={() => onSelect(evt)}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function EventNode({ event, onClick }) {
  const color = riskColor(event.risk_level);
  const icon  = EVENT_ICONS[event.event_type] || "⚡";

  return (
    <button
      className="tl-node"
      onClick={onClick}
      title={event.detail}
      style={{ borderColor: color, background: `${color}18` }}
    >
      <span className="tl-node-icon">{icon}</span>
      <span className="tl-node-time">
        {event.timestamp
          ? new Date(event.timestamp).toLocaleTimeString("en-US", {
              hour: "2-digit", minute: "2-digit", hour12: false,
            })
          : "—"}
      </span>
    </button>
  );
}

function EventModal({ event, onClose }) {
  const color = riskColor(event.risk_level);
  const icon  = EVENT_ICONS[event.event_type] || "⚡";

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>✕</button>

        <div className="modal-header">
          <span className="modal-icon">{icon}</span>
          <div>
            <div className="modal-type" style={{ color }}>
              {event.event_type?.replace(/_/g, " ")}
            </div>
            <div className="modal-patient">{event.patient_id}</div>
          </div>
          <div className="modal-risk-badge" style={{ background: `${color}22`, color, borderColor: `${color}55` }}>
            {event.risk_level}
          </div>
        </div>

        <div className="modal-detail">{event.detail}</div>

        <div className="modal-meta">
          <div className="modal-meta-row">
            <span>Time</span>
            <span>{event.timestamp ? new Date(event.timestamp).toLocaleString() : "—"}</span>
          </div>
          <div className="modal-meta-row">
            <span>Elapsed</span>
            <span>{timeElapsed(event.timestamp)}</span>
          </div>
          {event.id && (
            <div className="modal-meta-row">
              <span>Event ID</span>
              <span>#{event.id}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Timeline;
