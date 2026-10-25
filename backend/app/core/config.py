from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(slots=True)
class Settings:
    """Configuración centralizada y tipada del sistema (Cero secretos hardcodeados)."""

    app_name: str = "TechCorp LATAM — Asistente Empresarial Inteligente (ADK + GCP)"
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    app_version: str = field(default_factory=lambda: os.getenv("APP_VERSION", "1.0.0"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # Base de Datos (Cloud SQL PostgreSQL 16 + Fallback SQLite para pruebas locales sin Docker)
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://techcorp_user:techcorp_pass@localhost:5432/techcorp_adk",
        )
    )
    sqlite_fallback_path: str = field(
        default_factory=lambda: os.getenv("SQLITE_FALLBACK_PATH", "/tmp/techcorp_local.db")
    )

    # Autenticación JWT (Soporta HS256 y RS256)
    jwt_algorithm: str = field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))
    jwt_secret_key: str = field(
        default_factory=lambda: os.getenv(
            "JWT_SECRET_KEY",
            "TECHCORP_LATAM_DEV_ONLY_EPHEMERAL_KEY_REPLACE_VIA_GCP_SECRET_MANAGER_2026",
        )
    )
    jwt_public_key_pem: str = field(default_factory=lambda: os.getenv("JWT_PUBLIC_KEY_PEM", ""))
    jwt_private_key_pem: str = field(default_factory=lambda: os.getenv("JWT_PRIVATE_KEY_PEM", ""))
    jwt_expire_minutes: int = field(
        default_factory=lambda: int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    )

    # CORS Restrictivo
    cors_allowed_origins: list[str] = field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv(
                "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
            ).split(",")
            if origin.strip()
        ]
    )

    # Rate Limiting Estricto: 10 requests/minuto por usuario
    rate_limit_requests_per_minute: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "10"))
    )

    # Google Cloud Vertex AI (LLM Primario)
    gcp_project_id: str = field(default_factory=lambda: os.getenv("GCP_PROJECT_ID", "techcorp-latam-prod"))
    gcp_location: str = field(default_factory=lambda: os.getenv("GCP_LOCATION", "us-central1"))
    vertex_primary_model: str = field(
        default_factory=lambda: os.getenv("VERTEX_PRIMARY_MODEL", "gemini-2.5-pro")
    )
    vertex_light_model: str = field(
        default_factory=lambda: os.getenv("VERTEX_LIGHT_MODEL", "gemini-2.5-flash")
    )
    vertex_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("VERTEX_TIMEOUT_SECONDS", "12.0"))
    )

    # Ollama Local (LLM Fallback: llama3.2:3b)
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_fallback_model: str = field(
        default_factory=lambda: os.getenv("OLLAMA_FALLBACK_MODEL", "llama3.2:3b")
    )
    ollama_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "15.0"))
    )

    # Circuit Breaker
    cb_failure_threshold: int = field(
        default_factory=lambda: int(os.getenv("CB_FAILURE_THRESHOLD", "3"))
    )
    cb_recovery_timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("CB_RECOVERY_TIMEOUT_SECONDS", "45"))
    )

    # Auditoría Inmutable JSONL
    audit_jsonl_path: str = field(
        default_factory=lambda: os.getenv("AUDIT_JSONL_PATH", "/tmp/immutable_audit_trail.jsonl")
    )

    # Caché y Calidad de Datos Financieros
    market_cache_ttl_open_seconds: int = field(
        default_factory=lambda: int(os.getenv("MARKET_CACHE_TTL_OPEN_SECONDS", "60"))
    )
    market_cache_ttl_closed_seconds: int = field(
        default_factory=lambda: int(os.getenv("MARKET_CACHE_TTL_CLOSED_SECONDS", "900"))
    )
    max_data_staleness_seconds: int = field(
        default_factory=lambda: int(os.getenv("MAX_DATA_STALENESS_SECONDS", "86400"))
    )


settings = Settings()
