# Changelog (`CHANGELOG.md`)
Todos los cambios notables de este proyecto se documentan siguiendo [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y [Semantic Versioning](https://semver.org/lang/es/).

## [1.0.0] - 2026-10-24
### Added
- **Backend Python 3.14 + FastAPI:** Gateway REST asíncrono con validación estricta Pydantic v2, autenticación JWT (HS256/RS256) y control de acceso basado en roles (`usuario` y `admin`).
- **Google ADK ReAct Agent (Modalidad 2.2):** Implementación del Root Agent con ciclo `Reason -> Act -> Observe`, memoria de sesión persistente por `session_id` y 3 herramientas invocables (`@tool`): `search_corporate_policies`, `create_it_support_ticket` y `analyze_stock_comparative`.
- **Circuit Breaker + Fallback LLM:** Conmutación automática desde Vertex AI (`gemini-2.5-pro` / `gemini-2.5-flash`) hacia Ollama local (`llama3.2:3b`) ante timeouts, errores HTTP 429 o caídas de servicio.
- **Motor Financiero Cuantitativo Resiliente:** Validación de frescura de precios, homogeneidad de moneda, detección de anomalías por Z-score, caché con TTL diferenciado por estado del mercado y fallback entre proveedores compatibles.
- **Auditoría Inmutable Criptográfica:** Registro en PostgreSQL y `JSONL` con cadena de hashes SHA-256 verificable y exportación directa a **PDF** y **CSV** para administradores.
- **Frontend React 18 + Vite 6 + TypeScript (Diseño Pixel Art):** Interfaz accesible (WCAG AA) con terminal de chat multi-turno y Dashboard de Uso y Análisis de Costos E6 integrado en vivo.
