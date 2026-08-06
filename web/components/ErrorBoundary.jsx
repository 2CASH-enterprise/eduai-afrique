"use client";

import { Component } from "react";

const API_BASE_URL = "http://178.104.56.200:8000";

const C = {
  fond: "#FAF8F3", surface: "#FFFFFF", ligne: "#E7E2D6",
  encre: "#22304A", encreDoux: "#5B6472", accent: "#B08D57",
};

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { aPlante: false };
  }

  static getDerivedStateFromError() {
    return { aPlante: true };
  }

  componentDidCatch(erreur, infos) {
    // Remontée best-effort — un plantage qui vient de se produire ne doit
    // jamais provoquer une seconde erreur si cet envoi échoue à son tour.
    fetch(`${API_BASE_URL}/erreurs/plantage-navigateur`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: String(erreur?.message || erreur),
        stack: infos?.componentStack || erreur?.stack || null,
        url: typeof window !== "undefined" ? window.location.href : null,
        user_agent: typeof navigator !== "undefined" ? navigator.userAgent : null,
      }),
    }).catch(() => {});
  }

  render() {
    if (this.state.aPlante) {
      return (
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: "24px", backgroundColor: C.fond, fontFamily: "'IBM Plex Sans', sans-serif" }}>
          <div style={{ maxWidth: 380, textAlign: "center" }}>
            <p style={{ fontSize: 15, fontWeight: 600, color: C.encre, marginBottom: 8 }}>Une erreur est survenue</p>
            <p style={{ fontSize: 13, color: C.encreDoux, marginBottom: 20 }}>
              L'équipe OskarAI en a été informée automatiquement. Essaie de recharger la page.
            </p>
            <button
              onClick={() => window.location.reload()}
              style={{ backgroundColor: C.encre, color: C.surface, border: "none", borderRadius: 8, padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
            >
              Recharger
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
