import React, { useState, useEffect } from "react";
import "./SplashScreen.css";

const BOOT_LINES = [
  "Initializing neural core...",
  "Loading Gemini 1.5 Flash...",
  "Voice module: Swara Neural aktiv...",
  "Memory systems connected...",
  "Sab agents ready...",
  "MEGAN Online.",
];

const LETTERS = ["M", "E", "G", "A", "N"];

export default function SplashScreen({ onComplete }) {
  const [phase, setPhase]           = useState("logo");      // logo | letters | boot | exit
  const [visibleLetters, setVisible] = useState([]);
  const [bootLines, setBootLines]    = useState([]);
  const [exitAnim, setExitAnim]      = useState(false);

  /* ── Phase 1: Logo glow (0-800ms) → letters animate in ── */
  useEffect(() => {
    const t1 = setTimeout(() => setPhase("letters"), 800);
    return () => clearTimeout(t1);
  }, []);

  /* ── Phase 2: Letters animate in via CSS, then boot lines ── */
  useEffect(() => {
    if (phase !== "letters") return;
    const t = setTimeout(() => setPhase("boot"), 1000);
    return () => clearTimeout(t);
  }, [phase]);

  /* ── Phase 3: Boot lines appear ── */

  useEffect(() => {
    if (phase !== "boot") return;
    let i = 0;
    const interval = setInterval(() => {
      setBootLines((prev) => [...prev, BOOT_LINES[i]]);
      i++;
      if (i >= BOOT_LINES.length) {
        clearInterval(interval);
        setTimeout(() => {
          setExitAnim(true);
          setTimeout(onComplete, 900);
        }, 700);
      }
    }, 260);
    return () => clearInterval(interval);
  }, [phase, onComplete]);

  return (
    <div className={`splash-root ${exitAnim ? "splash-exit" : ""}`}>

      {/* ── Deep space bg + radial glow ── */}
      <div className="splash-bg" />
      <div className="splash-glow-center" />
      <div className="splash-scanlines" />

      {/* ── Orbit rings ── */}
      <div className="orbit orbit-1" />
      <div className="orbit orbit-2" />
      <div className="orbit orbit-3" />

      {/* ── Floating hex particles ── */}
      {[...Array(10)].map((_, i) => (
        <div key={i} className={`hex-particle hex-p${i + 1}`} />
      ))}

      {/* ── Centre card ── */}
      <div className="splash-card">

        {/* Glass highlight strip */}
        <div className="card-gloss" />

        {/* Logo */}
        <div className="logo-ring">
          <div className="ring-pulse" />
          <img
            src="/megan-logo.png"
            alt="MEGAN Logo"
            className="splash-logo"
            draggable={false}
          />
        </div>

        {/* M E G A N animated letters */}
        <div className="megan-letters" aria-label="MEGAN">
          {LETTERS.map((letter, i) => (
            <span
              key={i}
              className={`letter letter-${i} ${phase !== "logo" ? "letter-in" : ""}`}
            >
              {letter}
            </span>
          ))}
        </div>

        {/* Tagline */}
        <p className={`splash-tagline ${phase !== "logo" ? "tagline-in" : ""}`}>
          Aapki Personal AI Assistant &nbsp;·&nbsp; Hinglish Mode
        </p>

        {/* Divider */}
        <div className={`splash-divider ${phase === "boot" || exitAnim ? "divider-in" : ""}`} />

        {/* Boot lines */}
        <div className="boot-console">
          {bootLines.map((line, i) => (
            <div key={i} className="boot-line">
              <span className="boot-prompt">›</span>
              <span className="boot-text">{line}</span>
            </div>
          ))}
          {phase === "boot" && bootLines.length < BOOT_LINES.length && (
            <div className="boot-cursor" />
          )}
        </div>

      </div>

      {/* Version badge */}
      <div className="splash-version">v1.1 &nbsp;·&nbsp; Gemini 1.5 Flash</div>
    </div>
  );
}
