from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.admin_routes import router as admin_router
from app.api.auth_routes import router as auth_router
from app.api.chat_routes import router as chat_router
from app.api.health_routes import router as health_router
from app.core.config import settings
from app.core.observability import log_structured_event, metrics_collector


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Proyecto A — Asistente Empresarial Inteligente para TechCorp LATAM (800 empleados). "
            "Modalidad 2.2: Google Agent Development Kit (ADK) con ciclo ReAct, Circuit Breaker "
            "(Vertex AI Gemini 2.5 -> Ollama llama3.2:3b), Auditoría Inmutable SHA-256 y Análisis de Costos E6."
        ),
    )

    # CORS Restrictivo por diseño
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        metrics_collector.total_errors += 1
        log_structured_event(
            "INPUT_VALIDATION_REJECTED",
            f"Entrada inválida en {request.url.path}",
            severity="WARNING",
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "INVALID_INPUT_PAYLOAD",
                "message": "Los datos enviados no cumplen con el esquema de validación requerido.",
                "details": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        metrics_collector.total_errors += 1
        log_structured_event(
            "UNHANDLED_SERVER_ERROR",
            f"Excepción controlada en {request.url.path}: {type(exc).__name__}",
            severity="ERROR",
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Ocurrió un error interno procesando su solicitud. El incidente fue registrado.",
            },
        )

    app.include_router(auth_router)
    app.include_router(chat_router)
    app.include_router(admin_router)
    app.include_router(health_router)
    return app


app = create_application()
