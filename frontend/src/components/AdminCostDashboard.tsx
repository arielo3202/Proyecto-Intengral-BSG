import React, { useEffect, useState } from "react";
import {
  downloadAuditReport,
  fetchAdminDashboard,
  toggleCircuitBreakerState
} from "../services/apiClient";
import { AdminDashboardData, AuthSession } from "../types/api";

interface AdminCostDashboardProps {
  session: AuthSession;
}

export const AdminCostDashboard: React.FC<AdminCostDashboardProps> = ({
  session
}) => {
  const [data, setData] = useState<AdminDashboardData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [simulatedEmployees, setSimulatedEmployees] = useState<number>(800);

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const d = await fetchAdminDashboard(session.access_token);
      setData(d);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error cargando dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const handleCircuitBreakerChange = async (
    target: "CLOSED" | "OPEN" | "HALF_OPEN"
  ) => {
    await toggleCircuitBreakerState(session.access_token, target);
    await loadDashboard();
  };

  if (loading && !data) {
    return (
      <div className="pixel-window" role="status" aria-live="polite">
        <h2 className="pixel-title">CARGANDO TELEMETRÍA Y MODELO DE COSTOS...</h2>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="pixel-window pixel-card-coral" role="alert">
        <h2 className="pixel-title">ERROR DE ACCESO ADMINISTRATIVO</h2>
        <p>{error}</p>
      </div>
    );
  }

  const e6 = data.cost_analysis_e6;
  const breakdown = e6.monthly_projection_800_employees.cost_breakdown_usd;
  const scaleFactor = simulatedEmployees / 800.0;
  const maxModalityCost = Math.max(
    ...e6.modalities_comparison.map((m) => m.total_usd)
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* BARRA SUPERIOR DE EXPORTACIÓN PDF / CSV Y CONTROL DEL CIRCUIT BREAKER */}
      <section className="pixel-window" aria-labelledby="admin-controls-heading">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "12px"
          }}
        >
          <div>
            <h2 id="admin-controls-heading" className="pixel-title" style={{ margin: 0 }}>
              PANEL DE CONTROL FINOPS, CIRCUIT BREAKER Y AUDITORÍA INMUTABLE
            </h2>
            <p style={{ margin: "6px 0 0 0", color: "var(--px-text-muted)" }}>
              Exclusivo para Rol Administrador — Incluye Entregable E6 integrado en vivo y
              descarga certificada PDF/CSV.
            </p>
          </div>

          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            <button
              type="button"
              className="pixel-btn pixel-btn-emerald"
              onClick={() => downloadAuditReport(session.access_token, "pdf")}
            >
              ⬇ EXPORTAR REPORTE PDF (E6 + AUDITORÍA)
            </button>
            <button
              type="button"
              className="pixel-btn pixel-btn-cyan"
              onClick={() => downloadAuditReport(session.access_token, "csv")}
            >
              ⬇ EXPORTAR AUDITORÍA CSV
            </button>
            <button type="button" className="pixel-btn" onClick={loadDashboard}>
              ↻ REFRESCAR MÉTRICAS
            </button>
          </div>
        </div>
      </section>

      {/* TARJETAS KPI EN TIEMPO REAL Y ESTADO DEL CIRCUIT BREAKER */}
      <section
        className="pixel-window"
        aria-labelledby="realtime-kpi-heading"
      >
        <h2 id="realtime-kpi-heading" className="pixel-title">
          1. SALUD DEL SISTEMA, CIRCUIT BREAKER Y USO EN TIEMPO REAL
        </h2>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))",
            gap: "14px",
            marginBottom: "18px"
          }}
        >
          <div className="pixel-card">
            <div style={{ fontSize: "12px", color: "var(--px-text-muted)" }}>
              ESTADO CIRCUIT BREAKER LLM
            </div>
            <div style={{ margin: "8px 0" }}>
              <span
                className={`pixel-badge ${
                  data.circuit_breaker.state === "CLOSED"
                    ? "badge-closed"
                    : data.circuit_breaker.state === "OPEN"
                    ? "badge-open"
                    : "badge-half"
                }`}
              >
                {data.circuit_breaker.state}
              </span>
            </div>
            <div style={{ fontSize: "12px" }}>
              Fallos consecutivos: {data.circuit_breaker.failure_count} /{" "}
              {data.circuit_breaker.failure_threshold}
            </div>
          </div>

          <div className="pixel-card pixel-card-amber">
            <div style={{ fontSize: "12px", color: "var(--px-text-muted)" }}>
              TOKENS PROCESADOS (SESIÓN ACTUAL)
            </div>
            <div className="pixel-subtitle" style={{ fontSize: "28px", margin: "4px 0" }}>
              {e6.realtime_usage.total_tokens.toLocaleString()} TOKENS
            </div>
            <div style={{ fontSize: "12px" }}>
              Costo real acumulado: ${e6.realtime_usage.accumulated_cost_usd.toFixed(6)} USD
            </div>
          </div>

          <div className="pixel-card pixel-card-emerald">
            <div style={{ fontSize: "12px", color: "var(--px-text-muted)" }}>
              LATENCIA PROMEDIO / P95
            </div>
            <div className="pixel-subtitle" style={{ fontSize: "28px", margin: "4px 0" }}>
              {data.observability_metrics.avg_latency_ms} ms
            </div>
            <div style={{ fontSize: "12px" }}>
              P95: {data.observability_metrics.p95_latency_ms} ms | Disponibilidad:{" "}
              {data.observability_metrics.availability_percent}%
            </div>
          </div>

          <div className="pixel-card">
            <div style={{ fontSize: "12px", color: "var(--px-text-muted)" }}>
              CADENA DE AUDITORÍA SHA-256
            </div>
            <div
              className="pixel-subtitle"
              style={{
                fontSize: "24px",
                margin: "4px 0",
                color: data.audit_integrity.is_valid
                  ? "var(--px-emerald)"
                  : "var(--px-coral)"
              }}
            >
              {data.audit_integrity.is_valid ? "ÍNTEGRA (VERIFICADA)" : "CORRUPTA"}
            </div>
            <div style={{ fontSize: "12px" }}>
              Bloques sellados: {data.audit_integrity.verified_records}
            </div>
          </div>
        </div>

        {/* Simulador interactivo del Circuit Breaker */}
        <div
          className="pixel-card"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "10px"
          }}
        >
          <div>
            <strong>Simulador de Fallos del Circuit Breaker:</strong> Prueba cómo el Root Agent
            ADK conmuta automáticamente de{" "}
            <code>Vertex AI (Gemini 2.5)</code> hacia{" "}
            <code>Ollama Local (llama3.2:3b)</code> sin interrumpir el servicio.
          </div>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <button
              type="button"
              className="pixel-btn pixel-btn-emerald"
              onClick={() => handleCircuitBreakerChange("CLOSED")}
            >
              RESTAURAR VERTEX (CLOSED)
            </button>
            <button
              type="button"
              className="pixel-btn pixel-btn-amber"
              onClick={() => handleCircuitBreakerChange("HALF_OPEN")}
            >
              SONDA (HALF_OPEN)
            </button>
            <button
              type="button"
              className="pixel-btn pixel-btn-coral"
              onClick={() => handleCircuitBreakerChange("OPEN")}
            >
              SIMULAR CAÍDA VERTEX → OLLAMA (OPEN)
            </button>
          </div>
        </div>
      </section>

      {/* SECCIÓN E6 INTEGRADA: ANÁLISIS GRÁFICO DE COSTOS MENSUALES Y COMPARATIVA ENTRE MODALIDADES */}
      <section className="pixel-window" aria-labelledby="e6-cost-heading">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "14px",
            marginBottom: "16px"
          }}
        >
          <div>
            <h2 id="e6-cost-heading" className="pixel-title" style={{ margin: 0 }}>
              2. ENTREGABLE E6 INTEGRADO — ANÁLISIS DE COSTOS MENSUALES Y COMPARATIVA DE MODALIDADES
            </h2>
            <p style={{ margin: "6px 0 0 0", color: "var(--px-text-muted)" }}>
              Desglose proyectado de Tokens, Cómputo Cloud Run, Almacenamiento Cloud SQL y Red para
              TechCorp LATAM.
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <label htmlFor="emp-slider" style={{ fontSize: "13px", fontWeight: 700 }}>
              Escala Empleados ({simulatedEmployees}):
            </label>
            <input
              id="emp-slider"
              type="range"
              min={100}
              max={2500}
              step={100}
              value={simulatedEmployees}
              onChange={(e) => setSimulatedEmployees(Number(e.target.value))}
              aria-label="Simulador de número de empleados"
            />
          </div>
        </div>

        {/* Gráfico Pixel Art de Barras: Desglose Mensual por Rubro (Modalidad 2.2) */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: "18px",
            marginBottom: "20px"
          }}
        >
          <div className="pixel-card">
            <h3 className="pixel-title" style={{ fontSize: "12px" }}>
              DESGLOSE MENSUAL — MODALIDAD 2.2 ({simulatedEmployees} EMPLEADOS)
            </h3>

            {[
              {
                label: "Tokens Vertex AI (Mix 80% Flash / 15% Pro / 5% Caché)",
                val: breakdown.tokens_vertex_ai_hybrid * scaleFactor,
                color: "var(--px-amber)"
              },
              {
                label: "Cómputo Serverless (Cloud Run Backend ADK + Frontend)",
                val: breakdown.compute_cloud_run * scaleFactor,
                color: "var(--px-cyan)"
              },
              {
                label: "Base de Datos Cloud SQL (PostgreSQL 16 HA + Backups)",
                val: breakdown.database_cloud_sql_pg16 * (0.7 + 0.3 * scaleFactor),
                color: "var(--px-emerald)"
              },
              {
                label: "Almacenamiento JSONL Inmutable + Secret Manager",
                val: breakdown.storage_audit_and_secrets * scaleFactor,
                color: "var(--px-violet)"
              },
              {
                label: "Red VPC + Cloud Logging & Monitoring",
                val: breakdown.network_and_cloud_logging * scaleFactor,
                color: "var(--px-coral)"
              }
            ].map((item, i) => {
              const totalScaled = breakdown.total_monthly_usd * scaleFactor;
              const pct = Math.min(100, Math.round((item.val / totalScaled) * 100));
              return (
                <div key={i} style={{ marginBottom: "12px" }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      fontSize: "12.5px",
                      marginBottom: "4px"
                    }}
                  >
                    <span>{item.label}</span>
                    <strong>
                      ${item.val.toFixed(2)} USD ({pct}%)
                    </strong>
                  </div>
                  <div className="pixel-bar-track" aria-hidden="true">
                    <div
                      className="pixel-bar-fill"
                      style={{ width: `${pct}%`, color: item.color }}
                    />
                  </div>
                </div>
              );
            })}

            <div
              style={{
                marginTop: "14px",
                paddingTop: "10px",
                borderTop: "2px solid var(--px-amber)",
                display: "flex",
                justifyContent: "space-between",
                fontSize: "15px"
              }}
            >
              <strong>TOTAL MENSUAL ESTIMADO:</strong>
              <strong style={{ color: "var(--px-amber)" }}>
                ${(breakdown.total_monthly_usd * scaleFactor).toFixed(2)} USD / mes ($
                {breakdown.cost_per_employee_usd.toFixed(2)} / empleado)
              </strong>
            </div>
          </div>

          {/* Gráfico Comparativo entre Modalidades (2.1 vs 2.2 vs 2.3) */}
          <div className="pixel-card pixel-card-emerald">
            <h3 className="pixel-title" style={{ fontSize: "12px" }}>
              COMPARATIVA DE ARQUITECTURAS (2.1 GCP vs 2.2 ADK+GCP vs 2.3 OLLAMA)
            </h3>

            {e6.modalities_comparison.map((mod) => {
              const scaledTotal = mod.total_usd * scaleFactor;
              const widthPct = Math.min(
                100,
                Math.round((mod.total_usd / maxModalityCost) * 100)
              );
              return (
                <div
                  key={mod.modality_id}
                  style={{
                    marginBottom: "14px",
                    padding: "10px",
                    border: mod.recommended
                      ? "2px solid var(--px-emerald)"
                      : "1px solid var(--px-border-light)",
                    backgroundColor: "rgba(0,0,0,0.25)"
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      fontSize: "12.5px",
                      marginBottom: "6px"
                    }}
                  >
                    <strong>
                      {mod.name} {mod.recommended ? "★ ÓPTIMA" : ""}
                    </strong>
                    <strong style={{ color: "var(--px-amber)" }}>
                      ${scaledTotal.toFixed(2)} USD/mes
                    </strong>
                  </div>
                  <div className="pixel-bar-track" aria-hidden="true">
                    <div
                      className="pixel-bar-fill"
                      style={{
                        width: `${widthPct}%`,
                        color: mod.recommended
                          ? "var(--px-emerald)"
                          : "var(--px-cyan)"
                      }}
                    />
                  </div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      fontSize: "11.5px",
                      marginTop: "6px",
                      color: "var(--px-text-muted)"
                    }}
                  >
                    <span>Tokens: ${(mod.tokens_usd * scaleFactor).toFixed(2)}</span>
                    <span>Cómputo: ${(mod.compute_usd * scaleFactor).toFixed(2)}</span>
                    <span>BD/Red: ${(mod.storage_network_usd * scaleFactor).toFixed(2)}</span>
                    <span>Latencia P95: {mod.p95_latency_ms}ms</span>
                    <span>SLA: {mod.availability_sla_pct}%</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* MONITOR CUANTITATIVO DE ACCIONES Y CALIDAD DE DATOS */}
      <section className="pixel-window" aria-labelledby="quant-snapshot-heading">
        <h2 id="quant-snapshot-heading" className="pixel-title">
          3. SNAPSHOT DEL MOTOR CUANTITATIVO Y CALIDAD DE DATOS FINANCIEROS
        </h2>
        <div style={{ overflowX: "auto" }}>
          <table className="pixel-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Emisor</th>
                <th>Precio (USD)</th>
                <th>SMA-20</th>
                <th>EMA-12</th>
                <th>RSI-14</th>
                <th>Volatilidad Anual</th>
                <th>Sharpe Ratio</th>
                <th>Max Drawdown</th>
                <th>Calidad / Proveedor</th>
              </tr>
            </thead>
            <tbody>
              {data.quantitative_market_snapshot.map((m) => (
                <tr key={m.ticker}>
                  <td>
                    <strong>{m.ticker}</strong>
                  </td>
                  <td>{m.company_name}</td>
                  <td>${m.latest_price.toFixed(2)}</td>
                  <td>${m.sma_20.toFixed(2)}</td>
                  <td>${m.ema_12.toFixed(2)}</td>
                  <td>{m.rsi_14.toFixed(2)}</td>
                  <td>{m.annualized_volatility_pct.toFixed(2)}%</td>
                  <td>
                    <strong>{m.sharpe_ratio.toFixed(2)}</strong>
                  </td>
                  <td style={{ color: "var(--px-coral)" }}>
                    {m.max_drawdown_pct.toFixed(2)}%
                  </td>
                  <td>
                    <span className="pixel-badge badge-closed">
                      {m.quality_status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* VISOR DE AUDITORÍA INMUTABLE (JSONL + CADENA SHA-256) */}
      <section className="pixel-window" aria-labelledby="audit-trail-heading">
        <h2 id="audit-trail-heading" className="pixel-title">
          4. REGISTRO DE AUDITORÍA INMUTABLE (JSONL + CADENA HASH SHA-256)
        </h2>
        <div style={{ overflowX: "auto" }}>
          <table className="pixel-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Timestamp UTC</th>
                <th>Evento</th>
                <th>Usuario / Rol</th>
                <th>Sesión ADK</th>
                <th>Modelo / Proveedor</th>
                <th>Tokens</th>
                <th>Costo USD</th>
                <th>Circuit Breaker</th>
                <th>Hash SHA-256 Encadenado</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_audit_logs.map((log) => (
                <tr key={log.id}>
                  <td>#{log.id}</td>
                  <td>{log.event_timestamp.slice(0, 19).replace("T", " ")}</td>
                  <td>{log.event_type}</td>
                  <td>
                    {log.user_id} ({log.user_role})
                  </td>
                  <td>{log.session_id}</td>
                  <td>
                    {log.model_used} ({log.provider_used})
                  </td>
                  <td>{log.total_tokens}</td>
                  <td>${Number(log.cost_usd).toFixed(6)}</td>
                  <td>{log.circuit_breaker_state}</td>
                  <td>
                    <code title={log.record_hash}>
                      {log.record_hash.slice(0, 18)}...
                    </code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};
