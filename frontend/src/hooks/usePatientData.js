/**
 * SENTINEL — Patient Data State Manager
 *
 * Consumes raw WS streams and exposes clean, structured state:
 *   - patients:       array of patient objects with current vitals
 *   - riskHistory:    patient_id → last 60 {time, score} points
 *   - activeAlerts:   unacknowledged alerts sorted newest-first
 *   - unackedCount:   number of unacknowledged alerts
 */

import { useMemo } from "react";

const PATIENT_DEFAULTS = [
  { id: "P001", name: "James Thornton", age: 67, ward: "ICU-A" },
  { id: "P002", name: "Margaret Chen",  age: 74, ward: "ICU-A" },
  { id: "P003", name: "David Okafor",   age: 55, ward: "ICU-B" },
  { id: "P004", name: "Sofia Reyes",    age: 48, ward: "ICU-B" },
  { id: "P005", name: "Robert Kim",     age: 61, ward: "ICU-C" },
];

function usePatientData({ vitals, vitalHistory, alerts }) {
  // ── Patients list with current vitals merged in ──────────────────────────
  const patients = useMemo(() => {
    return PATIENT_DEFAULTS.map((p) => ({
      ...p,
      currentVitals: vitals[p.id] || null,
    }));
  }, [vitals]);

  // ── Risk score history per patient (for the chart) ───────────────────────
  const riskHistory = useMemo(() => {
    const result = {};
    PATIENT_DEFAULTS.forEach(({ id }) => {
      const readings = vitalHistory[id] || [];
      result[id] = readings.map((r, idx) => ({
        index:      idx,
        time:       r.timestamp
          ? new Date(r.timestamp).toLocaleTimeString("en-US", {
              hour:   "2-digit",
              minute: "2-digit",
              second: "2-digit",
              hour12: false,
            })
          : `T-${readings.length - idx}`,
        score:      r.risk_score ?? 0,
        risk_level: r.risk_level ?? "STABLE",
        hr:         r.hr,
        bp:         r.bp,
        spo2:       r.spo2,
        rr:         r.rr,
        temp:       r.temp,
      }));
    });
    return result;
  }, [vitalHistory]);

  // ── Normalise history into a chart-ready combined series ─────────────────
  const chartData = useMemo(() => {
    // Find the max length across all patients
    const maxLen = Math.max(
      ...PATIENT_DEFAULTS.map(({ id }) => (riskHistory[id] || []).length),
      0
    );

    const rows = [];
    for (let i = 0; i < maxLen; i++) {
      const row = { index: i };
      PATIENT_DEFAULTS.forEach(({ id, name }) => {
        const hist = riskHistory[id] || [];
        const offset = hist.length - maxLen + i;
        if (offset >= 0 && offset < hist.length) {
          row[id]        = hist[offset].score;
          row[`${id}_level`] = hist[offset].risk_level;
          row[`${id}_label`] = name.split(" ")[0];
          row.time       = hist[offset].time;
        }
      });
      rows.push(row);
    }
    return rows;
  }, [riskHistory]);

  // ── Alerts ────────────────────────────────────────────────────────────────
  const activeAlerts = useMemo(() => {
    return [...alerts].sort(
      (a, b) =>
        new Date(b.triggered_at).getTime() - new Date(a.triggered_at).getTime()
    );
  }, [alerts]);

  const unackedCount = useMemo(
    () => activeAlerts.filter((a) => !a.acknowledged).length,
    [activeAlerts]
  );

  // ── Per-patient current risk level ────────────────────────────────────────
  const patientRiskLevels = useMemo(() => {
    const result = {};
    PATIENT_DEFAULTS.forEach(({ id }) => {
      const v = vitals[id];
      result[id] = v?.risk_level ?? "STABLE";
    });
    return result;
  }, [vitals]);

  return {
    patients,
    riskHistory,
    chartData,
    activeAlerts,
    unackedCount,
    patientRiskLevels,
    patientDefaults: PATIENT_DEFAULTS,
  };
}

export default usePatientData;
export { PATIENT_DEFAULTS };
