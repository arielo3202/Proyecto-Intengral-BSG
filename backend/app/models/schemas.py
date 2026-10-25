from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class LoginRequestDTO(BaseModel):
    email: str = Field(..., min_length=5, max_length=120, examples=["empleado@techcorp.latam"])
    password: str = Field(..., min_length=6, max_length=128, examples=["UserPixel2026!"])


class LoginResponseDTO(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str
    role: Literal["usuario", "admin"]
    department: str
    expires_in_seconds: int


class ChatMessageRequestDTO(BaseModel):
    session_id: str = Field(
        ...,
        min_length=4,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Identificador único de la sesión ADK multi-turno",
    )
    message: str = Field(
        ...,
        min_length=2,
        max_length=2500,
        description="Consulta del empleado sobre políticas, soporte TI o análisis bursátil",
    )
    preferred_tier: Literal["light", "pro"] = Field(
        default="light",
        description="Tier de modelo en Vertex AI (light=gemini-2.5-flash, pro=gemini-2.5-pro)",
    )


class UserChatResponseDTO(BaseModel):
    """
    DTO ESTRICTO PARA ROL 'usuario':
    Por requisito de negocio y seguridad, NO incluye tokens, latencias, proveedor LLM,
    traza ReAct, hashes de auditoría ni costos.
    """

    session_id: str
    reply: str
    timestamp: str
    remaining_requests_minute: int


class TechnicalTelemetryDTO(BaseModel):
    """Bloque técnico exclusivo para el Rol 'admin'."""

    llm_provider: str
    llm_model: str
    circuit_breaker_state: str
    fallback_triggered: bool
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    latency_ms: float
    react_steps: list[dict[str, Any]]
    audit_record_hash: str


class AdminChatResponseDTO(UserChatResponseDTO):
    """DTO extendido que se retorna ÚNICAMENTE cuando el JWT posee role == 'admin'."""

    technical_telemetry: TechnicalTelemetryDTO


class CircuitBreakerToggleDTO(BaseModel):
    target_state: Literal["CLOSED", "OPEN", "HALF_OPEN"]
    reason: str = Field(default="Simulación operativa desde Dashboard Admin", max_length=200)
