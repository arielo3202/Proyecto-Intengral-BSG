from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response

from app.core.observability import metrics_collector
from app.core.security import AuthenticatedUser, require_admin_role
from app.models.schemas import CircuitBreakerToggleDTO
from app.services.audit_service import immutable_audit_service
from app.services.circuit_breaker import llm_circuit_breaker
from app.services.cost_analyzer import build_e6_cost_and_usage_analysis
from app.services.financial_quant import quant_market_service

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Administración, Auditoría Inmutable y Dashboard de Costos E6 (Solo Admin)"],
)


@router.get("/dashboard")
async def get_admin_dashboard(
    _admin: AuthenticatedUser = Depends(require_admin_role),
) -> dict[str, Any]:
    """
    Retorna el estado integral del sistema para el Dashboard Admin:
    - Estado del Circuit Breaker (Vertex AI vs Ollama llama3.2:3b)
    - Métricas de observabilidad y salud de proveedores
    - Análisis de Costos Mensual y Comparativa de Modalidades (Entregable E6 integrado)
    - Resumen de integridad de la cadena de auditoría SHA-256
    - Snapshot comparativo del motor cuantitativo financiero
    """
    cost_and_usage = build_e6_cost_and_usage_analysis()
    chain_integrity = immutable_audit_service.verify_chain_integrity()
    recent_audit = immutable_audit_service.list_records(limit=25)

    market_snapshot = []
    for ticker in ("MELI", "GLOB", "AAPL", "MSFT"):
        series = quant_market_service.fetch_and_validate_series(ticker, "USD")
        market_snapshot.append(quant_market_service.compute_indicators(series))

    return {
        "circuit_breaker": llm_circuit_breaker.get_status(),
        "observability_metrics": metrics_collector.get_summary(),
        "cost_analysis_e6": cost_and_usage,
        "audit_integrity": chain_integrity,
        "recent_audit_logs": recent_audit,
        "quantitative_market_snapshot": market_snapshot,
    }


@router.post("/circuit-breaker/toggle")
async def toggle_circuit_breaker(
    payload: CircuitBreakerToggleDTO,
    admin_user: AuthenticatedUser = Depends(require_admin_role),
) -> dict[str, Any]:
    new_status = llm_circuit_breaker.force_state(
        target_state=payload.target_state,
        reason=f"{payload.reason} (Acción por {admin_user.email})",
    )
    immutable_audit_service.record_event(
        event_type="CIRCUIT_BREAKER_MANUAL_OVERRIDE",
        user_id=admin_user.user_id,
        user_role=admin_user.role,
        session_id="admin-control-plane",
        provider_used="control_plane",
        model_used="n/a",
        total_tokens=0,
        cost_usd=0.0,
        latency_ms=1.0,
        circuit_breaker_state=payload.target_state,
        metadata={"reason": payload.reason},
    )
    return new_status


@router.get("/audit")
async def list_immutable_audit_logs(
    limit: int = 50,
    _admin: AuthenticatedUser = Depends(require_admin_role),
) -> dict[str, Any]:
    return {
        "integrity": immutable_audit_service.verify_chain_integrity(),
        "records": immutable_audit_service.list_records(limit=min(limit, 250)),
    }


@router.get("/export/csv")
async def export_audit_and_metrics_csv(
    _admin: AuthenticatedUser = Depends(require_admin_role),
) -> Response:
    """Descarga en formato CSV todos los registros de auditoría inmutable y costos."""
    csv_bytes = immutable_audit_service.export_csv_bytes()
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="techcorp_latam_audit_metrics.csv"'
        },
    )


@router.get("/export/pdf")
async def export_audit_and_metrics_pdf(
    _admin: AuthenticatedUser = Depends(require_admin_role),
) -> Response:
    """Descarga en formato PDF el reporte ejecutivo de auditoría inmutable (SHA-256) y análisis de costos E6."""
    cost_summary = build_e6_cost_and_usage_analysis()
    pdf_bytes = immutable_audit_service.export_pdf_bytes(cost_summary=cost_summary)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="techcorp_latam_audit_cost_report_e6.pdf"'
        },
    )
