# ADR-002: Patrón Circuit Breaker entre Vertex AI (Gemini 2.5) y Ollama Local (`llama3.2:3b`)
- **Estado:** Aceptado
- **Fecha:** 2026-10-24
- **Contexto:** Los servicios de LLM en la nube pueden experimentar picos de latencia, límites de cuota (`HTTP 429`) o interrupciones regionales que afectarían la continuidad operativa de los 800 empleados.
- **Decisión:** Implementar una máquina de estados `LLMCircuitBreaker` (`CLOSED`, `OPEN`, `HALF_OPEN`) con `failure_threshold=3` y `recovery_timeout=45s`, acompañada de reintentos con *exponential backoff + jitter*. Cuando el circuito se abre, el tráfico se redirige de forma transparente a `llama3.2:3b` ejecutándose en Ollama (`http://localhost:11434`).
- **Consecuencias:** Disponibilidad efectiva superior al 99.95% y aislamiento de fallos externos sin bloquear los hilos asíncronos de FastAPI.
