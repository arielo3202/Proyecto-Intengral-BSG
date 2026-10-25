# E2 — Documento de Diseño Técnico (RFC) y Análisis de Costos (`DESIGN_RFC.md`)
**Proyecto A — Asistente Empresarial Inteligente (TechCorp LATAM)**  
**Estado:** Aprobado para Producción (v1.0.0)  
**Autores:** Principal Solution Architect, Senior Python Backend Developer, Senior React Frontend Developer, Financial Quantitative Analyst, Application Security Architect, Product Owner.

---

## 1. Resumen Ejecutivo y Contexto del Problema

**TechCorp LATAM** cuenta con **800 empleados** distribuidos en Latinoamérica que realizan consultas diarias sobre políticas internas (RRHH, trabajo remoto, reembolsos, vacaciones), procedimientos de seguridad informática, soporte técnico N1/N2 y análisis financiero corporativo/comparativo de mercado.  
Antes de este proyecto, las consultas generaban cuellos de botella en Mesa de Ayuda (tiempo medio de respuesta > 4 horas) y carecían de trazabilidad auditable y de control presupuestario sobre el consumo de modelos generativos.

Este RFC documenta las decisiones de diseño de la **Modalidad 2.2 (Google ADK + GCP)** y detalla cómo se satisfacen los requisitos funcionales y no funcionales sin caer en sobreingeniería.

---

## 2. Justificación de Decisiones Tecnológicas y Alternativas Descartadas

| Componente | Selección Tecnológica | Justificación Técnica y de Negocio | Alternativas Descartadas y Motivo de Rechazo |
| :--- | :--- | :--- | :--- |
| **Lenguaje y Runtime Backend** | **Python 3.14 + FastAPI (ASGI)** | Aprovecha las mejoras de rendimiento del intérprete en Python 3.14, tipado estricto moderno, evaluación diferida de anotaciones (PEP 649/749) y concurrencia asíncrona nativa en FastAPI para soportar I/O concurrente hacia Vertex AI, Ollama y PostgreSQL. | **Django REST Framework:** Mayor sobrecarga síncrona y acoplamiento ORM innecesario.<br/>**Node.js/NestJS:** Menor madurez nativa con Google ADK Python y librerías cuantitativas (`numpy`/`pandas`). |
| **Framework de Agentes** | **Google Agent Development Kit (ADK)** | Implementación nativa del ciclo **ReAct (`Reason` → `Act` → `Observe`)** con soporte declarativo para herramientas `@tool`, memoria de sesión por `session_id` e integración de primera clase con Vertex AI y Cloud Run. | **LangChain / CrewAI:** Exceso de capas de abstracción cambiantes, mayor latencia de serialización y dificultad para auditar cada paso determinista del prompt. |
| **LLM Primario y Fallback** | **Vertex AI (Gemini 2.5 Pro / Light) + Fallback Ollama (`llama3.2:3b`)** | `Gemini 2.5 Light (Flash)` resuelve el 80% de consultas de políticas con latencia sub-segundo y bajo costo; `Gemini 2.5 Pro` atiende razonamiento cuantitativo complejo; `llama3.2:3b` en Ollama garantiza continuidad operativa si la nube sufre caídas o *rate limits* (HTTP 429). | **Proveedor único (OpenAI o solo Vertex sin fallback):** Punto único de falla que detendría la operación de los 800 empleados ante una degradación regional. |
| **Infraestructura de Cómputo** | **Google Cloud Run (Serverless Containers)** | Escalado automático de 1 a $N$ instancias según concurrencia HTTP, pago exacto por vCPU/RAM consumidos y despliegue directo desde contenedor sin administrar nodos. | **Google Kubernetes Engine (GKE):** Sobreingeniería severa (Regla 6) para 800 empleados; costo fijo de gestión de clúster y complejidad DevOps injustificada. |
| **Base de Datos** | **Cloud SQL para PostgreSQL 16** | ACID transaccional para usuarios, sesiones multi-turno, cadena inmutable de auditoría y series temporales financieras indexadas por `(ticker, timestamp DESC)`. | **MongoDB / Firestore puro:** Menor rigidez de esquema para series financieras y reportes relacionales de costos/auditoría. |
| **Interfaz Frontend** | **React 18 + Vite 6 + TypeScript (Estilo Pixel Art WCAG AA)** | Compilación instantánea con Vite 6, tipado estricto de contratos API y estética **Pixel Art** de alto contraste inspirada en terminales retro financieras, cumpliendo navegación por teclado y lectores de pantalla (ARIA). | **Next.js SSR completo:** Innecesario para una SPA corporativa interna autenticada por JWT donde el SEO público no aplica. |

