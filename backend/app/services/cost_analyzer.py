from __future__ import annotations

from typing import Any
from app.db.database import db_manager


# Precios Oficiales por 1 Millón de Tokens (USD)
MODEL_PRICING_PER_1M: dict[str, dict[str, float]] = {
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "gemini-2.5-pro": {"input": 1.25, "output": 5.00},
    "llama3.2:3b": {"input": 0.00, "output": 0.00},
}


def compute_turn_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING_PER_1M.get(model, MODEL_PRICING_PER_1M["gemini-2.5-flash"])
    cost = (prompt_tokens / 1_000_000.0) * pricing["input"] + (
        completion_tokens / 1_000_000.0
    ) * pricing["output"]
    return round(cost, 6)


def build_e6_cost_and_usage_analysis() -> dict[str, Any]:
    """
    Construye el Análisis de Costos Mensual (Entregable E6 Integrado) y el consumo acumulado
    en tiempo real desde PostgreSQL para ser graficado directamente en el Dashboard Admin Pixel Art.
    """
    with db_manager._get_conn() as conn:
        agg = conn.execute(
            """
            SELECT
                COUNT(*) AS total_turns,
                COALESCE(SUM(prompt_tokens), 0) AS sum_prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) AS sum_completion_tokens,
                COALESCE(SUM(estimated_cost_usd), 0.0) AS sum_cost_usd,
                COALESCE(AVG(latency_ms), 0.0) AS avg_latency_ms
            FROM chat_messages
            WHERE sender_role = 'assistant'
            """
        ).fetchone()

        by_model_rows = conn.execute(
            """
            SELECT
                llm_model,
                llm_provider,
                COUNT(*) AS calls,
                COALESCE(SUM(prompt_tokens + completion_tokens), 0) AS tokens,
                COALESCE(SUM(estimated_cost_usd), 0.0) AS cost_usd,
                COALESCE(AVG(latency_ms), 0.0) AS avg_latency_ms
            FROM chat_messages
            WHERE sender_role = 'assistant'
            GROUP BY llm_model, llm_provider
            """
        ).fetchall()

    realtime_usage = {
        "total_assistant_turns": int(agg["total_turns"]) if agg else 0,
        "prompt_tokens": int(agg["sum_prompt_tokens"]) if agg else 0,
        "completion_tokens": int(agg["sum_completion_tokens"]) if agg else 0,
        "total_tokens": (int(agg["sum_prompt_tokens"]) + int(agg["sum_completion_tokens"])) if agg else 0,
        "accumulated_cost_usd": round(float(agg["sum_cost_usd"]), 6) if agg else 0.0,
        "avg_turn_latency_ms": round(float(agg["avg_latency_ms"]), 2) if agg else 0.0,
        "breakdown_by_model": [dict(r) for r in by_model_rows],
    }

    # Proyección mensual para los 800 empleados de TechCorp LATAM (68,640 consultas/mes)
    monthly_projection_modality_2_2 = {
        "headcount_employees": 800,
        "active_daily_users_dau": 520,
        "monthly_queries_estimated": 68640,
        "monthly_input_tokens": 80_500_000,
        "monthly_output_tokens": 29_400_000,
        "cost_breakdown_usd": {
            "tokens_vertex_ai_hybrid": 60.89,
            "compute_cloud_run": 78.40,
            "database_cloud_sql_pg16": 84.50,
            "storage_audit_and_secrets": 6.20,
            "network_and_cloud_logging": 12.60,
            "total_monthly_usd": 242.59,
            "cost_per_employee_usd": 0.30,
        },
    }

    modalities_comparison = [
        {
            "modality_id": "2.1",
            "name": "Modalidad 2.1 — GCP Console (100% Gemini Pro sin ADK Caching)",
            "tokens_usd": 247.63,
            "compute_usd": 68.00,
            "storage_network_usd": 97.10,
            "total_usd": 412.73,
            "p95_latency_ms": 2150,
            "availability_sla_pct": 99.50,
            "recommended": False,
        },
        {
            "modality_id": "2.2",
            "name": "Modalidad 2.2 — Google ADK + GCP + Circuit Breaker (Seleccionada)",
            "tokens_usd": 60.89,
            "compute_usd": 78.40,
            "storage_network_usd": 103.30,
            "total_usd": 242.59,
            "p95_latency_ms": 920,
            "availability_sla_pct": 99.95,
            "recommended": True,
        },
        {
            "modality_id": "2.3",
            "name": "Modalidad 2.3 — Ollama 100% Local (Servidor GPU Dedicado)",
            "tokens_usd": 0.00,
            "compute_usd": 310.00,
            "storage_network_usd": 45.00,
            "total_usd": 355.00,
            "p95_latency_ms": 3400,
            "availability_sla_pct": 98.50,
            "recommended": False,
        },
    ]

    return {
        "realtime_usage": realtime_usage,
        "monthly_projection_800_employees": monthly_projection_modality_2_2,
        "modalities_comparison": modalities_comparison,
    }
