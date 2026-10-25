# E1 — Arquitectura del Sistema (`ARCHITECTURE.md`)
**Proyecto A — Asistente Empresarial Inteligente | Cliente: TechCorp LATAM (800 empleados)**  
**Modalidad 2.2:** Google Agent Development Kit (ADK) + Google Cloud Platform (Cloud Run, Cloud SQL, Vertex AI)

---

## 1. Visión Arquitectónica y Principios Rectorales

La arquitectura del **Asistente Empresarial Inteligente de TechCorp LATAM** fue diseñada por el equipo multidisciplinario siguiendo el principio de **Monolito Modular Cloud-Native Desacoplado** sobre **Google Cloud Run** y **Cloud SQL (PostgreSQL 16)**, evitando la sobreingeniería (sin Kubernetes/GKE, sin Kafka y sin mallas de microservicios innecesarias para una carga de 800 empleados), pero garantizando trazabilidad criptográfica, control estricto de costos, alta disponibilidad mediante un **Circuit Breaker con Fallback hacia Ollama (`llama3.2:3b`)** y seguridad por diseño (**RBAC estricto en backend**).

### Principios Aplicados
1. **Security by Design:** Autenticación JWT (HS256/RS256) validada en cada request; segregación total de esquemas de respuesta (Pydantic DTOs distintos para `user` y `admin` de modo que ningún dato de tokens, latencia, hash de auditoría o costos viaje jamás en el payload HTTP de un usuario estándar).
2. **Observability by Design:** Registro estructurado compatible con **Google Cloud Logging** (mínimo 6 tipos de eventos estructurados: `AGENT_REACT_STEP`, `LLM_INVOCATION`, `CIRCUIT_BREAKER_STATE_CHANGE`, `RATE_LIMIT_EXCEEDED`, `FINANCIAL_DATA_QUALITY_ALERT`, `AUDIT_RECORD_SEALED`).
3. **Resiliencia Multi-Proveedor (LLM y Datos Financieros):**
   - **LLM:** Vertex AI (`gemini-2.5-pro` / `gemini-2.5-flash`) como proveedor primario; si acumula 3 fallos consecutivos o timeouts (>12s), el **Circuit Breaker** pasa a estado `OPEN` y enruta automáticamente las consultas del ciclo ReAct hacia **Ollama (`llama3.2:3b`)** local/sidecar sin interrumpir la operación de los 800 empleados.
   - **Datos Bursátiles / Cuantitativos:** Proveedor primario con validación de frescura, moneda, cobertura de ticker y detección de anomalías por Z-score ($|z| > 3.5$), con fallback automático a proveedor secundario homologado sin mezclar monedas ni ajustes de forma silenciosa.

---

## 2. Diagrama de Arquitectura C4 — Nivel 1 (Contexto) y Nivel 2 (Contenedores)

