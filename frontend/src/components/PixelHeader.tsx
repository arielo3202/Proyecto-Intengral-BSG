import React from "react";
import { AuthSession } from "../types/api";

interface PixelHeaderProps {
  session: AuthSession | null;
  activeTab: "chat" | "admin";
  onSelectTab: (tab: "chat" | "admin") => void;
  onLogout: () => void;
}

export const PixelHeader: React.FC<PixelHeaderProps> = ({
  session,
  activeTab,
  onSelectTab,
  onLogout
}) => {
  return (
    <header
      className="pixel-window"
      role="banner"
      style={{
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "space-between",
        alignItems: "center",
        gap: "14px"
      }}
    >
      <div>
        <h1 className="pixel-title" style={{ fontSize: "16px", marginBottom: "6px" }}>
          [TECHCORP LATAM] ASISTENTE EMPRESARIAL INTELIGENTE
        </h1>
        <p className="pixel-subtitle" style={{ margin: 0 }}>
          Modalidad 2.2: Google ADK (ReAct) + Vertex AI / Ollama Fallback + Cloud Run
        </p>
      </div>

      {session && (
        <nav
          aria-label="Navegación principal del sistema"
          style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}
        >
          <span
            className={`pixel-badge ${
              session.role === "admin" ? "badge-half" : "badge-closed"
            }`}
            aria-label={`Rol activo: ${session.role}`}
          >
            ROL: {session.role.toUpperCase()} ({session.email})
          </span>

          <button
            type="button"
            className={`pixel-btn ${activeTab === "chat" ? "pixel-btn-cyan" : ""}`}
            onClick={() => onSelectTab("chat")}
            aria-current={activeTab === "chat" ? "page" : undefined}
          >
            CHAT ASISTENTE
          </button>

          {/* El botón del Dashboard de Costos y Auditoría SOLO existe para el Rol Admin */}
          {session.role === "admin" && (
            <button
              type="button"
              className={`pixel-btn ${activeTab === "admin" ? "pixel-btn-emerald" : ""}`}
              onClick={() => onSelectTab("admin")}
              aria-current={activeTab === "admin" ? "page" : undefined}
            >
              DASHBOARD COSTOS E6 & AUDITORÍA
            </button>
          )}

          <button
            type="button"
            className="pixel-btn pixel-btn-coral"
            onClick={onLogout}
            aria-label="Cerrar sesión segura"
          >
            SALIR
          </button>
        </nav>
      )}
    </header>
  );
};
