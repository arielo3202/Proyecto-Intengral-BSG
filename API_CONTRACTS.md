# Contratos de API REST (`API_CONTRACTS.md`)
**Complemento formal a la especificación interactiva OpenAPI 3.1 disponible en `/docs`**

---

## 1. Seguridad, Cabeceras y Segregación por Rol (RBAC)

Todos los endpoints protegidos requieren la cabecera:
```http
Authorization: Bearer <JWT_TOKEN_HS256_OR_RS256>
```

### Garantía de No Exposición Técnica al Rol `usuario`
El endpoint `POST /api/v1/chat/message` inspecciona el claim `role` del token JWT validado:
- Si `role == "usuario"`: Responde con el esquema `UserChatResponseDTO` (solo contiene `session_id`, `reply`, `timestamp` y `remaining_requests_minute`). **Jamás** serializa costos, uso de tokens, proveedor LLM, latencia ni pasos internos del ciclo ReAct.
- Si `role == "admin"`: Responde con el esquema `AdminChatResponseDTO`, que extiende la respuesta con el bloque `technical_telemetry` (traza completa `Reason -> Act -> Observe`, tokens, costo en USD, latencia, estado del Circuit Breaker y hash SHA-256 de auditoría).

---

## 2. Catálogo de Endpoints

| Método | Ruta | Rol Requerido | Rate Limit | Descripción |
| :---: | :--- | :---: | :---: | :--- |
| `POST` | `/api/v1/auth/login` | Público | 20/min | Autentica credenciales y emite JWT firmado con claims `sub`, `email`, `role`, `exp`. |
| `GET` | `/api/v1/auth/me` | `usuario`, `admin` | 30/min | Devuelve el perfil del usuario autenticado y su cuota actual de rate limit. |
| `POST` | `/api/v1/chat/message` | `usuario`, `admin` | **10/min** | Ejecuta el Root Agent de Google ADK (ciclo ReAct con `@tool` y `session_id`). |
| `GET` | `/api/v1/chat/sessions/{session_id}` | `usuario`, `admin` | 30/min | Recupera el historial multi-turno de una sesión perteneciente al usuario. |
| `GET` | `/api/v1/admin/dashboard` | **Solo `admin`** | 30/min | Devuelve métricas en tiempo real, estado del Circuit Breaker, salud de proveedores y **Análisis de Costos E6** completo. |
| `POST` | `/api/v1/admin/circuit-breaker/toggle` | **Solo `admin`** | 10/min | Permite simular o restaurar el estado del Circuit Breaker (`CLOSED`, `OPEN`, `HALF_OPEN`) para pruebas operativas. |
| `GET` | `/api/v1/admin/audit` | **Solo `admin`** | 30/min | Lista los registros de auditoría inmutable (JSONL + PostgreSQL) y verifica la cadena SHA-256. |
| `GET` | `/api/v1/admin/export/csv` | **Solo `admin`** | 10/min | Descarga en `text/csv` los registros de auditoría inmutable y métricas de costos. |
| `GET` | `/api/v1/admin/export/pdf` | **Solo `admin`** | 10/min | Genera y descarga en `application/pdf` el reporte oficial de auditoría, métricas y análisis financiero E6. |
| `GET` | `/health/live` | Público | Sin límite | Liveness probe para Cloud Run. |
| `GET` | `/health/ready` | Público | Sin límite | Readiness probe (verifica estado de ADK Runner, Circuit Breaker y proveedores). |
| `GET` | `/health/db` | Público | Sin límite | Comprueba conectividad activa y latencia contra PostgreSQL. |
