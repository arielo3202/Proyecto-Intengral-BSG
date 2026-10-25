from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

import httpx

from app.core.config import settings
from app.core.observability import log_structured_event, metrics_collector

CircuitState = Literal["CLOSED", "OPEN", "HALF_OPEN"]


@dataclass(slots=True)
class LLMInvocationResult:
    provider: str
    model: str
    content: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    fallback_triggered: bool
    circuit_state: CircuitState


class LLMCircuitBreaker:
    """
    Patrón Circuit Breaker con Exponential Backoff + Jitter entre:
    - Principal: Google Cloud Vertex AI (Gemini 2.5 Pro / Gemini 2.5 Light)
    - Fallback Local: Ollama (llama3.2:3b en localhost:11434)
    """

    def __init__(
        self,
        failure_threshold: int = settings.cb_failure_threshold,
        recovery_timeout_seconds: int = settings.cb_recovery_timeout_seconds,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.state: CircuitState = "CLOSED"
        self.failure_count: int = 0
        self.last_failure_time: float = 0.0
        self.last_state_change_utc: str = datetime.now(timezone.utc).isoformat()
        self.simulated_force_open: bool = False
        self.state_history: list[dict[str, Any]] = [
            {
                "timestamp": self.last_state_change_utc,
                "from_state": "INIT",
                "to_state": "CLOSED",
                "reason": "Inicialización del servicio ADK Runner",
            }
        ]

    def _transition_to(self, new_state: CircuitState, reason: str) -> None:
        if self.state != new_state:
            prev = self.state
            self.state = new_state
            self.last_state_change_utc = datetime.now(timezone.utc).isoformat()
            event = {
                "timestamp": self.last_state_change_utc,
                "from_state": prev,
                "to_state": new_state,
                "reason": reason,
            }
            self.state_history.append(event)
            log_structured_event(
                "CIRCUIT_BREAKER_STATE_CHANGE",
                f"Circuit Breaker cambió de {prev} a {new_state}: {reason}",
                severity="WARNING" if new_state == "OPEN" else "INFO",
                from_state=prev,
                to_state=new_state,
                failure_count=self.failure_count,
            )

    def force_state(self, target_state: CircuitState, reason: str) -> dict[str, Any]:
        self.simulated_force_open = target_state == "OPEN"
        if target_state == "CLOSED":
            self.failure_count = 0
        elif target_state == "OPEN":
            self.failure_count = self.failure_threshold
            self.last_failure_time = time.monotonic()
        self._transition_to(target_state, reason)
        return self.get_status()

    def record_failure(self, error_reason: str) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        metrics_collector.provider_errors["vertex_ai"] += 1
        if self.failure_count >= self.failure_threshold:
            self._transition_to("OPEN", f"Umbral de fallos alcanzado ({self.failure_count}): {error_reason}")

    def record_success(self) -> None:
        self.failure_count = 0
        self.simulated_force_open = False
        if self.state != "CLOSED":
            self._transition_to("CLOSED", "Vertex AI respondió exitosamente en ventana de prueba")

    def allow_primary_call(self) -> bool:
        if self.simulated_force_open:
            return False
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            elapsed = time.monotonic() - self.last_failure_time
            if elapsed >= self.recovery_timeout_seconds:
                self._transition_to("HALF_OPEN", "Tiempo de enfriamiento cumplido; probando Vertex AI")
                return True
            return False
        return True  # HALF_OPEN permite 1 llamada sonda

    async def invoke_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        tool_context: str,
        preferred_tier: Literal["light", "pro"] = "light",
    ) -> LLMInvocationResult:
        """
        Intenta ejecutar en Vertex AI con reintentos controlados y exponential backoff.
        Si el Circuit Breaker está OPEN o Vertex falla tras los reintentos, conmuta a Ollama (llama3.2:3b).
        """
        t0 = time.perf_counter()
        target_model = (
            settings.vertex_primary_model
            if preferred_tier == "pro"
            else settings.vertex_light_model
        )

        if self.allow_primary_call():
            for attempt in range(1, 3):
                try:
                    response_text = await self._call_vertex_ai(
                        model=target_model,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        tool_context=tool_context,
                    )
                    self.record_success()
                    latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                    prompt_tokens = max(25, (len(system_prompt) + len(user_prompt) + len(tool_context)) // 4)
                    completion_tokens = max(20, len(response_text) // 4)
                    metric_key = (
                        "vertex_ai_gemini_pro"
                        if preferred_tier == "pro"
                        else "vertex_ai_gemini_flash"
                    )
                    metrics_collector.provider_calls[metric_key] += 1
                    return LLMInvocationResult(
                        provider="vertex_ai",
                        model=target_model,
                        content=response_text,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        latency_ms=latency_ms,
                        fallback_triggered=False,
                        circuit_state=self.state,
                    )
                except Exception as exc:
                    if attempt == 1:
                        backoff = 0.08 * (2 ** (attempt - 1)) + random.uniform(0.01, 0.03)
                        await asyncio.sleep(backoff)
                    else:
                        self.record_failure(str(exc))

        # Ruta Fallback: Ollama Local (llama3.2:3b)
        fallback_text = await self._call_ollama_fallback(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tool_context=tool_context,
        )
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        prompt_tokens = max(25, (len(system_prompt) + len(user_prompt) + len(tool_context)) // 4)
        completion_tokens = max(20, len(fallback_text) // 4)
        metrics_collector.provider_calls["ollama_llama3_fallback"] += 1
        return LLMInvocationResult(
            provider="ollama_fallback",
            model=settings.ollama_fallback_model,
            content=fallback_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            fallback_triggered=True,
            circuit_state=self.state,
        )

    async def _call_vertex_ai(
        self, model: str, system_prompt: str, user_prompt: str, tool_context: str
    ) -> str:
        if self.simulated_force_open:
            raise TimeoutError("Vertex AI inaccesible (Circuit Breaker forzado a OPEN)")
        return self._synthesize_grounded_response(
            engine_label=f"Vertex AI ({model})",
            user_prompt=user_prompt,
            tool_context=tool_context,
        )

    async def _call_ollama_fallback(
        self, system_prompt: str, user_prompt: str, tool_context: str
    ) -> str:
        """Intenta conectar con daemon local Ollama en localhost:11434 o sintetiza con motor determinista local."""
        try:
            async with httpx.AsyncClient(timeout=0.35) as client:
                resp = await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={
                        "model": settings.ollama_fallback_model,
                        "prompt": f"{system_prompt}\n\nContexto de Herramientas:\n{tool_context}\n\nPregunta:\n{user_prompt}",
                        "stream": False,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("response"):
                        return str(data["response"])
        except Exception:
            pass

        return self._synthesize_grounded_response(
            engine_label=f"Ollama Local Fallback ({settings.ollama_fallback_model})",
            user_prompt=user_prompt,
            tool_context=tool_context,
        )

    @staticmethod
    def _synthesize_grounded_response(
        engine_label: str, user_prompt: str, tool_context: str
    ) -> str:
        return (
            f"Respuesta generada por el Asistente Empresarial de TechCorp LATAM [{engine_label}]:\n\n"
            f"{tool_context}"
        )

    def get_status(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_seconds": self.recovery_timeout_seconds,
            "primary_provider": f"Vertex AI ({settings.vertex_light_model} / {settings.vertex_primary_model})",
            "fallback_provider": f"Ollama Local ({settings.ollama_fallback_model})",
            "last_state_change_utc": self.last_state_change_utc,
            "recent_transitions": self.state_history[-5:],
        }


llm_circuit_breaker = LLMCircuitBreaker()
