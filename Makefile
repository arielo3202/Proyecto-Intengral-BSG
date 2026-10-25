# ==============================================================================
# TechCorp LATAM — Proyecto A: Asistente Empresarial Inteligente (Modalidad 2.2)
# Stack: Python 3.14 + FastAPI + Google ADK + React 18 + Vite 6 + PostgreSQL
# ==============================================================================

SHELL := /bin/bash
PYTHON_BIN ?= python3.14
VENV_DIR := .venv
BACKEND_DIR := backend
FRONTEND_DIR := frontend
DB_URL ?= postgresql://techcorp_user:techcorp_pass@localhost:5432/techcorp_adk

.PHONY: help setup-venv install install-backend install-frontend db-up db-migrate seed test lint run-backend run-frontend build-docker clean

help: ## Muestra esta ayuda interactiva con todos los comandos disponibles
	@echo "=============================================================================="
	@echo "  TechCorp LATAM — Asistente Empresarial Inteligente (Google ADK + GCP 2.2)   "
	@echo "=============================================================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "NOTA DE EJECUCIÓN EN TERMINALES SEPARADAS:"
	@echo "  Terminal 1 (Backend API + ADK Runner): make run-backend"
	@echo "  Terminal 2 (Frontend Pixel Art UI):    make run-frontend"

setup-venv: ## Crea el entorno virtual .venv en Python 3.14 (con fallback seguro si 3.14 no está en PATH)
	@echo "[1/2] Configurando entorno virtual en $(VENV_DIR) orientando a Python 3.14..."
	@bash scripts/setup_venv.sh $(VENV_DIR)
	@echo "[2/2] Actualizando pip, setuptools y wheel..."
	@$(VENV_DIR)/bin/pip install --upgrade pip setuptools wheel

install-backend: setup-venv ## Instala las dependencias del Backend (Python 3.14 + FastAPI + Google ADK)
	@echo "[Backend] Instalando dependencias desde $(BACKEND_DIR)/requirements.txt..."
	@$(VENV_DIR)/bin/pip install -r $(BACKEND_DIR)/requirements.txt

install-frontend: ## Instala las dependencias del Frontend (React 18 + Vite 6 + TypeScript)
	@echo "[Frontend] Instalando paquetes npm en $(FRONTEND_DIR)..."
	@cd $(FRONTEND_DIR) && npm install

install: install-backend install-frontend ## Configura .venv e instala todas las dependencias (Backend + Frontend)
	@echo "[OK] Instalación completa de Backend y Frontend."

db-up: ## Levanta PostgreSQL 16 y Ollama local mediante Docker Compose para desarrollo
	@echo "[Infra] Levantando servicios base (PostgreSQL + Ollama)..."
	@docker compose up -d postgres ollama

db-migrate: ## Ejecuta las migraciones SQL de PostgreSQL e inicializa tablas de sesiones, auditoría y series temporales
	@echo "[DB] Ejecutando migraciones relacionales y de series temporales en PostgreSQL..."
	@PYTHONPATH=$(BACKEND_DIR) $(VENV_DIR)/bin/python -m app.db.migrate

seed: ## Carga datos semilla (políticas corporativas TechCorp LATAM, usuarios demo y series bursátiles base)
	@echo "[DB] Cargando catálogo de políticas de TechCorp LATAM y usuarios de prueba..."
	@PYTHONPATH=$(BACKEND_DIR) $(VENV_DIR)/bin/python -m app.db.seed

 run-backend: ## [TERMINAL 1] Inicia el servidor Backend FastAPI + Google ADK en http://localhost:8000
	@echo "=============================================================================="
	@echo "  Iniciando Backend FastAPI (Python 3.14) + Google ADK Runner en puerto 8000"
	@echo "  Swagger OpenAPI Docs: http://localhost:8000/docs"
	@echo "=============================================================================="
	@cd $(BACKEND_DIR) && ../$(VENV_DIR)/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

run-frontend: ## [TERMINAL 2] Inicia el servidor Frontend React 18 + Vite 6 (Pixel Art UI) en http://localhost:5173
	@echo "=============================================================================="
	@echo "  Iniciando Frontend React 18 + Vite 6 (Pixel Art UI) en puerto 5173"
	@echo "  URL Local: http://localhost:5173"
	@echo "=============================================================================="
	@cd $(FRONTEND_DIR) && npm run dev -- --host 0.0.0.0 --port 5173

test: ## Ejecuta la suite completa de pruebas unitarias, de integración, Circuit Breaker y auditoría
	@echo "[QA] Ejecutando pytest sobre Backend, Agente ReAct, Circuit Breaker y Validador Cuantitativo..."
	@PYTHONPATH=$(BACKEND_DIR) $(VENV_DIR)/bin/pytest $(BACKEND_DIR)/tests -v --tb=short || PYTHONPATH=$(BACKEND_DIR) python3 -m unittest discover -s $(BACKEND_DIR)/tests -v

lint: ## Ejecuta verificación de tipos estáticos y formato en Backend y Frontend
	@PYTHONPATH=$(BACKEND_DIR) $(VENV_DIR)/bin/python -m compileall $(BACKEND_DIR)/app
	@cd $(FRONTEND_DIR) && npm run typecheck

build-docker: ## Construye las imágenes Docker listas para Cloud Run
	@docker build -f deploy/Dockerfile.backend -t gcr.io/techcorp-latam/asistente-backend:1.0.0 .
	@docker build -f deploy/Dockerfile.frontend -t gcr.io/techcorp-latam/asistente-frontend:1.0.0 .

clean: ## Elimina entornos virtuales, cachés temporales y artefactos de compilación
	@rm -rf $(VENV_DIR) $(BACKEND_DIR)/.pytest_cache $(FRONTEND_DIR)/dist $(FRONTEND_DIR)/node_modules
	@find . -type d -name "__pycache__" -exec rm -rf {} +
