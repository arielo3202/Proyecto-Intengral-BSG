# Modelo de Datos Relacional y de Series Temporales (`DATA_MODEL.md`)
**Rol Responsable:** Database Architect & Financial Data Engineer  
**Motor Principal:** Cloud SQL para PostgreSQL 16 (con soporte de fallback local asíncrono para pruebas aisladas)

---

## 1. Diagrama Entidad-Relación (MER) en Mermaid

```mermaid
erDiagram
    USERS ||--o{ CHAT_SESSIONS : "posee"
    USERS ||--o{ IMMUTABLE_AUDIT_LOGS : "genera"
    CHAT_SESSIONS ||--o{ CHAT_MESSAGES : "contiene"
    CHAT_SESSIONS ||--o{ IMMUTABLE_AUDIT_LOGS : "traza"
    MARKET_INSTRUMENTS ||--o{ MARKET_TIMESERIES : "registra_precios"

    USERS {
        varchar(64) id PK "UUID v4 del empleado"
        varchar(120) email UK "Correo corporativo @techcorp.latam"
        varchar(120) full_name "Nombre completo"
        varchar(255) password_hash "Hash Argon2 / PBKDF2-SHA256"
        varchar(20) role "ENUM: usuario | admin"
        varchar(60) department "Departamento (TI, Finanzas, RRHH)"
        boolean is_active "Estado de la cuenta"
        timestamptz created_at "Fecha de alta"
    }

    CHAT_SESSIONS {
        varchar(64) session_id PK "ID de sesión ADK"
        varchar(64) user_id FK "Propietario de la sesión"
        varchar(160) title "Título resumido de la conversación"
        timestamptz created_at "Inicio de sesión"
        timestamptz updated_at "Última interacción"
    }

    CHAT_MESSAGES {
        bigserial id PK "Secuencia ordenada"
        varchar(64) session_id FK "Sesión asociada"
        varchar(20) sender_role "user | assistant | tool"
        text content "Contenido textual del mensaje"
        jsonb react_trace "Pasos ReAct (Reason/Act/Observe) - Solo visible a Admin"
        varchar(64) llm_provider "vertex_ai | ollama_fallback"
        varchar(64) llm_model "gemini-2.5-flash | gemini-2.5-pro | llama3.2:3b"
        integer prompt_tokens "Tokens de entrada"
        integer completion_tokens "Tokens de salida"
        numeric(12,6) estimated_cost_usd "Costo calculado del turno"
        numeric(10,2) latency_ms "Tiempo de respuesta en ms"
        timestamptz created_at "Timestamp UTC"
    }

    IMMUTABLE_AUDIT_LOGS {
        bigserial id PK "Secuencia inmutable"
        timestamptz event_timestamp "Timestamp UTC exacto"
        varchar(64) event_type "CHAT_COMPLETION | CIRCUIT_BREAKER | RATE_LIMIT | AUTH"
        varchar(64) user_id FK "ID del usuario actor"
        varchar(20) user_role "usuario | admin"
        varchar(64) session_id "ID de sesión ADK"
        varchar(64) provider_used "Proveedor ejecutado"
        varchar(64) model_used "Modelo ejecutado"
        integer total_tokens "Total de tokens consumidos"
        numeric(12,6) cost_usd "Costo USD imputado"
        numeric(10,2) latency_ms "Latencia registrada"
        varchar(32) circuit_breaker_state "CLOSED | OPEN | HALF_OPEN"
        jsonb metadata_json "Metadatos sanitizados (sin secretos)"
        char(64) prev_hash "Hash SHA-256 del registro N-1"
        char(64) record_hash UK "Hash SHA-256 criptográfico del registro N"
    }

    MARKET_INSTRUMENTS {
        varchar(16) ticker PK "Símbolo bursátil (ej. MELI, AAPL, MSFT)"
        varchar(120) name "Razón social del emisor"
        char(3) currency "Divisa ISO-4217 (USD, MXN, BRL)"
        varchar(32) exchange "Bolsa de valores (NASDAQ, NYSE, BMV)"
        varchar(32) adjustment_type "SPLIT_AND_DIVIDEND_ADJUSTED"
        varchar(64) license_source "Proveedor autoritativo"
    }

    MARKET_TIMESERIES {
        bigserial id PK
        varchar(16) ticker FK
        timestamptz bar_timestamp "Fecha/hora del corte"
        numeric(18,6) open_price
        numeric(18,6) high_price
        numeric(18,6) low_price
        numeric(18,6) close_price
        bigint volume
        char(3) currency "Moneda validada"
        varchar(32) source_provider "Proveedor que originó el dato"
        boolean is_anomaly_flagged "Bandera de Z-score > 3.5"
    }
```

---

## 2. Índices y Optimización de Consultas en PostgreSQL

1. `idx_chat_messages_session_created`: `CREATE INDEX ON chat_messages (session_id, created_at ASC);` — Permite reconstruir la ventana de memoria del agente ADK en $< 2\text{ ms}$.
2. `idx_audit_logs_timestamp_desc`: `CREATE INDEX ON immutable_audit_logs (event_timestamp DESC, event_type);` — Optimiza la paginación del visor de auditoría y las exportaciones CSV/PDF del Administrador.
3. `idx_market_timeseries_ticker_ts`: `CREATE UNIQUE INDEX ON market_timeseries (ticker, bar_timestamp DESC);` — Índice compuesto tipo B-Tree descendente para cálculo vectorizado de SMA, EMA, RSI y volatilidad histórica sin *full table scans*.
