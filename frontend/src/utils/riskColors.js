/**
 * SENTINEL — Risk Level Color Utilities
 *
 * Maps risk levels and vital values to the design-system colors.
 */

// ── Design tokens ──────────────────────────────────────────────────────────
export const COLORS = {
  stable:   "#10b981",
  warning:  "#f59e0b",
  critical: "#ef4444",
  muted:    "#334155",
  surface:  "#0e1420",
  border:   "#1e2a3a",
  text:     "#e2e8f0",
};

// Patient line colors for the risk chart
export const PATIENT_COLORS = {
  P001: "#0ea5e9",
  P002: "#f59e0b",
  P003: "#10b981",
  P004: "#8b5cf6",
  P005: "#ec4899",
};

// ── Risk level → color ─────────────────────────────────────────────────────
export function riskColor(level) {
  switch ((level || "").toUpperCase()) {
    case "CRITICAL": return COLORS.critical;
    case "WARNING":  return COLORS.warning;
    case "STABLE":
    default:         return COLORS.stable;
  }
}

// ── Risk score → color (continuous) ────────────────────────────────────────
export function scoreColor(score) {
  if (score >= 70) return COLORS.critical;
  if (score >= 40) return COLORS.warning;
  return COLORS.stable;
}

// ── Risk level → glow shadow ────────────────────────────────────────────────
export function riskGlow(level) {
  switch ((level || "").toUpperCase()) {
    case "CRITICAL": return `0 0 20px rgba(239, 68, 68, 0.08)`;
    case "WARNING":  return "none";
    case "STABLE":   return "none";
    default:         return "none";
  }
}

// ── Vital badge safety checks ───────────────────────────────────────────────
export function hrColor(hr) {
  if (hr == null) return COLORS.muted;
  if (hr < 50 || hr > 120)  return COLORS.critical;
  if (hr < 60 || hr > 100)  return COLORS.warning;
  return COLORS.text;
}

export function bpColor(bp) {
  if (bp == null) return COLORS.muted;
  if (bp < 80 || bp > 180)  return COLORS.critical;
  if (bp < 90 || bp > 140)  return COLORS.warning;
  return COLORS.text;
}

export function spo2Color(spo2) {
  if (spo2 == null) return COLORS.muted;
  if (spo2 < 90)   return COLORS.critical;
  if (spo2 < 94)   return COLORS.warning;
  return COLORS.text;
}

export function rrColor(rr) {
  if (rr == null) return COLORS.muted;
  if (rr < 8 || rr > 30)  return COLORS.critical;
  if (rr < 12 || rr > 25) return COLORS.warning;
  return COLORS.text;
}

export function tempColor(temp) {
  if (temp == null) return COLORS.muted;
  if (temp < 35 || temp > 39.5) return COLORS.critical;
  if (temp < 36 || temp > 38.5) return COLORS.warning;
  return COLORS.text;
}

// ── Severity → color  ───────────────────────────────────────────────────────
export function severityColor(severity) {
  switch ((severity || "").toUpperCase()) {
    case "CRITICAL": return COLORS.critical;
    case "HIGH":     return COLORS.warning;
    case "MEDIUM":
    default:         return "#60a5fa";   // blue for medium
  }
}

// ── Time elapsed string ─────────────────────────────────────────────────────
export function timeElapsed(isoString) {
  if (!isoString) return "—";
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (diff < 60)   return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ${diff % 60}s ago`;
  return `${Math.floor(diff / 3600)}h ${Math.floor((diff % 3600) / 60)}m ago`;
}

// ── Vital label formatting ──────────────────────────────────────────────────
export function formatVital(key, value) {
  if (value == null) return "—";
  switch (key) {
    case "hr":   return `${Math.round(value)} bpm`;
    case "bp":   return `${Math.round(value)} mmHg`;
    case "spo2": return `${value.toFixed(1)}%`;
    case "rr":   return `${Math.round(value)} br/m`;
    case "temp": return `${value.toFixed(1)}°C`;
    default:     return String(value);
  }
}
