import {
  AdminDashboardData,
  AuthSession,
  ChatResponsePayload
} from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export async function loginWithCredentials(
  email: string,
  password: string
): Promise<AuthSession> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Error de autenticación JWT");
  }
  return res.json();
}

export async function sendChatTurn(
  token: string,
  sessionId: string,
  message: string,
  preferredTier: "light" | "pro" = "light"
): Promise<ChatResponsePayload> {
  const res = await fetch(`${API_BASE}/api/v1/chat/message`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      preferred_tier: preferredTier
    })
  });
  if (res.status === 429) {
    const err = await res.json().catch(() => ({}));
    const retry = res.headers.get("Retry-After") || "60";
    throw new Error(
      `[HTTP 429 RATE LIMIT] Has superado las 10 consultas/minuto. Reintenta en ${retry}s. (${err?.detail?.message || ""})`
    );
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Error al procesar consulta con el Agente ADK");
  }
  return res.json();
}

export async function fetchAdminDashboard(
  token: string
): Promise<AdminDashboardData> {
  const res = await fetch(`${API_BASE}/api/v1/admin/dashboard`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) {
    throw new Error("No autorizado o error al cargar el Dashboard Admin E6");
  }
  return res.json();
}

export async function toggleCircuitBreakerState(
  token: string,
  targetState: "CLOSED" | "OPEN" | "HALF_OPEN"
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/admin/circuit-breaker/toggle`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({
      target_state: targetState,
      reason: `Cambio manual desde UI Pixel Art a ${targetState}`
    })
  });
  if (!res.ok) {
    throw new Error("No se pudo cambiar el estado del Circuit Breaker");
  }
}

export async function downloadAuditReport(
  token: string,
  format: "csv" | "pdf"
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/admin/export/${format}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) {
    throw new Error(`Error exportando reporte en formato ${format.toUpperCase()}`);
  }
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download =
    format === "pdf"
      ? "techcorp_latam_audit_cost_report_e6.pdf"
      : "techcorp_latam_audit_metrics.csv";
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
