# Estrategia de Calidad y Pruebas Automatizadas (`TESTING.md`)
**Rol Responsable:** Software Quality Engineer

---

## 1. Pirámide de Pruebas Implementada

1. **Pruebas Unitarias (`backend/tests/test_quant_audit.py`):**
   - Verificación matemática de indicadores bursátiles (SMA-20, EMA-12, RSI-14, Volatilidad Anualizada, Sharpe Ratio y Máximo Drawdown).
   - Detección de anomalías de precios ($|Z| > 3.5$), datos atrasados (*stale data*), inconsistencias de divisa (`USD` vs `MXN`) y falta de cobertura de ticker.
   - Verificación criptográfica de la cadena de hashes SHA-256 del registro de auditoría inmutable y detección de adulteraciones.
2. **Pruebas de Resiliencia y Agente ADK (`backend/tests/test_agent_cb.py`):**
   - Transiciones del **Circuit Breaker** (`CLOSED` $\rightarrow$ `OPEN` tras 3 fallos de Vertex AI $\rightarrow$ fallback automático a Ollama `llama3.2:3b` $\rightarrow$ `HALF_OPEN` $\rightarrow$ `CLOSED`).
   - Ciclo completo **ReAct (`Reason` $\rightarrow$ `Act` $\rightarrow$ `Observe`)** invocando las `@tool` decoradas y persistiendo memoria por `session_id`.
3. **Pruebas de Integración y Seguridad API (`backend/tests/test_api.py`):**
   - Autenticación JWT y validación de que el Rol `usuario` **jamás** recibe telemetría técnica ni puede acceder a `/api/v1/admin/*` (`HTTP 403`).
   - Cumplimiento estricto del **Rate Limiting de 10 requests/minuto por usuario** (`HTTP 429` en la solicitud #11).
   - Generación y descarga real de reportes de auditoría y costos en formatos **CSV** (`text/csv`) y **PDF** (`application/pdf`).
   - Endpoints de observabilidad `/health/live`, `/health/ready` y `/health/db`.

## 2. Ejecución de Pruebas
```bash
make test
```
