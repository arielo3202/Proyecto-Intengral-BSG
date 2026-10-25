import React, { useState } from "react";
import { sendChatTurn } from "../services/apiClient";
import { AuthSession, TechnicalTelemetry } from "../types/api";

interface ChatTerminalProps {
  session: AuthSession;
}

interface TurnEntry {
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
  /** Exclusivo para Rol Admin */
  telemetry?: TechnicalTelemetry;
}

export const ChatTerminal: React.FC<ChatTerminalProps> = ({ session }) => {
  const [sessionId, setSessionId] = useState<string>("sess-techcorp-001");
  const [prompt, setPrompt] = useState<string>("");
  const [preferredTier, setPreferredTier] = useState<"light" | "pro">("light");
  const [remainingQuota, setRemainingQuota] = useState<number>(10);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [turns, setTurns] = useState<TurnEntry[]>([
    {
      sender: "assistant",
      text: "Bienvenido al Asistente Empresarial Inteligente de TechCorp LATAM. Puedes consultar políticas de trabajo remoto, vacaciones, reembolsos, soporte técnico VPN o solicitar un análisis cuantitativo de acciones (ej. MELI, GLOB, AAPL, MSFT).",
      timestamp: new Date().toISOString()
    }
  ]);

  const handleSend = async (customPrompt?: string) => {
    const textToSend = (customPrompt ?? prompt).trim();
    if (!textToSend || loading) return;

    setErrorMsg(null);
    setPrompt("");
    setTurns((prev) => [
      ...prev,
      { sender: "user", text: textToSend, timestamp: new Date().toISOString() }
    ]);
    setLoading(true);

    try {
      const response = await sendChatTurn(
        session.access_token,
        sessionId,
        textToSend,
        preferredTier
      );
      setRemainingQuota(response.remaining_requests_minute);
      setTurns((prev) => [
        ...prev,
        {
          sender: "assistant",
          text: response.reply,
          timestamp: response.timestamp,
          // Si es rol usuario, response.technical_telemetry es undefined desde el backend
          telemetry:
            session.role === "admin" ? response.technical_telemetry : undefined
        }
      ]);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Error de comunicación");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="pixel-window" aria-labelledby="chat-terminal-title">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
          marginBottom: "14px"
        }}
      >
        <h2 id="chat-terminal-title" className="pixel-title" style={{ margin: 0 }}>
          TERMINAL CONVERSACIONAL MULTI-TURNO (SESSION MEMORY ADK)
        </h2>

        <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
          <label htmlFor="session-id-input" style={{ fontSize: "13px" }}>
            ID Sesión ADK:
          </label>
          <input
            id="session-id-input"
            className="pixel-input"
            style={{ width: "190px", padding: "6px 10px" }}
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
            aria-label="Identificador de sesión multi-turno"
          />

          <span className="pixel-badge badge-closed" aria-live="polite">
            CUOTA: {remainingQuota}/10 REQ/MIN
          </span>
        </div>
      </div>

      {/* Botones de consulta rápida para probar las 3 @tool del Root Agent ADK */}
      <div
        style={{
          display: "flex",
          gap: "8px",
          flexWrap: "wrap",
          marginBottom: "16px"
        }}
        role="group"
        aria-label="Consultas rápidas de demostración"
      >
        <button
          type="button"
          className="pixel-btn pixel-btn-cyan"
          onClick={() =>
            handleSend("¿Cuál es la política de trabajo híbrido/remoto y el bono de internet?")
          }
        >
          @TOOL POLÍTICAS RRHH
        </button>
        <button
          type="button"
          className="pixel-btn pixel-btn-emerald"
          onClick={() =>
            handleSend(
              "Necesito abrir un ticket urgente por bloqueo de mi token MFA en la VPN corporativa"
            )
          }
        >
          @TOOL CREAR TICKET TI
        </button>
        <button
          type="button"
          className="pixel-btn"
          onClick={() =>
            handleSend(
              "Comparar acciones de MELI, GLOB y MSFT con SMA, RSI, Volatilidad y Sharpe Ratio"
            )
          }
        >
          @TOOL ANÁLISIS CUANTITATIVO ACCIONES
        </button>
      </div>

      {/* Historial de mensajes */}
      <div
        role="log"
        aria-live="polite"
        aria-label="Historial de conversación con el asistente"
        style={{
          maxHeight: "460px",
          overflowY: "auto",
          padding: "12px",
          backgroundColor: "var(--px-bg-input)",
          border: "3px solid var(--px-border-light)",
          marginBottom: "16px"
        }}
      >
        {turns.map((turn, idx) => (
          <article
            key={idx}
            className={`pixel-card ${
              turn.sender === "user" ? "pixel-card-amber" : "pixel-card-emerald"
            }`}
            style={{ marginBottom: "14px" }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: "6px",
                fontSize: "12px",
                color: "var(--px-text-muted)"
              }}
            >
              <strong>
                {turn.sender === "user"
                  ? `👤 ${session.full_name}`
                  : "🤖 ROOT AGENT (TechCorp ADK)"}
              </strong>
              <span>{new Date(turn.timestamp).toLocaleTimeString()}</span>
            </div>

            <div style={{ whiteSpace: "pre-wrap" }}>{turn.text}</div>

            {/* BLOQUE EXCLUSIVO PARA ROL ADMINISTRADOR: Trazas ReAct, Tokens, Latencia y Hash SHA-256 */}
            {session.role === "admin" && turn.telemetry && (
              <details
                style={{
                  marginTop: "12px",
                  paddingTop: "10px",
                  borderTop: "2px dashed var(--px-cyan)",
                  fontSize: "12.5px"
                }}
              >
                <summary
                  style={{
                    cursor: "pointer",
                    color: "var(--px-amber)",
                    fontWeight: 700
                  }}
                >
                  [SOLO ADMIN] TELEMETRÍA ADK ReAct | Modelo: {turn.telemetry.llm_model} (
                  {turn.telemetry.llm_provider}) | Tokens: {turn.telemetry.total_tokens} |
                  Latencia: {turn.telemetry.latency_ms}ms | Costo: $
                  {turn.telemetry.estimated_cost_usd.toFixed(6)} USD
                </summary>
                <div style={{ marginTop: "8px" }}>
                  <div>
                    <strong>Estado Circuit Breaker:</strong>{" "}
                    {turn.telemetry.circuit_breaker_state} |{" "}
                    <strong>Fallback Activado:</strong>{" "}
                    {turn.telemetry.fallback_triggered ? "SÍ (Ollama llama3.2:3b)" : "NO"}
                  </div>
                  <div>
                    <strong>Hash Auditoría SHA-256:</strong>{" "}
                    <code>{turn.telemetry.audit_record_hash}</code>
                  </div>
                  <div style={{ marginTop: "6px" }}>
                    <strong>Trazabilidad del Ciclo ReAct (Reason → Act → Observe):</strong>
                    <ul>
                      {turn.telemetry.react_steps.map((s, sIdx) => (
                        <li key={sIdx}>
                          <strong>[{s.phase}]</strong>{" "}
                          {s.thought || s.invoked_tool || s.observation_summary}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </details>
            )}
          </article>
        ))}
      </div>

      {errorMsg && (
        <div
          role="alert"
          className="pixel-card pixel-card-coral"
          style={{ marginBottom: "14px" }}
        >
          {errorMsg}
        </div>
      )}

      {/* Formulario de envío */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}
      >
        {session.role === "admin" && (
          <select
            aria-label="Seleccionar tier de modelo Vertex AI"
            className="pixel-select"
            style={{ width: "210px" }}
            value={preferredTier}
            onChange={(e) => setPreferredTier(e.target.value as "light" | "pro")}
          >
            <option value="light">Tier: Gemini 2.5 Light</option>
            <option value="pro">Tier: Gemini 2.5 Pro</option>
          </select>
        )}

        <input
          type="text"
          className="pixel-input"
          style={{ flex: 1, minWidth: "240px" }}
          placeholder="Escribe tu consulta sobre políticas, soporte TI o acciones bursátiles..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          aria-label="Mensaje para el asistente"
        />

        <button type="submit" className="pixel-btn" disabled={loading}>
          {loading ? "PROCESANDO ReAct..." : "ENVIAR [ENTER]"}
        </button>
      </form>
    </section>
  );
};
