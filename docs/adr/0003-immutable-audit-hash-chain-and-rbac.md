# ADR-003: Registro de Auditoría Inmutable con Cadena Hash SHA-256 y Segregación RBAC Estricta
- **Estado:** Aceptado
- **Fecha:** 2026-10-24
- **Contexto:** Por cumplimiento normativo y control financiero, ningún usuario con rol `usuario` debe visualizar información técnica (tokens, costos, latencias o logs), mientras que el rol `admin` requiere evidencia inalterable de cada operación y capacidad de exportación en PDF y CSV.
- **Decisión:**
  1. Definir DTOs de salida disjuntos en FastAPI (`UserChatResponseDTO` vs `AdminChatResponseDTO`).
  2. Persistir cada evento en formato `JSONL` y en PostgreSQL encadenando criptográficamente cada fila con el hash SHA-256 de la fila inmediata anterior (`prev_hash` -> `record_hash`).
- **Consecuencias:** Prevención total de fuga de metadatos técnicos al usuario final y detección inmediata de cualquier intento de manipulación de registros históricos.
