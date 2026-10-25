from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response

from app.agent.adk_agent import techcorp_adk_agent
from app.core.rate_limiter import user_rate_limiter
from app.core.security import AuthenticatedUser, get_current_user
from app.db.database import db_manager
from app.models.schemas import (
    AdminChatResponseDTO,
    ChatMessageRequestDTO,
    TechnicalTelemetryDTO,
    UserChatResponseDTO,
)

router = APIRouter(prefix="/api/v1/chat", tags=["Chat Multi-Turno (Google ADK ReAct)"])


@router.post(
    "/message",
    response_model=AdminChatResponseDTO | UserChatResponseDTO,
    summary="Procesa un mensaje multi-turno con Google ADK segregando la salida según el Rol JWT",
)
async def send_chat_message(
    payload: ChatMessageRequestDTO,
    response: Response,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AdminChatResponseDTO | UserChatResponseDTO:
    # 1. Aplicar Rate Limiting estricto: 10 requests/minuto por usuario
    rl_status = user_rate_limiter.check_and_consume(current_user.user_id)
    response.headers["X-RateLimit-Limit"] = str(rl_status.limit)
    response.headers["X-RateLimit-Remaining"] = str(rl_status.remaining)

    # 2. Ejecutar el Root Agent de Google ADK (Reason -> Act -> Observe)
    result = await techcorp_adk_agent.run_react_turn(
        user_id=current_user.user_id,
        user_email=current_user.email,
        user_role=current_user.role,
        session_id=payload.session_id,
        user_message=payload.message,
        preferred_tier=payload.preferred_tier,
    )

    # 3. Segregación estricta por rol:
    # Si el rol es 'usuario', JAMÁS se devuelve información técnica, tokens, latencias ni costos.
    if current_user.role == "usuario":
        return UserChatResponseDTO(
            session_id=result.session_id,
            reply=result.reply,
            timestamp=result.timestamp,
            remaining_requests_minute=rl_status.remaining,
        )

    # Si el rol es 'admin', se incluye la telemetría completa del ciclo ReAct y auditoría.
    return AdminChatResponseDTO(
        session_id=result.session_id,
        reply=result.reply,
        timestamp=result.timestamp,
        remaining_requests_minute=rl_status.remaining,
        technical_telemetry=TechnicalTelemetryDTO(
            llm_provider=result.llm_provider,
            llm_model=result.llm_model,
            circuit_breaker_state=result.circuit_breaker_state,
            fallback_triggered=result.fallback_triggered,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            estimated_cost_usd=result.estimated_cost_usd,
            latency_ms=result.latency_ms,
            react_steps=result.react_steps,
            audit_record_hash=result.audit_record_hash,
        ),
    )


@router.get("/sessions/{session_id}")
async def get_session_history(
    session_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    raw_messages = db_manager.get_session_messages(session_id=session_id, limit=30)
    sanitized_messages: list[dict[str, Any]] = []
    for m in raw_messages:
        if current_user.role == "usuario":
            # El rol 'usuario' solo ve el texto y el rol del emisor, nunca tokens ni costos
            sanitized_messages.append(
                {
                    "sender_role": m["sender_role"],
                    "content": m["content"],
                    "created_at": m["created_at"],
                }
            )
        else:
            sanitized_messages.append(m)

    return {
        "session_id": session_id,
        "message_count": len(sanitized_messages),
        "messages": sanitized_messages,
    }
