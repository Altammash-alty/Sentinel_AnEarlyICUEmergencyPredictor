/**
 * SENTINEL — Status Bar
 * Fixed top bar with system health metrics, connection status, and controls.
 */
import { useState, useEffect } from "react";
import { riskColor, COLORS } from "../utils/riskColors";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function StatusBar({ isConnected, connectionStatus, unackedCount, onThemeToggle, isDark }) {
  const [stats, setStats] = useState(null);
  const [uptime, setUptime] = useState(0);

  useEffect(() => {
    let isMounted = true;
    const fetchStats = async () => {
      try {
        const res = await fetch(`${API_BASE}/system/stats`);
        if (res.ok && isMounted) {
          const data = await res.json();
          setStats(data);
          setUptime(data.uptime_seconds || 0);
        }
      } catch (_) {}
    };
    fetchStats();
    const interval = setInterval(fetchStats, 3000);
    return () => { isMounted = false; clearInterval(interval); };
  }, []);

  useEffect(() => {
    const timer = setInterval(() => setUptime((u) => u + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  const formatUptime = (s) => {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = Math.floor(s % 60);
    return `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}:${String(sec).padStart(2,"0")}`;
  };

  const dot = isConnected ? COLORS.stable : COLORS.critical;

  const handleExportCSV = () => {
    window.open(`${API_BASE}/alerts/export/csv`, "_blank");
  };

  return (
    <div className="status-bar">
      {/* Left — Logo + status */}
      <div className="status-left">
        <div className="sentinel-logo">
          <span className="logo-icon">⚕</span>
          <span className="logo-text">SENTINEL</span>
          <span className="logo-version">v1.0</span>
        </div>
        <div className={`status-dot-wrap ${isConnected ? 'pulse' : ''}`} style={{
          background: isConnected ? 'rgba(16,185,129,0.10)' : 'rgba(239,68,68,0.10)',
          color: isConnected ? '#10b981' : '#ef4444',
          border: isConnected ? '1px solid rgba(16,185,129,0.25)' : '1px solid rgba(239,68,68,0.25)',
          padding: '4px 10px',
          borderRadius: '12px',
          fontSize: '11px',
          fontWeight: '700',
          letterSpacing: '0.05em'
        }}>
          <span className="status-dot" style={{ background: dot }} />
          <span>{isConnected ? "LIVE" : "OFFLINE"}</span>
        </div>
      </div>

      {/* Center — Metrics */}
      <div className="status-metrics">
        <Metric icon="📡" label="Packets/sec" value={stats?.packets_per_sec?.toFixed(1) ?? "—"} />
        <Metric icon="🔄" label="Collisions" value={stats?.collisions_total ?? "—"} accent={COLORS.warning} />
        <Metric
          icon="🚨"
          label="Active Alerts"
          value={unackedCount}
          accent={unackedCount > 0 ? COLORS.critical : COLORS.stable}
        />
        <Metric icon="⏱" label="Uptime" value={formatUptime(uptime)} />
        <Metric
          icon="🧠"
          label="LSTM"
          value={stats?.model_loaded ? "ONLINE" : "NEWS2"}
          accent={stats?.model_loaded ? COLORS.stable : COLORS.warning}
        />
      </div>

      {/* Right — Controls */}
      <div className="status-right" style={{ gap: '12px' }}>
        <button 
          className="status-btn" 
          style={{ background: 'rgba(239,68,68,0.10)', border: '1px solid rgba(239,68,68,0.30)', color: '#ef4444', transition: 'background 0.2s', ...({':hover': {background: 'rgba(239,68,68,0.20)'}}) }}
          onClick={async () => {
            try { await fetch(`${API_BASE}/system/trigger/deterioration`, { method: "POST" }); } catch (e) {}
          }}
          title="Force Deterioration Event"
        >
          ⚕ Trigger Crisis
        </button>
        <button 
          className="status-btn"
          style={{ background: 'rgba(245,158,11,0.10)', border: '1px solid rgba(245,158,11,0.30)', color: '#f59e0b' }}
          onClick={async () => {
            try { await fetch(`${API_BASE}/system/trigger/collision`, { method: "POST" }); } catch (e) {}
          }}
          title="Force Identity Collision"
        >
          🔄 Force Collision
        </button>
        <button className="status-btn export-btn" style={{ background: 'rgba(14,165,233,0.10)', border: '1px solid rgba(14,165,233,0.30)', color: '#0ea5e9' }} onClick={handleExportCSV}>
          ⬇ Export CSV
        </button>
      </div>
    </div>
  );
}

function Metric({ icon, label, value, accent }) {
  return (
    <div className="status-metric" style={{ background: '#141b2d', border: '1px solid #1e2a3a' }}>
      <span className="metric-icon">{icon}</span>
      <div className="metric-body">
        <span className="metric-label" style={{ color: '#334155' }}>{label}</span>
        <span className="metric-value" style={{ color: accent || '#e2e8f0' }}>
          {value}
        </span>
      </div>
    </div>
  );
}

export default StatusBar;
