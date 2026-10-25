# ADR-001: Adopción de Google ADK con Ciclo ReAct y Memoria por `session_id` (Modalidad 2.2)
- **Estado:** Aceptado
- **Fecha:** 2026-10-24
- **Contexto:** TechCorp LATAM requiere un asistente empresarial para 800 empleados capaz de consultar normativa interna, abrir tickets de soporte TI y ejecutar cálculos financieros auditables manteniendo contexto multi-turno.
- **Decisión:** Utilizar **Google Agent Development Kit (ADK)** estructurado bajo el patrón **ReAct (`Reason` -> `Act` -> `Observe`)** con herramientas Python tipadas decoradas mediante `@tool` y persistencia de sesión por `session_id` en Cloud SQL (PostgreSQL).
- **Consecuencias:** Trazabilidad completa de cada decisión del agente, fácil extensión del catálogo de herramientas sin modificar el motor de orquestación y compatibilidad nativa con Cloud Run y Vertex AI.
