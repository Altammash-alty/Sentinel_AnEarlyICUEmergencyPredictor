/**
 * SENTINEL — Telemetry Feed
 * Scrolling raw hex packet feed with collision highlighting and stats.
 */
import { useMemo } from "react";
import { COLORS } from "../utils/riskColors";

function TelemetryFeed({ telemetry }) {
  const stats = useMemo(() => {
    const total      = telemetry.length;
    const corrected  = telemetry.filter((t) => t.was_corrected).length;
    const recent10s  = telemetry.slice(0, 5); // approx rate from last 5 packets
    return { total, corrected, accuracy: total > 0 ? ((total - corrected) / total * 100).toFixed(1) : "100.0" };
  }, [telemetry]);

  return (
    <div className="panel telemetry-panel">
      <div className="panel-header">
        <span className="panel-title">📡 Telemetry Feed — Raw Hex Stream</span>
      </div>

      {/* Stats row */}
      <div className="telemetry-stats">
        <StatChip label="Packets Received" value={stats.total} />
        <StatChip label="Collisions Resolved" value={stats.corrected} accent={COLORS.warning} />
        <StatChip label="Resolution Accuracy" value={`${stats.accuracy}%`} accent={COLORS.stable} />
      </div>

      {/* Packet feed */}
      <div className="telemetry-list">
        {telemetry.length === 0 ? (
          <div className="empty-state">Waiting for telemetry packets…</div>
        ) : (
          telemetry.slice(0, 100).map((pkt, i) => (
            <TelemetryRow key={i} packet={pkt} />
          ))
        )}
      </div>
    </div>
  );
}

function TelemetryRow({ packet }) {
  const corrected = packet.was_corrected;
  const conf      = packet.confidence_score ?? 1;
  const confPct   = Math.round(conf * 100);
  const confColor = conf >= 0.8 ? COLORS.stable : conf >= 0.5 ? COLORS.warning : COLORS.critical;

  const ts = packet.timestamp
    ? new Date(packet.timestamp).toLocaleTimeString("en-US", { hour12: false })
    : "—";

  const hexPreview = packet.raw_hex ? packet.raw_hex.slice(0, 64) : "";
  const hexChunks = hexPreview.match(/.{1,2}/g) || [];

  return (
    <div className={`telemetry-row ${corrected ? "telemetry-corrected" : ""}`}>
      {/* Collision badge */}
      {corrected && (
        <span className="collision-badge">COLLISION RESOLVED</span>
      )}

      {/* Timestamp */}
      <span className="tel-timestamp">{ts}</span>

      {/* Hex string chunked */}
      <span className="tel-hex">
        {hexChunks.map((chunk, idx) => (
          <span key={idx} className={`hex-chunk ${idx % 8 === 0 ? "hex-highlight" : ""}`}>
            {chunk}
          </span>
        ))}
        {packet.raw_hex?.length > 64 && <span className="hex-chunk">...</span>}
      </span>

      {/* IDs */}
      <div className="tel-ids">
        <span className="tel-id-label">Claimed:</span>
        <span className={`tel-id ${corrected ? "tel-id-wrong" : "tel-id-ok"}`}>
          {packet.decoded_patient_id}
        </span>

        {corrected && (
          <>
            <span className="tel-arrow">→</span>
            <span className="tel-id-label">Resolved:</span>
            <span className="tel-id tel-id-ok">{packet.resolved_patient_id}</span>
          </>
        )}
      </div>

      {/* Confidence bar */}
      <div className="tel-conf-wrap">
        <div className="tel-conf-bar">
          <div
            className="tel-conf-fill"
            style={{ width: `${confPct}%`, background: confColor }}
          />
        </div>
        <span className="tel-conf-label" style={{ color: confColor }}>
          {confPct}%
        </span>
      </div>
    </div>
  );
}

function StatChip({ label, value, accent }) {
  return (
    <div className="stat-chip">
      <span className="stat-val" style={accent ? { color: accent } : {}}>{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}

export default TelemetryFeed;
