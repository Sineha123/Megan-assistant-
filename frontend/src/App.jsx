import React, { useState, useRef, useEffect, useCallback } from "react";
import MEGANChat from "./components/MEGANChat.jsx";
import SplashScreen from "./components/SplashScreen.jsx";
import "./App.css";


export default function App() {
  const [systemStatus, setSystemStatus] = useState(null);
  const [showSplash, setShowSplash]     = useState(true);

  // Poll system status once on mount
  useEffect(() => {
    fetch("/system/status")
      .then((r) => r.json())
      .then(setSystemStatus)
      .catch(() => setSystemStatus({ status: "offline" }));
  }, []);

  if (showSplash) {
    return <SplashScreen onComplete={() => setShowSplash(false)} />;
  }

  return (
    <div className="app-root">
      {/* Animated background grid */}
      <div className="bg-grid" aria-hidden="true" />
      <div className="bg-glow"  aria-hidden="true" />

      {/* Header */}
      <header className="app-header">
        <div className="logo">
          <span className="logo-icon">⬡</span>
          <span className="logo-text">MEGAN</span>
          <span className="logo-sub">HINGLISH AI ASSISTANT</span>
        </div>
        <div className="status-bar">
          {systemStatus ? (
            <>
              <StatusPill
                label="Dimag"
                value={systemStatus.brain}
                ok={systemStatus.brain === "online"}
              />
              <StatusPill
                label="Yaaddasht"
                value={systemStatus.memory}
                ok={systemStatus.memory === "active"}
              />
              <StatusPill
                label="Awaaz"
                value={systemStatus.agents?.voice}
                ok={systemStatus.agents?.voice === "ready"}
              />
            </>
          ) : (
            <span className="status-connecting">Connect ho rahi hun...</span>
          )}
        </div>
      </header>

      {/* Main chat */}
      <main className="app-main">
        <MEGANChat userId="user_001" />
      </main>
    </div>
  );
}


function StatusPill({ label, value, ok }) {
  return (
    <div className={`status-pill ${ok ? "ok" : "warn"}`}>
      <span className="pill-dot" />
      <span className="pill-label">{label}</span>
      <span className="pill-value">{value ?? "—"}</span>
    </div>
  );
}
