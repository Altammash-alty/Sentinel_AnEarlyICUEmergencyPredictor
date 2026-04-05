/**
 * SENTINEL — Root Application
 * Assembles all panels in the specified layout and wires WS data.
 */
import { useState } from "react";
import StatusBar      from "./components/StatusBar";
import PatientGrid    from "./components/PatientGrid";
import RiskScoreChart from "./components/RiskScoreChart";
import AlertFeed      from "./components/AlertFeed";
import Timeline       from "./components/Timeline";
import TelemetryFeed  from "./components/TelemetryFeed";
import useWebSocket   from "./hooks/useWebSocket";
import usePatientData from "./hooks/usePatientData";

function App() {
  const [isDark, setIsDark] = useState(true);

  const {
    vitals, vitalHistory, alerts, timeline, telemetry,
    isConnected, connectionStatus,
  } = useWebSocket();

  const {
    patients, chartData, activeAlerts, unackedCount,
  } = usePatientData({ vitals, vitalHistory, alerts });

  return (
    <div className={`app-root ${isDark ? "theme-dark" : "theme-light"}`}>
      {/* ── STATUS BAR ─────────────────────────────────────────────────── */}
      <StatusBar
        isConnected={isConnected}
        connectionStatus={connectionStatus}
        unackedCount={unackedCount}
        onThemeToggle={() => setIsDark(!isDark)}
        isDark={isDark}
      />

      <main className="app-main">
        {/* ── PATIENT GRID ───────────────────────────────────────────────── */}
        <section className="section-full">
          <PatientGrid patients={patients} />
        </section>

        {/* ── CHART + ALERTS (split row) ─────────────────────────────────── */}
        <section className="section-split">
          <div className="split-left">
            <RiskScoreChart chartData={chartData} />
          </div>
          <div className="split-right">
            <AlertFeed alerts={activeAlerts} unackedCount={unackedCount} />
          </div>
        </section>

        {/* ── TIMELINE ──────────────────────────────────────────────────── */}
        <section className="section-full">
          <Timeline timeline={timeline} />
        </section>

        {/* ── TELEMETRY FEED ────────────────────────────────────────────── */}
        <section className="section-full">
          <TelemetryFeed telemetry={telemetry} />
        </section>
      </main>
    </div>
  );
}

export default App;