---

## 3. Documentación Detallada del Ciclo ReAct en Google ADK

El agente principal (`TechCorpADKRootAgent`) implementa el patrón **ReAct** en tres fases explícitas y auditadas en cada turno:

1. **Fase `REASON` (Razonamiento):**
   - El agente recibe el mensaje del usuario junto con la ventana de memoria recuperada de PostgreSQL para su `session_id`.
   - Evalúa si la consulta requiere consultar información autoritativa (políticas internas de TechCorp LATAM, creación/estado de tickets TI, o análisis cuantitativo bursátil) o si puede responder directamente con el contexto existente.
   - Selecciona el modelo óptimo: `gemini-2.5-flash` (Light) para consultas operativas rápidas o `gemini-2.5-pro` para análisis financiero multi-indicador. Si el `LLMCircuitBreaker` está en estado `OPEN`, enruta la llamada a `Ollama (llama3.2:3b)`.
2. **Fase `ACT` (Acción mediante `@tool`):**
   - El agente invoca una o más herramientas Python decoradas con `@tool`:
     - `search_corporate_policies(query: str, category: str)`: Busca en el catálogo normativo de TechCorp LATAM (Vacaciones, Teletrabajo, Seguridad InfoSec, Reembolsos, Soporte TI) devolviendo el código oficial de política, SLA y pasos obligatorios.
     - `create_it_support_ticket(employee_email: str, issue_summary: str, priority: str)`: Registra un ticket auditable en la mesa de ayuda con SLA calculado.
     - `analyze_stock_comparative(tickers: list[str], period_days: int, base_currency: str)`: Ejecuta el motor cuantitativo financiero con validación de frescura, verificación de moneda homogénea, detección de anomalías ($Z$-score), cálculo de **SMA-20, EMA-12, RSI-14, Volatilidad Anualizada, Sharpe Ratio y Máximo Drawdown**.
3. **Fase `OBSERVE` (Observación y Síntesis):**
   - El resultado estructurado de la herramienta regresa al contexto del agente como un evento `TOOL_OBSERVATION`.
   - El agente verifica si los datos contienen alertas de calidad (ej. precio atrasado o ticker sin cobertura) y redacta la respuesta final fundamentada exclusivamente en los datos observados.

---

## 4. Diseño de Auditoría Inmutable (JSONL + Cadena Hash SHA-256)

Cada interacción procesada por el sistema genera un registro en la tabla `immutable_audit_logs` y en el archivo append-only `audit_trail.jsonl`. Para garantizar la inmutabilidad criptográfica:

$$H_n = \text{SHA256}\left( H_{n-1} \,\|\, \text{timestamp}_n \,\|\, \text{user\_id}_n \,\|\, \text{session\_id}_n \,\|\, \text{model}_n \,\|\, \text{prompt\_hash}_n \,\|\, \text{response\_hash}_n \,\|\, \text{cost\_usd}_n \right)$$

Donde $H_0 = \text{"0"} \times 64$ (Genesis Hash). Cualquier alteración manual de una fila histórica invalida inmediatamente la cadena completa al ejecutar el verificador de integridad en `/api/v1/admin/audit/verify`.

---

## 5. Análisis Real de Costos Mensuales y Comparativa entre Modalidades (Entregable E6 Integrado)

> **Nota de Diseño E6:** De acuerdo con las especificaciones del proyecto, este modelo matemático y comparativo está programado en vivo dentro del backend (`/api/v1/admin/cost-analysis`) y se visualiza gráficamente en el **Dashboard Pixel Art del Administrador** (`AdminCostDashboard.tsx`), permitiendo simular escenarios dinámicos sin depender de hojas de cálculo externas.

### 5.1 Supuestos Operativos Reales (800 Empleados — TechCorp LATAM)
- **Usuarios activos diarios (DAU):** 520 empleados (65% de 800) durante 22 días hábiles/mes.
- **Consultas promedio por empleado activo/día:** 6 consultas $\rightarrow$ **68,640 consultas/mes** (~70,000 requests/mes).
- **Longitud media por consulta (incluyendo Session Memory e invocación de Tools ReAct):**
  - Input: $1,150$ tokens promedio por request $\rightarrow$ **80.5M tokens de entrada/mes**.
  - Output: $420$ tokens promedio por request $\rightarrow$ **29.4M tokens de salida/mes**.
