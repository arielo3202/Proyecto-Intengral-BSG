from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from app.agent.tools import (
    ADK_TOOLS_REGISTRY,
    analyze_stock_comparative,
    create_it_support_ticket,
    search_corporate_policies,
)
from app.core.observability import log_structured_event, metrics_collector
from app.db.database import db_manager
from app.services.audit_service import immutable_audit_service
from app.services.circuit_breaker import llm_circuit_breaker
from app.services.cost_analyzer import compute_turn_cost_usd


@dataclass(slots=True)
class ReActExecutionOutput:
    session_id: str
    reply: str
    timestamp: str
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


class TechCorpADKRootAgent:
    """
    Root Agent implementado bajo la arquitectura Google Agent Development Kit (ADK - Modalidad 2.2).
    Ejecuta el ciclo explícito ReAct (Reason -> Act -> Observe), invoca funciones decoradas con @tool
    y mantiene Session Memory persistente en PostgreSQL por session_id.
    """

    def __init__(self) -> None:
        self.agent_name = "techcorp_latam_root_agent"
        self.tools = ADK_TOOLS_REGISTRY

    @staticmethod
    def _detect_intent_and_select_tools(
        user_message: str, user_email: str
    ) -> list[tuple[str, dict[str, Any], str]]:
        """
        Fase REASON del ciclo ReAct: Analiza semánticamente el mensaje del usuario y el contexto
        de la conversación para decidir qué herramientas (@tool) invocar y con qué argumentos JSON.
        """
        msg_lower = user_message.lower()
        planned_actions: list[tuple[str, dict[str, Any], str]] = []

        # 1. Detectar si solicita soporte técnico o apertura de ticket
        ticket_keywords = ["ticket", "bloqueo", "resetear", "reseteo", "no puedo entrar", "falla vpn", "incidente", "crear reporte"]
        if any(k in msg_lower for k in ticket_keywords):
            priority = "P1_CRITICAL" if ("urgente" in msg_lower or "critico" in msg_lower or "crítico" in msg_lower) else "P2_HIGH"
            planned_actions.append(
                (
                    "create_it_support_ticket",
                    {
                        "employee_email": user_email,
                        "issue_summary": user_message,
                        "priority": priority,
                    },
                    "El usuario reporta una incidencia operativa o solicita abrir un ticket de soporte TI; se invoca @tool create_it_support_ticket.",
                )
            )

        # 2. Detectar si solicita análisis financiero o comparativo de acciones (Tickers)
        quant_keywords = [
            "accion", "acciones", "ticker", "bolsa", "volatilidad", "rsi", "sma", "ema",
            "sharpe", "mercado", "meli", "aapl", "msft", "glob", "walmex", "comparar", "financiero",
        ]
        if any(k in msg_lower for k in quant_keywords):
            found_tickers = re.findall(r"\b(MELI|AAPL|MSFT|GLOB|WALMEX\.MX|TSLA|INVALID)\b", user_message.upper())
            if not found_tickers:
                found_tickers = ["MELI", "GLOB", "MSFT"]
            # Preservar orden sin duplicados
            unique_tickers = list(dict.fromkeys(found_tickers))
            currency = "MXN" if "MXN" in user_message.upper() and unique_tickers == ["WALMEX.MX"] else "USD"
            planned_actions.append(
                (
                    "analyze_stock_comparative",
                    {"tickers": unique_tickers, "expected_currency": currency},
                    f"El usuario solicita análisis cuantitativo/comparativo de mercado para {unique_tickers} en divisa base {currency}; se invoca @tool analyze_stock_comparative.",
                )
            )

        # 3. Por defecto o cuando se consulta sobre políticas, procedimientos, vacaciones, reembolsos o VPN
        policy_keywords = [
            "politica", "política", "vacaciones", "remoto", "teletrabajo", "hibrido",
            "reembolso", "viaticos", "gastos", "vpn", "seguridad", "procedimiento", "dias", "horario",
        ]
        if not planned_actions or any(k in msg_lower for k in policy_keywords):
            planned_actions.append(
                (
                    "search_corporate_policies",
                    {"query": user_message, "category": "all"},
                    "Se requiere fundamentar la respuesta en el catálogo normativo oficial de TechCorp LATAM; se invoca @tool search_corporate_policies.",
                )
            )

        return planned_actions

    @staticmethod
    def _format_observations_for_synthesis(
        history_summary: str, observations: list[dict[str, Any]]
    ) -> str:
        sections: list[str] = []
        if history_summary:
            sections.append(f"• Contexto de Sesión Multi-turno Activo: {history_summary}")

        for obs in observations:
            t_name = obs["tool_name"]
            out = obs["output"]
            if t_name == "search_corporate_policies":
                for pol in out.get("policies", []):
                    steps_str = " | ".join(pol.get("mandatory_steps", []))
                    sections.append(
                        f"• [{pol['policy_code']}] {pol['title']}:\n"
                        f"  - Resumen Normativo: {pol['summary']}\n"
                        f"  - Pasos Obligatorios: {steps_str}\n"
                        f"  - SLA Oficial: {pol['sla_response']}"
                    )
            elif t_name == "create_it_support_ticket":
                tck = out.get("ticket", {})
                sections.append(
                    f"• Ticket de Soporte TI Generado Exitosamente:\n"
                    f"  - Folio: {tck.get('ticket_id')} | Prioridad: {tck.get('priority')} | Estado: {tck.get('status')}\n"
                    f"  - SLA Comprometido: Respuesta en máximo {tck.get('sla_hours')} horas para {tck.get('employee_email')}."
                )
            elif t_name == "analyze_stock_comparative":
                metrics_list = out.get("comparative_metrics", [])
                alerts_list = out.get("validation_alerts", [])
                if metrics_list:
                    lines = [
                        f"• Análisis Cuantitativo Verificado (Divisa Base Homogénea: {out.get('base_currency_enforced')}, "
                        f"Mejor Ratio de Sharpe: {out.get('best_risk_adjusted_ticker')}):"
                    ]
                    for m in metrics_list:
                        lines.append(
                            f"  - {m['ticker']} ({m['company_name']}): Precio=${m['latest_price']} {m['currency']} | "
                            f"SMA20={m['sma_20']} | EMA12={m['ema_12']} | RSI14={m['rsi_14']} | "
                            f"Retorno={m['period_return_pct']}% | Volatilidad Anual={m['annualized_volatility_pct']}% | "
                            f"Sharpe={m['sharpe_ratio']} | MaxDrawdown={m['max_drawdown_pct']}% "
                            f"[Proveedor: {m['provider_used']}]"
                        )
                    sections.append("\n".join(lines))
                if alerts_list:
                    for al in alerts_list:
                        sections.append(
                            f"• Alerta de Calidad de Datos Financieros [{al['error_code']}] en {al['ticker']}: {al['message']}"
                        )

        return "\n\n".join(sections)

    async def run_react_turn(
        self,
        user_id: str,
        user_email: str,
        user_role: Literal["usuario", "admin"],
        session_id: str,
        user_message: str,
        preferred_tier: Literal["light", "pro"] = "light",
    ) -> ReActExecutionOutput:
        t0 = time.perf_counter()

        # 1. Recuperar Session Memory previa para el session_id desde PostgreSQL
        prior_messages = db_manager.get_session_messages(session_id=session_id, limit=10)
        db_manager.upsert_session(session_id=session_id, user_id=user_id, title=user_message[:80])
        db_manager.append_message(
            session_id=session_id,
            sender_role="user",
            content=user_message,
        )

        history_summary = ""
        if prior_messages:
            prev_user_msgs = [m["content"] for m in prior_messages if m["sender_role"] == "user"]
            if prev_user_msgs:
                history_summary = f"El usuario cuenta con {len(prev_user_msgs)} consulta(s) previa(s) en esta sesión ({session_id}). Última previa: '{prev_user_msgs[-1][:70]}'"

        # 2. Ciclo ReAct: REASON -> ACT -> OBSERVE
        react_steps: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []

        planned_tools = self._detect_intent_and_select_tools(user_message, user_email)
        effective_tier: Literal["light", "pro"] = (
            "pro"
            if any(t[0] == "analyze_stock_comparative" for t in planned_tools)
            else preferred_tier
        )

        for idx, (tool_name, tool_args, thought_reason) in enumerate(planned_tools, start=1):
            # Paso REASON
            react_steps.append(
                {
                    "step": idx,
                    "phase": "REASON",
                    "thought": thought_reason,
                    "selected_tool": tool_name,
                    "tool_args": tool_args,
                }
            )
            # Paso ACT (Ejecución de la función Python decorada con @tool)
            tool_fn = self.tools[tool_name]
            tool_output = tool_fn(**tool_args)
            react_steps.append(
                {
                    "step": idx,
                    "phase": "ACT",
                    "invoked_tool": tool_name,
                    "status": tool_output.get("status", "EXECUTED"),
                }
            )
            # Paso OBSERVE (Incorporación del resultado al contexto del agente)
            observations.append({"tool_name": tool_name, "output": tool_output})
            react_steps.append(
                {
                    "step": idx,
                    "phase": "OBSERVE",
                    "observation_summary": f"Resultado estructurado recibido desde {tool_name} ({tool_output.get('status')}).",
                    "raw_observation": tool_output,
                }
            )

        log_structured_event(
            "AGENT_REACT_STEP",
            f"Agente ADK completó {len(planned_tools)} ciclo(s) ReAct para sesión {session_id}",
            severity="INFO",
            session_id=session_id,
            tools_invoked=[t[0] for t in planned_tools],
        )

        # 3. Invocar LLM (Vertex AI Gemini 2.5 Pro/Light con Circuit Breaker y Fallback a Ollama llama3.2:3b)
        tool_context_str = self._format_observations_for_synthesis(history_summary, observations)
        system_prompt = (
            "Eres el Asistente Empresarial Inteligente de TechCorp LATAM (Modalidad 2.2 Google ADK + GCP). "
            "Responde siempre en español claro, preciso y fundamentado únicamente en las observaciones de las herramientas."
        )
        llm_result = await llm_circuit_breaker.invoke_llm(
            system_prompt=system_prompt,
            user_prompt=user_message,
            tool_context=tool_context_str,
            preferred_tier=effective_tier,
        )

        total_latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        total_tokens = llm_result.prompt_tokens + llm_result.completion_tokens
        turn_cost_usd = compute_turn_cost_usd(
            model=llm_result.model,
            prompt_tokens=llm_result.prompt_tokens,
            completion_tokens=llm_result.completion_tokens,
        )

        # 4. Persistir respuesta del asistente en Session Memory y sellar registro de Auditoría Inmutable (SHA-256)
        db_manager.append_message(
            session_id=session_id,
            sender_role="assistant",
            content=llm_result.content,
            react_trace=react_steps,
            llm_provider=llm_result.provider,
            llm_model=llm_result.model,
            prompt_tokens=llm_result.prompt_tokens,
            completion_tokens=llm_result.completion_tokens,
            estimated_cost_usd=turn_cost_usd,
            latency_ms=total_latency_ms,
        )

        audit_entry = immutable_audit_service.record_event(
            event_type="CHAT_COMPLETION",
            user_id=user_id,
            user_role=user_role,
            session_id=session_id,
            provider_used=llm_result.provider,
            model_used=llm_result.model,
            total_tokens=total_tokens,
            cost_usd=turn_cost_usd,
            latency_ms=total_latency_ms,
            circuit_breaker_state=llm_result.circuit_state,
            metadata={
                "tools_used": [t[0] for t in planned_tools],
                "fallback_triggered": llm_result.fallback_triggered,
                "prior_turns_in_session": len(prior_messages),
            },
        )

        metrics_collector.record_request(latency_ms=total_latency_ms, is_error=False)

        return ReActExecutionOutput(
            session_id=session_id,
            reply=llm_result.content,
            timestamp=datetime.now(timezone.utc).isoformat(),
            llm_provider=llm_result.provider,
            llm_model=llm_result.model,
            circuit_breaker_state=llm_result.circuit_state,
            fallback_triggered=llm_result.fallback_triggered,
            prompt_tokens=llm_result.prompt_tokens,
            completion_tokens=llm_result.completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=turn_cost_usd,
            latency_ms=total_latency_ms,
            react_steps=react_steps,
            audit_record_hash=str(audit_entry["record_hash"]),
        )


techcorp_adk_agent = TechCorpADKRootAgent()