```mermaid
flowchart TB
    subgraph Usuarios["Usuarios de TechCorp LATAM (800 Empleados)"]
        EMP["👤 Empleado (Rol: usuario)<br/>Consultas de políticas, TI y soporte"]
        ADM["🛡️ Administrador TI/FinOps (Rol: admin)<br/>Auditoría inmutable, métricas y costos E6"]
    end

    subgraph Frontend_Container["Cloud Run Service #1: Frontend Web"]
        UI["🕹️ SPA React 18 + Vite 6 + TypeScript<br/>Diseño UI/UX Pixel Art (WCAG AA)<br/>- Chat Terminal Multi-turno<br/>- Dashboard Costos E6 y Auditoría (Solo Admin)"]
    end

    subgraph Backend_Container["Cloud Run Service #2: Backend API + Google ADK Runner (Python 3.14)"]
        API["⚡ FastAPI REST Gateway<br/>- Auth JWT (HS256/RS256) + RBAC<br/>- Rate Limiter (10 req/min/user)<br/>- Exportador PDF/CSV"]
        ADK["🤖 Google ADK Root Agent (Ciclo ReAct)<br/>- Reason / Act / Observe<br/>- Gestor de Session Memory (session_id)"]
        TOOLS["🛠️ Catálogo de @tool Invocables<br/>1. search_corporate_policies<br/>2. create_it_support_ticket<br/>3. analyze_stock_comparative"]
        CB["🔌 LLM Circuit Breaker + Router<br/>- Exponential Backoff + Jitter<br/>- Estado: CLOSED / OPEN / HALF_OPEN"]
        FIN_ENG["📈 Motor Cuantitativo y Data Quality<br/>- Caché TTL (Mercado Abierto/Cerrado)<br/>- Validador de Moneda, Tickers y Anomalías"]
        AUDIT["🔒 Motor de Auditoría Criptográfica<br/>- Cadena SHA-256 (prev_hash -> record_hash)<br/>- Exportación JSONL + PostgreSQL"]
    end

    subgraph GCP_Managed["Google Cloud Platform (Servicios Gestionados)"]
        VERTEX["✨ Vertex AI API<br/>Gemini 2.5 Pro / Gemini 2.5 Light"]
        CSQL[("🐘 Cloud SQL (PostgreSQL 16)<br/>- users / sessions / messages<br/>- immutable_audit_logs<br/>- market_timeseries / metrics")]
        SECRETS["🔑 Cloud Secret Manager<br/>Claves JWT, Credenciales DB y APIs"]
        CLOG["📊 Cloud Logging & Monitoring<br/>Eventos estructurados JSON + Alertas"]
    end

    subgraph Fallback_Providers["Contingencia y Proveedores Externos"]
        OLLAMA["🦙 Ollama Local / Sidecar<br/>Modelo: llama3.2:3b (localhost:11434)"]
        FIN_API1["🌐 Proveedor Financiero Primario<br/>(Cotizaciones y Series OHLCV)"]
        FIN_API2["🌐 Proveedor Financiero Fallback<br/>(Homologado en Moneda y Ajustes)"]
    end

    EMP -->|HTTPS / JWT| UI
    ADM -->|HTTPS / JWT| UI
    UI -->|REST JSON / Bearer Token| API
    API --> ADK
    ADK --> TOOLS
    ADK --> CB
    TOOLS --> FIN_ENG
    TOOLS --> CSQL
    CB -->|Ruta Primaria| VERTEX
    CB -.->|Ruta Fallback si CB=OPEN| OLLAMA
    FIN_ENG -->|Consulta Primaria| FIN_API1
    FIN_ENG -.->|Fallback Homologado| FIN_API2
    API --> AUDIT
    AUDIT --> CSQL
    API --> CLOG
    API -.->|Lectura al arranque| SECRETS
```

---

## 3. Diagrama de Componentes Internos del Backend (C4 Nivel 3)

```mermaid
classDiagram
    class FastAPIGateway {
        +POST /api/v1/auth/login
        +POST /api/v1/chat/message
        +GET /api/v1/chat/sessions/{session_id}
        +GET /api/v1/admin/dashboard
        +GET /api/v1/admin/audit
        +GET /api/v1/admin/export/csv
        +GET /api/v1/admin/export/pdf
        +GET /health/live
        +GET /health/ready
        +GET /health/db
    }

    class SecurityMiddleware {
        +verify_jwt_token(token: str) UserClaims
        +require_role(allowed_roles: list[Role])
        +check_rate_limit(user_id: str) RateLimitStatus
    }

    class TechCorpADKRootAgent {
        +session_memory: SessionMemoryStore
        +tools: dict[str, ToolDefinition]
        +run_react_cycle(user_id: str, session_id: str, prompt: str) AgentExecutionResult
    }

    class LLMCircuitBreaker {
        +state: CircuitState
        +failure_count: int
        +invoke_with_fallback(messages, tools) LLMResponse
        +record_success()
        +record_failure(reason: str)
    }

    class QuantitativeMarketService {
        +get_verified_quote(ticker: str, expected_currency: str) MarketSeries
        +compute_indicators(series: MarketSeries) QuantIndicators
        +validate_data_quality(points: list) QualityReport
    }

    class ImmutableAuditService {
        +append_event(event: AuditPayload) AuditRecord
        +verify_chain_integrity() ChainVerificationResult
        +export_csv() bytes
        +export_pdf() bytes
    }

    FastAPIGateway --> SecurityMiddleware
    FastAPIGateway --> TechCorpADKRootAgent
    FastAPIGateway --> ImmutableAuditService
    TechCorpADKRootAgent --> LLMCircuitBreaker
    TechCorpADKRootAgent --> QuantitativeMarketService
```

---

## 4. Diagrama de Estados y Transiciones del Agente ReAct (Google ADK)

