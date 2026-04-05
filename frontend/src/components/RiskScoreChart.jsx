/**
 * SENTINEL — Risk Score Chart
 * Multi-line Recharts area chart showing rolling 60-point risk history.
 */
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ReferenceLine, ReferenceArea, ResponsiveContainer,
} from "recharts";
import { PATIENT_COLORS, COLORS, riskColor } from "../utils/riskColors";
import { PATIENT_DEFAULTS } from "../hooks/usePatientData";

const PATIENT_NAMES = Object.fromEntries(
  PATIENT_DEFAULTS.map((p) => [p.id, p.name.split(" ")[0]])
);

function RiskScoreChart({ chartData }) {
  return (
    <div className="panel chart-panel">
      <div className="panel-header">
        <span className="panel-title">📈 SENTINEL Risk Trajectory — Live</span>
        <span className="panel-subtitle">Last 60 readings · 2s interval</span>
      </div>

      <ResponsiveContainer width="100%" height="100%" minHeight={260}>
        <AreaChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="4 4" stroke="#1e2a3a" vertical={false} />

          {/* Zone boundary lines */}
          <ReferenceLine y={40} stroke={COLORS.warning} strokeDasharray="6 3" strokeOpacity={0.4} label={{ value: "WARNING", fill: COLORS.warning, fontSize: 9, position: "right" }} />
          <ReferenceLine y={70} stroke={COLORS.critical} strokeDasharray="6 3" strokeOpacity={0.4} label={{ value: "CRITICAL", fill: COLORS.critical, fontSize: 9, position: "right" }} />

          <XAxis
            dataKey="time"
            tick={{ fill: COLORS.muted, fontSize: 9, fontFamily: "JetBrains Mono" }}
            tickLine={false}
            axisLine={{ stroke: "#1a2e52" }}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "JetBrains Mono" }}
            tickLine={false}
            axisLine={false}
            width={30}
          />

          <Tooltip content={<CustomTooltip />} />

          <Legend
            formatter={(value) => (
              <span style={{ color: COLORS.text, fontSize: 11, fontFamily: "Inter" }}>
                {PATIENT_NAMES[value] || value}
              </span>
            )}
          />

          {PATIENT_DEFAULTS.map(({ id }) => (
            <Area
              key={id}
              type="monotone"
              dataKey={id}
              name={id}
              stroke={PATIENT_COLORS[id]}
              strokeWidth={2}
              fill="transparent"
              dot={false}
              activeDot={{ r: 4, strokeWidth: 0, fill: PATIENT_COLORS[id] }}
              isAnimationActive={false}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip" style={{ background: '#141b2d', border: '1px solid #1e2a3a', borderRadius: '8px', boxShadow: 'none' }}>
      <div className="tooltip-time">{label}</div>
      {payload.map((entry) => {
        const pid  = entry.dataKey;
        const name = PATIENT_NAMES[pid] || pid;
        const score = entry.value;
        const color = score >= 70
          ? COLORS.critical
          : score >= 40
          ? COLORS.warning
          : COLORS.stable;
        return (
          <div key={pid} className="tooltip-row">
            <span style={{ color: PATIENT_COLORS[pid] }}>{name}</span>
            <span style={{ color }} className="tooltip-score">
              {score?.toFixed(1) ?? "—"}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default RiskScoreChart;
