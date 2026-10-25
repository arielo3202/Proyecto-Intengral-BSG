# 🕹️ TechCorp LATAM — Proyecto A: Asistente Empresarial Inteligente
**Modalidad 2.2: Google Agent Development Kit (ADK) + Google Cloud Platform (Vertex AI, Cloud Run, Cloud SQL)**

Sistema empresarial de asistencia conversacional multi-turno, análisis cuantitativo financiero y auditoría criptográfica para los **800 empleados de TechCorp LATAM**, construido bajo un diseño visual **Pixel Art** accesible (WCAG AA).

---

## 🚀 Características Principales

1. **Agente ReAct con Google ADK (`Reason` → `Act` → `Observe`):**
   - **Root Agent** con memoria de sesión persistente por `session_id` en PostgreSQL.
   - **3 Tools invocables (`@tool`):**
     - `search_corporate_policies`: Consulta normativa oficial de RRHH, Teletrabajo, InfoSec, Reembolsos y Procedimientos TI de TechCorp LATAM.
     - `create_it_support_ticket`: Genera tickets de soporte técnico con asignación automática de SLA.
     - `analyze_stock_comparative`: Calcula indicadores cuantitativos reales (**SMA-20, EMA-12, RSI-14, Volatilidad Anualizada, Sharpe Ratio y Max Drawdown**) con validación de calidad de datos, homogeneidad de moneda, detección de anomalías ($Z$-score) y fallback entre proveedores financieros compatibles.
2. **Resiliencia LLM con Circuit Breaker:**
   - **LLM Primario:** Google Vertex AI (`gemini-2.5-pro` y `gemini-2.5-flash`).
   - **LLM Fallback:** Ollama local (`llama3.2:3b` en `localhost:11434`).
   - Conmutación automática cuando el Circuit Breaker detecta 3 fallos consecutivos, `HTTP 429` o timeouts, con recuperación automática en estado `HALF_OPEN`.
3. **Seguridad por Diseño y Segregación de Roles (JWT HS256 / RS256):**
   - **Rol `usuario`:** Acceso exclusivo al chat multi-turno. El backend filtra estrictamente cualquier dato de tokens, latencias, trazas ReAct, logs o costos.
   - **Rol `admin`:** Acceso total a telemetría en tiempo real, estado del Circuit Breaker, visor de auditoría inmutable (`JSONL + SHA-256`), exportación a **PDF y CSV** y **Dashboard Gráfico de Costos E6 Integrado**.
4. **Rate Limiting Estricto:** Límite de **10 requests/minuto por usuario** con respuesta `HTTP 429` y cabeceras `X-RateLimit-*`.

---

## 📁 Estructura del Proyecto