El ciclo **ReAct (`Reason` → `Act` → `Observe`)** implementado sobre Google ADK mantiene estado determinista y trazabilidad por cada turno de conversación asociado a `session_id`:

```mermaid
stateDiagram-v2
    [*] --> SESSION_LOAD: Request autenticada + Rate Limit OK (<10 req/min)
    SESSION_LOAD --> REASONING: Carga historial multi-turno de session_id desde Cloud SQL
    
    state REASONING {
        [*] --> EVALUATE_INTENT
        EVALUATE_INTENT --> CHECK_CIRCUIT_BREAKER
        CHECK_CIRCUIT_BREAKER --> CALL_VERTEX_GEMINI: CB == CLOSED o HALF_OPEN
        CHECK_CIRCUIT_BREAKER --> CALL_OLLAMA_FALLBACK: CB == OPEN
        CALL_VERTEX_GEMINI -->CALL_OLLAMA_FALLBACK: Timeout / HTTP 429 / 5xx (Incrementa fallo CB)
    }

    REASONING --> ACT_TOOL_EXECUTION: El agente decide invocar @tool (ej. search_corporate_policies)
    REASONING --> FINAL_SYNTHESIS: El agente ya posee evidencia suficiente

    state ACT_TOOL_EXECUTION {
        [*] --> VALIDATE_TOOL_ARGS
        VALIDATE_TOOL_ARGS --> EXECUTE_PYTHON_TOOL
        EXECUTE_PYTHON_TOOL --> CAPTURE_TOOL_OUTPUT
    }

    ACT_TOOL_EXECUTION --> OBSERVING: Retorna JSON estructurado de la herramienta
    OBSERVING --> REASONING: Inyecta observación al contexto ReAct (máx. 4 iteraciones)

    FINAL_SYNTHESIS --> AUDIT_AND_PERSIST: Guarda turno en session_memory + Sella Hash SHA-256 en JSONL/PostgreSQL
    AUDIT_AND_PERSIST --> FILTER_BY_ROLE: Aplica DTO según Rol JWT
    FILTER_BY_ROLE --> [*]: Rol 'usuario' (Solo respuesta limpia) / Rol 'admin' (Respuesta + Telemetría ReAct)
```

---

## 5. Flujo de Resiliencia del Circuit Breaker y Proveedores Financieros

```mermaid
sequenceDiagram
    autonumber
    actor U as Empleado / Admin
    participant API as FastAPI + RateLimiter
    participant ADK as ADK Root Agent (ReAct)
    participant CB as Circuit Breaker
    participant VTX as Vertex AI (Gemini 2.5)
    participant OLL as Ollama (llama3.2:3b)
    participant DB as Cloud SQL (PostgreSQL)

    U->>API: POST /api/v1/chat/message (Bearer JWT)
    API->>API: Valida JWT + Verifica Rate Limit (<=10 req/min)
    API->>ADK: run_react_cycle(session_id, message)
    ADK->>DB: Recupera Session Memory (session_id)
    ADK->>CB: Solicita inferencia ReAct (Reason)
    alt Circuit Breaker CLOSED
        CB->>VTX: generate_content (timeout=12s, retry=2 exp backoff)
        alt Vertex AI Responde OK
            VTX-->>CB: Pensamiento + Llamada a @tool
        else Error 429 / 503 / Timeout en Vertex AI
            VTX--xCB: Excepción capturada
            CB->>CB: Incrementa contador de fallos (Si >=3 -> OPEN)
            CB->>OLL: Fallback inmediato a llama3.2:3b (localhost:11434)
            OLL-->>CB: Pensamiento + Llamada a @tool
        end
    else Circuit Breaker OPEN
        CB->>OLL: Enrutamiento directo a llama3.2:3b (ahorra latencia de espera)
        OLL-->>CB: Pensamiento + Llamada a @tool
    end
    CB-->>ADK: Acción determinada
    ADK->>ADK: Ejecuta @tool (Act) y registra observación (Observe)
    ADK->>DB: Persiste nuevos mensajes + Registro de Auditoría con Hash SHA-256 Encadenado
    ADK-->>API: Resultado + Metadatos Técnicos
    API->>API: Filtra campos técnicos si role == "usuario"
    API-->>U: HTTP 200 JSON
```
