from __future__ import annotations

from typing import Any
from fastapi import APIRouter

from app.core.observability import metrics_collector
from app.db.database import db_manager
from app.services.circuit_breaker import llm_circuit_breaker
from app.services.financial_quant import quant_market_service

router = APIRouter(prefix="/health", tags=["Observabilidad y Health Checks"])


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """Comprueba que el proceso ASGI Python 3.14 está activo."""
    return {"status": "alive", "service": "techcorp-asistente-adk"}


@router.get("/ready")
async def readiness_check() -> dict[str, Any]:
    """Comprueba preparación del servicio, estado de degradación del Circuit Breaker y proveedores financieros."""
    cb = llm_circuit_breaker.get_status()
    db_state = db_manager.check_health()
    degraded = cb["state"] == "OPEN" or quant_market_service.simulate_primary_provider_down
    return {
        "status": "degraded_using_fallback" if degraded else "ready",
        "circuit_breaker_state": cb["state"],
        "financial_primary_provider_up": not quant_market_service.simulate_primary_provider_down,
        "database": db_state["status"],
        "metrics_snapshot": metrics_collector.get_summary(),
    }


@router.get("/db")
async def database_connectivity_check() -> dict[str, Any]:
    """Verifica conectividad activa y latencia con PostgreSQL / motor relacional."""
    return db_manager.check_health()