```text
techcorp-asistente-adk/
├── Makefile                        # Automatización de entorno .venv, migraciones, tests y ejecución dual
├── requirements.txt                # Dependencias orientadas a Python 3.14
├── .env.example                    # Plantilla de variables de entorno (cero secretos en código)
├── README.md                       # Documentación principal
├── ARCHITECTURE.md                 # [Entregable E1] Diagramas C4, flujos ReAct y estados del agente
├── DESIGN_RFC.md                   # [Entregable E2 + E6] RFC Técnico, decisiones y modelo de costos
├── REQUIREMENTS.md                 # Historias de usuario y criterios de aceptación
├── DATA_MODEL.md                   # Modelo Entidad-Relación (MER) e índices PostgreSQL
├── API_CONTRACTS.md                # Contratos REST y políticas RBAC
├── DEVELOPMENT.md                  # Guía de entorno local reproducible
├── DEPLOYMENT.md                   # Despliegue en Cloud Run + Cloud SQL + Secret Manager
├── TESTING.md                      # Estrategia de pruebas automatizadas
├── CHANGELOG.md                    # Historial de versiones (SemVer)
├── docs/adr/                       # Architecture Decision Records (ADR-001 a ADR-003)
├── scripts/
│   ├── setup_venv.sh               # Creador de entorno virtual .venv en Python 3.14
│   └── init_db.sql                 # Esquema DDL PostgreSQL 16 (relacional + series temporales)
├── deploy/
│   ├── Dockerfile.backend          # Contenedor productivo Backend Python 3.14 + ADK Runner
│   ├── Dockerfile.frontend         # Contenedor productivo Frontend React + Nginx
│   ├── docker-compose.yml          # Orquestación local (PostgreSQL 16 + Ollama + App)
│   └── cloudrun-service.yaml       # Manifiesto declarativo Knative / Cloud Run
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                 # Punto de entrada FastAPI + Middlewares + Routers
│   │   ├── core/
│   │   │   ├── config.py           # Configuración tipada con Pydantic Settings
│   │   │   ├── security.py         # JWT (HS256/RS256), hashing de contraseñas y RBAC
│   │   │   ├── observability.py    # Cloud Logging estructurado (JSON) y métricas
│   │   │   └── rate_limiter.py     # Sliding Window Rate Limiter (10 req/min/usuario)
│   │   ├── db/
│   │   │   ├── database.py         # Motor SQLAlchemy Async (Cloud SQL PostgreSQL / Fallback local)
│   │   │   ├── models.py           # Modelos ORM (Users, Sessions, Messages, Audit, MarketSeries)
│   │   │   ├── migrate.py          # Ejecutor de migraciones de esquema
│   │   │   └── seed.py             # Carga inicial de usuarios, políticas y series financieras
│   │   ├── models/
│   │   │   └── schemas.py          # Contratos Pydantic v2 segregados por rol (User vs Admin)
│   │   ├── services/
│   │   │   ├── circuit_breaker.py  # Circuit Breaker (CLOSED/OPEN/HALF_OPEN) + Backoff Vertex/Ollama
│   │   │   ├── financial_quant.py  # Motor cuantitativo, caché TTL y validador de calidad de datos
│   │   │   ├── audit_service.py    # Auditoría inmutable JSONL + Cadena SHA-256 + Exportador PDF/CSV
│   │   │   └── cost_analyzer.py    # Calculadora de costos en tiempo real y comparativa E6
│   │   ├── agent/
│   │   │   ├── tools.py            # Funciones decoradas con @tool (Políticas, Tickets, Acciones)
│   │   │   └── adk_agent.py        # Root Agent Google ADK con ciclo ReAct y Session Memory
│   │   └── api/
│   │       ├── auth_routes.py      # Endpoints de autenticación JWT
│   │       ├── chat_routes.py      # Endpoints de conversación multi-turno y sesiones
│   │       ├── admin_routes.py     # Endpoints de dashboard, costos E6, auditoría y exportación PDF/CSV
│   │       └── health_routes.py    # Endpoints /health/live, /health/ready y /health/db
│   └── tests/
│       ├── test_api.py             # Pruebas de endpoints, JWT RBAC, Rate Limit y exportación PDF/CSV
│       ├── test_agent_cb.py        # Pruebas del ciclo ReAct ADK y Circuit Breaker (Vertex -> Ollama)
│       └── test_quant_audit.py     # Pruebas de indicadores financieros, anomalías y cadena SHA-256
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── types/api.ts
        ├── services/apiClient.ts
        ├── styles/pixel-art.css    # Sistema de diseño Pixel Art accesible (WCAG AA)
        └── components/
            ├── PixelHeader.tsx
            ├── LoginScreen.tsx
            ├── ChatTerminal.tsx
            └── AdminCostDashboard.tsx
```

---

## ⚡ Inicio Rápido en Terminales Separadas

```bash
# 1. Clonar repositorio 
git clone https://github.com/arielo3202/Proyecto-Intengral-BSG.git

# 2. Crear el entorno virtual .venv (Python 3.14) 
make setup-venv
source .venv/bin/activate

# 3. Instalar dependencias y preparar la BD
make install
make db-up
make db-migrate
make seed

# 4. En la TERMINAL 1: Iniciar el Backend FastAPI + Google ADK Runner (Puerto 8000)
make run-backend

# 5. En la TERMINAL 2: Iniciar el Frontend React + Vite Pixel Art (Puerto 5173)
make run-frontend

# 6. En BASH: Realizar pruebas Unitarias, de Resilencia y Agente ADK, de Integración y Seguridad API
make test
```
