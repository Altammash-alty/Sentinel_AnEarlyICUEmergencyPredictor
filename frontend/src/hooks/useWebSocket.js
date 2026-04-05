/**
 * SENTINEL — WebSocket Connection Manager
 *
 * Connects to all 4 WS endpoints on mount.
 * Auto-reconnects with exponential backoff.
 * Exposes: vitals, alerts, timeline, telemetry, connectionStatus
 */

import { useState, useEffect, useRef, useCallback } from "react";

const WS_BASE = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

const ENDPOINTS = {
  vitals:    `${WS_BASE}/ws/vitals`,
  alerts:    `${WS_BASE}/ws/alerts`,
  timeline:  `${WS_BASE}/ws/timeline`,
  telemetry: `${WS_BASE}/ws/telemetry`,
};

const INITIAL_BACKOFF  = 500;    // ms
const MAX_BACKOFF      = 30_000; // ms
const BACKOFF_FACTOR   = 2;
const PING_INTERVAL    = 20_000; // ms — keep-alive ping

function useWebSocket() {
  const [vitals,    setVitals]    = useState({});  // patient_id → latest VitalReading
  const [vitalHistory, setVitalHistory] = useState({}); // patient_id → last 60 readings
  const [alerts,    setAlerts]    = useState([]);
  const [timeline,  setTimeline]  = useState([]);
  const [telemetry, setTelemetry] = useState([]);
  const [connectionStatus, setConnectionStatus] = useState({
    vitals:    "CONNECTING",
    alerts:    "CONNECTING",
    timeline:  "CONNECTING",
    telemetry: "CONNECTING",
  });

  const sockets  = useRef({});
  const backoffs  = useRef({ vitals: INITIAL_BACKOFF, alerts: INITIAL_BACKOFF, timeline: INITIAL_BACKOFF, telemetry: INITIAL_BACKOFF });
  const retries   = useRef({ vitals: null, alerts: null, timeline: null, telemetry: null });
  const pings     = useRef({});
  const mounted   = useRef(true);

  // ── Message handlers ───────────────────────────────────────────────────────

  const handleVitalsMessage = useCallback((msg) => {
    if (msg.type === "snapshot") {
      const { vitals: snap, history } = msg.payload;
      const vitalsMap = {};
      (snap || []).forEach((v) => { vitalsMap[v.patient_id] = v; });
      setVitals(vitalsMap);
      if (history) setVitalHistory(history);
    } else if (msg.type === "vital") {
      const v = msg.payload;
      setVitals((prev) => ({ ...prev, [v.patient_id]: v }));
      setVitalHistory((prev) => {
        const existing = prev[v.patient_id] || [];
        const updated  = [...existing, v].slice(-60);
        return { ...prev, [v.patient_id]: updated };
      });
    }
  }, []);

  const handleAlertsMessage = useCallback((msg) => {
    if (msg.type === "snapshot") {
      setAlerts(msg.payload || []);
    } else if (msg.type === "alert") {
      setAlerts((prev) => [msg.payload, ...prev].slice(0, 200));
    }
  }, []);

  const handleTimelineMessage = useCallback((msg) => {
    if (msg.type === "snapshot") {
      setTimeline(msg.payload || []);
    } else if (msg.type === "timeline") {
      setTimeline((prev) => [...prev, msg.payload].slice(-500));
    }
  }, []);

  const handleTelemetryMessage = useCallback((msg) => {
    if (msg.type === "snapshot") {
      setTelemetry((msg.payload || []).reverse());
    } else if (msg.type === "telemetry") {
      setTelemetry((prev) => [msg.payload, ...prev].slice(0, 200));
    }
  }, []);

  const HANDLERS = {
    vitals:    handleVitalsMessage,
    alerts:    handleAlertsMessage,
    timeline:  handleTimelineMessage,
    telemetry: handleTelemetryMessage,
  };

  // ── Connect to one endpoint ────────────────────────────────────────────────

  const connect = useCallback((key) => {
    if (!mounted.current) return;
    if (retries.current[key]) {
      clearTimeout(retries.current[key]);
      retries.current[key] = null;
    }

    const url = ENDPOINTS[key];
    let ws;
    try {
      ws = new WebSocket(url);
    } catch (err) {
      scheduleReconnect(key);
      return;
    }

    sockets.current[key] = ws;
    setConnectionStatus((prev) => ({ ...prev, [key]: "CONNECTING" }));

    ws.onopen = () => {
      if (!mounted.current) return;
      backoffs.current[key] = INITIAL_BACKOFF;
      setConnectionStatus((prev) => ({ ...prev, [key]: "CONNECTED" }));

      // Start keep-alive pings
      pings.current[key] = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          try { ws.send("ping"); } catch (_) {}
        }
      }, PING_INTERVAL);
    };

    ws.onmessage = (event) => {
      if (!mounted.current) return;
      try {
        const msg = JSON.parse(event.data);
        HANDLERS[key]?.(msg);
      } catch (_) {}
    };

    ws.onerror = () => {
      setConnectionStatus((prev) => ({ ...prev, [key]: "ERROR" }));
    };

    ws.onclose = () => {
      if (!mounted.current) return;
      clearInterval(pings.current[key]);
      setConnectionStatus((prev) => ({ ...prev, [key]: "DISCONNECTED" }));
      scheduleReconnect(key);
    };
  }, []);   // eslint-disable-line react-hooks/exhaustive-deps

  const scheduleReconnect = (key) => {
    if (!mounted.current) return;
    const delay = backoffs.current[key];
    backoffs.current[key] = Math.min(delay * BACKOFF_FACTOR, MAX_BACKOFF);
    retries.current[key] = setTimeout(() => connect(key), delay);
  };

  // ── Mount / unmount ────────────────────────────────────────────────────────

  useEffect(() => {
    mounted.current = true;
    Object.keys(ENDPOINTS).forEach((key) => connect(key));

    return () => {
      mounted.current = false;
      Object.keys(ENDPOINTS).forEach((key) => {
        clearTimeout(retries.current[key]);
        clearInterval(pings.current[key]);
        const ws = sockets.current[key];
        if (ws) {
          ws.onclose = null;
          ws.close();
        }
      });
    };
  }, [connect]);

  // ── Derived overall connection status ─────────────────────────────────────
  const isConnected = Object.values(connectionStatus).every(
    (s) => s === "CONNECTED"
  );

  return {
    vitals,
    vitalHistory,
    alerts,
    timeline,
    telemetry,
    connectionStatus,
    isConnected,
  };
}

export default useWebSocket;
