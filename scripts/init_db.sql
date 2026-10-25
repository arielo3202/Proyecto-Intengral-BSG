-- =============================================================================
-- TechCorp LATAM — Proyecto A: Esquema Relacional y de Series Temporales
-- Motor: Cloud SQL para PostgreSQL 16
-- =============================================================================

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    email VARCHAR(120) UNIQUE NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('usuario', 'admin')),
    department VARCHAR(60) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(160) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    sender_role VARCHAR(20) NOT NULL CHECK (sender_role IN ('user', 'assistant', 'tool')),
    content TEXT NOT NULL,
    react_trace JSONB,
    llm_provider VARCHAR(64),
    llm_model VARCHAR(64),
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    estimated_cost_usd NUMERIC(12, 6) DEFAULT 0.0,
    latency_ms NUMERIC(10, 2) DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created
    ON chat_messages (session_id, created_at ASC);

CREATE TABLE IF NOT EXISTS immutable_audit_logs (
    id BIGSERIAL PRIMARY KEY,
    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    user_role VARCHAR(20) NOT NULL,
    session_id VARCHAR(64) NOT NULL,
    provider_used VARCHAR(64) NOT NULL,
    model_used VARCHAR(64) NOT NULL,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd NUMERIC(12, 6) NOT NULL DEFAULT 0.0,
    latency_ms NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
    circuit_breaker_state VARCHAR(32) NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    prev_hash CHAR(64) NOT NULL,
    record_hash CHAR(64) UNIQUE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp_desc
    ON immutable_audit_logs (event_timestamp DESC, event_type);

CREATE TABLE IF NOT EXISTS market_instruments (
    ticker VARCHAR(16) PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    currency CHAR(3) NOT NULL,
    exchange VARCHAR(32) NOT NULL,
    adjustment_type VARCHAR(32) NOT NULL DEFAULT 'SPLIT_AND_DIVIDEND_ADJUSTED',
    license_source VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS market_timeseries (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(16) NOT NULL REFERENCES market_instruments(ticker) ON DELETE CASCADE,
    bar_timestamp TIMESTAMPTZ NOT NULL,
    open_price NUMERIC(18, 6) NOT NULL,
    high_price NUMERIC(18, 6) NOT NULL,
    low_price NUMERIC(18, 6) NOT NULL,
    close_price NUMERIC(18, 6) NOT NULL,
    volume BIGINT NOT NULL,
    currency CHAR(3) NOT NULL,
    source_provider VARCHAR(32) NOT NULL,
    is_anomaly_flagged BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (ticker, bar_timestamp)
);

CREATE INDEX IF NOT EXISTS idx_market_timeseries_ticker_ts
    ON market_timeseries (ticker, bar_timestamp DESC);
