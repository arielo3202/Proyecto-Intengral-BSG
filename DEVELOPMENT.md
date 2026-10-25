# Guía de Desarrollo Local Reproducible (`DEVELOPMENT.md`)

## 1. Requisitos del Sistema Local
- **Python:** `3.14.x` (compatible también con `3.12+` mediante el script `scripts/setup_venv.sh`).
- **Node.js:** `v20.11+` o `v22.x` con `npm 10+`.
- **PostgreSQL:** `16.x` (opcional en desarrollo local gracias al modo `USE_SQLITE_FALLBACK=true` para levantar sin Docker, o mediante `make db-up` con Docker Compose).
- **Ollama (para fallback local):** `ollama serve` y `ollama pull llama3.2:3b`.

## 2. Flujo de Trabajo en Dos Terminales (Requisito Estricto)

1. **Inicializar entorno virtual e instalar dependencias:**
   ```bash
   make install
   make db-migrate
   make seed
   ```
2. **Terminal 1 — Levantar Backend FastAPI + Google ADK Runner:**
   ```bash
   make run-backend
   ```
   El backend quedará escuchando en `http://localhost:8000` (Documentación interactiva en `http://localhost:8000/docs`).
3. **Terminal 2 — Levantar Frontend React 18 + Vite 6 (Pixel Art UI):**
   ```bash
   make run-frontend
   ```
   El frontend quedará disponible en `http://localhost:5173`.

## 3. Cuentas de Prueba Pre-cargadas
- **Rol Usuario (Empleado):** `empleado@techcorp.latam` / Contraseña: `UserPixel2026!`
- **Rol Administrador (FinOps / Auditoría):** `admin@techcorp.latam` / Contraseña: `AdminPixel2026!`
