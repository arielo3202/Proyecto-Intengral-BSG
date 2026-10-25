from __future__ import annotations

import unittest

from app.agent.adk_agent import techcorp_adk_agent
from app.services.circuit_breaker import llm_circuit_breaker


class TestAgentAndCircuitBreaker(unittest.IsolatedAsyncioTestCase):
    async def test_circuit_breaker_fallback_to_ollama_and_recovery(self) -> None:
        # 1. Estado normal CLOSED -> Usa Vertex AI
        llm_circuit_breaker.force_state("CLOSED", "Reset para test")
        out_closed = await techcorp_adk_agent.run_react_turn(
            user_id="usr-emp-001",
            user_email="empleado@techcorp.latam",
            user_role="usuario",
            session_id="sess-cb-test",
            user_message="¿Cuál es la política de vacaciones y días libres?",
            preferred_tier="light",
        )
        self.assertEqual(out_closed.llm_provider, "vertex_ai")
        self.assertFalse(out_closed.fallback_triggered)
        self.assertGreaterEqual(len(out_closed.react_steps), 3)

        # 2. Forzar fallo en Vertex AI (Circuit Breaker OPEN) -> Conmuta a Ollama llama3.2:3b
        llm_circuit_breaker.force_state("OPEN", "Simulación de caída de Vertex AI")
        out_open = await techcorp_adk_agent.run_react_turn(
            user_id="usr-emp-001",
            user_email="empleado@techcorp.latam",
            user_role="usuario",
            session_id="sess-cb-test",
            user_message="Necesito abrir un ticket urgente porque mi VPN está bloqueada",
            preferred_tier="light",
        )
        self.assertEqual(out_open.llm_provider, "ollama_fallback")
        self.assertEqual(out_open.llm_model, "llama3.2:3b")
        self.assertTrue(out_open.fallback_triggered)
        self.assertIn("TCK-", out_open.reply)

        # 3. Restaurar Circuit Breaker a CLOSED
        llm_circuit_breaker.force_state("CLOSED", "Restauración tras test")


if __name__ == "__main__":
    unittest.main()
