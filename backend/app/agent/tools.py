from __future__ import annotations

import uuid
from functools import wraps
from typing import Any, Callable

from app.db.database import db_manager
from app.services.financial_quant import FinancialDataError, quant_market_service

# Registro global de herramientas invocables por el Root Agent de Google ADK
ADK_TOOLS_REGISTRY: dict[str, Callable[..., dict[str, Any]]] = {}


def tool(func: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    """
    Decorador oficial @tool compatible con Google Agent Development Kit (ADK).
    Registra metadatos de inspección, nombre, docstring y argumentos JSON para el ciclo ReAct.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return func(*args, **kwargs)

    setattr(wrapper, "_is_adk_tool", True)
    setattr(wrapper, "_tool_name", func.__name__)
    setattr(wrapper, "_tool_description", (func.__doc__ or "").strip())
    ADK_TOOLS_REGISTRY[func.__name__] = wrapper
    return wrapper


# Base de conocimiento oficial de Políticas, Procedimientos y Soporte TI de TechCorp LATAM
CORPORATE_POLICIES_KB: list[dict[str, Any]] = [
    {
        "policy_code": "POL-HR-001",
        "title": "Política de Trabajo Híbrido, Remoto y Horarios Flexibles LATAM",
        "category": "rrhh",
        "keywords": ["remoto", "teletrabajo", "hibrido", "home office", "horario", "oficina", "dias"],
        "summary": (
            "Los 800 colaboradores de TechCorp LATAM cuentan con esquema híbrido 3x2 "
            "(hasta 3 días de trabajo remoto y 2 presenciales por semana) o 100% remoto previa "
            "aprobación de Ingeniería/Operaciones. El núcleo de disponibilidad sincrónica es de "
            "10:00 a 16:00 (hora local de cada sede: CDMX, Bogotá, Santiago, Buenos Aires, Lima)."
        ),
        "mandatory_steps": [
            "Registrar los días de teletrabajo en el portal Workday antes del viernes a las 17:00.",
            "Conectarse obligatoriamente mediante FortiClient/WireGuard Zero-Trust VPN al acceder a entornos GCP.",
            "Solicitar bono mensual de conectividad e internet ($45 USD) vía centro de costos RRHH-LATAM.",
        ],
        "sla_response": "Aprobación automática por líder directo en < 24 horas hábiles.",
    },
    {
        "policy_code": "POL-HR-002",
        "title": "Política de Vacaciones, Días Personales y Licencias Remuneradas",
        "category": "vacaciones",
        "keywords": ["vacaciones", "feriado", "permiso", "licencia", "dias libres", "descanso"],
        "summary": (
            "Todo empleado de TechCorp LATAM dispone de 15 días hábiles de vacaciones anuales "
            "desde el primer año (incrementando 2 días por cada año adicional hasta 25 días), "
            "más 4 'TechCorp Wellness Days' de libre disposición al año."
        ),
        "mandatory_steps": [
            "Solicitar vacaciones con mínimo 10 días hábiles de anticipación en el módulo de Capital Humano.",
            "Designar un par de respaldo (backup) para guardias de producción o proyectos activos.",
            "Recibir confirmación firmada digitalmente por el Engineering Manager o Product Owner.",
        ],
        "sla_response": "Resolución máxima en 48 horas hábiles.",
    },
    {
        "policy_code": "POL-FIN-003",
        "title": "Procedimiento de Reembolsos, Viáticos y Gastos Corporativos",
        "category": "finanzas",
        "keywords": ["reembolso", "viaticos", "gastos", "factura", "viaje", "certificacion", "curso"],
        "summary": (
            "TechCorp LATAM reembolsa gastos de viajes de negocio, certificaciones Google Cloud / AWS "
            "(hasta $1,200 USD/año por empleado) y equipamiento ergonómico autorizado. "
            "Todo comprobante fiscal (CFDI en México, Factura Electrónica DIAN en Colombia, Boleta/Factura SII en Chile) "
            "debe cargarse dentro de los primeros 15 días naturales posteriores al gasto."
        ),
        "mandatory_steps": [
            "Adjuntar XML y PDF del comprobante fiscal válido junto con el código de proyecto.",
            "Para montos mayores a $300 USD se requiere pre-aprobación del Director de Área.",
            "El depósito se liquida en la moneda local de nómina en el siguiente ciclo quincenal.",
        ],
        "sla_response": "Liquidación contable en 5 a 7 días hábiles tras validación fiscal.",
    },
    {
        "policy_code": "POL-SEC-004",
        "title": "Protocolo de Seguridad de la Información, Credenciales, VPN y Soporte Técnico TI",
        "category": "soporte_ti",
        "keywords": ["vpn", "password", "contraseña", "acceso", "bloqueo", "mfa", "token", "laptop", "soporte", "incidente", "error"],
        "summary": (
            "El acceso a repositorios, Cloud Console y bases de datos exige autenticación multifactor "
            "(MFA FIDO2/Passkey) y rotación de llaves cada 90 días. Está estrictamente prohibido almacenar "
            "secretos o API Keys en código fuente; todo secreto debe residir en Google Cloud Secret Manager."
        ),
        "mandatory_steps": [
            "En caso de bloqueo de MFA o pérdida de equipo, reportar inmediatamente al SOC interno (Severidad P1).",
            "Para reseteo de credenciales de desarrollo o permisos IAM en GCP, generar ticket con la herramienta create_it_support_ticket.",
            "Todo equipo corporativo debe mantener cifrado FileVault/BitLocker activo y agente EDR CrowdStrike en ejecución.",
        ],
        "sla_response": "Incidentes Críticos (P1): 15 min | Alta (P2): 2 horas | Normal (P3): 8 horas.",
    },
]


@tool
def search_corporate_policies(query: str, category: str = "all") -> dict[str, Any]:
    """
    Tool #1 (@tool): Busca políticas internas, procedimientos normativos y guías de soporte técnico
    en la base de conocimiento oficial de TechCorp LATAM.
    """
    q_lower = query.lower()
    cat_lower = category.lower().strip()
    matches: list[dict[str, Any]] = []

    for policy in CORPORATE_POLICIES_KB:
        score = 0
        if cat_lower != "all" and cat_lower in policy["category"]:
            score += 3
        for kw in policy["keywords"]:
            if kw in q_lower:
                score += 2
        if any(word in policy["title"].lower() or word in policy["summary"].lower() for word in q_lower.split() if len(word) > 3):
            score += 1
        if score > 0:
            matches.append({**policy, "relevance_score": score})

    matches.sort(key=lambda x: int(x["relevance_score"]), reverse=True)
    if not matches:
        matches = CORPORATE_POLICIES_KB[:2]

    return {
        "tool_name": "search_corporate_policies",
        "status": "SUCCESS",
        "matched_count": len(matches),
        "policies": matches[:2],
    }


@tool
def create_it_support_ticket(
    employee_email: str,
    issue_summary: str,
    priority: str = "P2_HIGH",
) -> dict[str, Any]:
    """
    Tool #2 (@tool): Crea un ticket formal y auditable de Soporte Técnico TI / SecOps en PostgreSQL
    asignando código de seguimiento y SLA según prioridad.
    """
    norm_priority = priority.upper().strip()
    sla_map = {"P1_CRITICAL": 1, "P2_HIGH": 4, "P3_NORMAL": 12}
    if norm_priority not in sla_map:
        norm_priority = "P2_HIGH"

    ticket_id = f"TCK-{uuid.uuid4().hex[:8].upper()}"
    record = db_manager.create_support_ticket(
        ticket_id=ticket_id,
        employee_email=employee_email,
        issue_summary=issue_summary[:300],
        priority=norm_priority,
        sla_hours=sla_map[norm_priority],
    )
    return {
        "tool_name": "create_it_support_ticket",
        "status": "TICKET_CREATED",
        "ticket": record,
    }


@tool
def analyze_stock_comparative(
    tickers: list[str],
    expected_currency: str = "USD",
) -> dict[str, Any]:
    """
    Tool #3 (@tool): Ejecuta análisis cuantitativo y comparativo de acciones (SMA-20, EMA-12, RSI-14,
    Volatilidad Anualizada, Sharpe Ratio y Max Drawdown) validando frescura, moneda y anomalías.
    """
    clean_list = [t.strip().upper() for t in tickers if t.strip()] or ["MELI", "GLOB"]
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for sym in clean_list:
        try:
            series = quant_market_service.fetch_and_validate_series(
                ticker=sym, expected_currency=expected_currency
            )
            indicators = quant_market_service.compute_indicators(series)
            results.append(indicators)
        except FinancialDataError as fde:
            errors.append({"ticker": sym, "error_code": fde.code, "message": fde.message})

    best_sharpe_ticker = None
    if results:
        best = max(results, key=lambda item: float(item["sharpe_ratio"]))
        best_sharpe_ticker = best["ticker"]

    return {
        "tool_name": "analyze_stock_comparative",
        "status": "SUCCESS" if results else "VALIDATION_REJECTED",
        "base_currency_enforced": expected_currency.upper(),
        "best_risk_adjusted_ticker": best_sharpe_ticker,
        "comparative_metrics": results,
        "validation_alerts": errors,
    }