- **Distribución inteligente de ruteo LLM (Modalidad 2.2):**
  - 80% en **Vertex AI Gemini 2.5 Light (Flash)** ($0.15 / 1M input, $0.60 / 1M output).
  - 15% en **Vertex AI Gemini 2.5 Pro** para análisis cuantitativo complejo ($1.25 / 1M input, $5.00 / 1M output).
  - 5% absorbido por **Caché TTL + Fallback Ollama (`llama3.2:3b`)** ($0.00 en API).

### 5.2 Desglose Mensual de Costos — Modalidad 2.2 (Google ADK + GCP)

| Rubro de Costo | Dimensionamiento Técnico (800 Empleados) | Costo Mensual Estimado (USD) | % del Total |
| :--- | :--- | ---: | ---: |
| **Tokens LLM (Vertex AI Mix 80/15/5)** | 64.4M in / 23.5M out en Flash ($23.76) + 12.1M in / 4.4M out en Pro ($37.13) | **$60.89 USD** | 25.1% |
| **Cómputo Cloud Run (Backend + Frontend + Sidecar)** | 2 vCPU / 4 GB RAM (Backend min-instances=1) + 1 vCPU / 1 GB (Frontend) | **$78.40 USD** | 32.3% |
| **Base de Datos Cloud SQL (PostgreSQL 16)** | Instancia `db-custom-2-4096` + 50 GB SSD + Backups automatizados | **$84.50 USD** | 34.8% |
| **Almacenamiento y Secret Manager** | Retención JSONL en Cloud Storage (20 GB) + 12 secretos rotados + Artifact Registry | **$6.20 USD** | 2.6% |
| **Red y Observabilidad (Cloud Logging/Monitoring)** | Egreso VPC/Internet (~85 GB/mes) + Ingesta de logs estructurados (>50 GB free tier) | **$12.60 USD** | 5.2% |
| **TOTAL MENSUAL ESTIMADO (Modalidad 2.2)** | **Costo por empleado: $0.30 USD / mes** | **$242.59 USD / mes** | **100.0%** |

### 5.3 Comparativa Estratégica entre Modalidades (2.1 vs 2.2 vs 2.3)

| Criterio / Métrica | Modalidad 2.1: GCP Console Estándar (Todo en Gemini 2.5 Pro sin ADK Caching) | Modalidad 2.2: Google ADK + GCP (Seleccionada — Ruteo Híbrido + ReAct + Fallback) | Modalidad 2.3: Ollama 100% Local / On-Prem (`llama3.2:3b` en Servidor Dedicado GPU) |
| :--- | :--- | :--- | :--- |
| **Costo Mensual de Tokens (API)** | $247.63 USD / mes (100% llamadas a modelo Pro sin caché de herramientas) | **$60.89 USD / mes** (Ahorro de 75% por ruteo Flash/Pro + caché de tools ADK) | **$0.00 USD / mes** (Inferencia local sin pago por token) |
| **Costo Mensual de Cómputo** | $68.00 USD / mes (Cloud Run básico) | **$78.40 USD / mes** (Cloud Run con ADK Runner y contenedor de contingencia) | **$310.00 USD / mes** (Instancia con GPU L4/T4 o amortización de hardware + energía) |
| **Costo Base de Datos + Red + Logs** | $97.10 USD / mes | **$103.30 USD / mes** | **$45.00 USD / mes** (PostgreSQL auto-hospedado con mayor carga operativa TI) |
| **Costo Total Mensual (TCO)** | **$412.73 USD / mes** | **$242.59 USD / mes (Óptimo)** | **$355.00 USD / mes** |
| **Latencia P95 Promedio** | 2,150 ms | **920 ms** | 3,400 ms (bajo concurrencia de 800 usuarios en modelo 3B) |
| **Calidad de Razonamiento ReAct y Tool Use** | Alta, pero sin orquestación determinista ADK | **Sobresaliente** (Ciclo ReAct nativo + validación cuantitativa + fallback) | Limitada en razonamiento financiero complejo (3B parámetros propenso a alucinaciones en multi-tool) |
| **Disponibilidad SLA Estimada** | 99.5% (Dependiente de 1 sola API) | **99.95% (Circuit Breaker conmuta a Ollama local ante caída de Vertex AI)** | 98.5% (Sujeto a saturación de cola local en horas pico) |
