from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.core.observability import log_structured_event
from app.core.security import (
    AuthenticatedUser,
    create_jwt_token,
    get_current_user,
    verify_password,
)
from app.db.database import db_manager
from app.models.schemas import LoginRequestDTO, LoginResponseDTO

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación y Roles JWT"])


@router.post("/login", response_model=LoginResponseDTO)
async def login_endpoint(payload: LoginRequestDTO) -> LoginResponseDTO:
    user_row = db_manager.get_user_by_email(payload.email)
    if not user_row or not verify_password(payload.password, str(user_row["password_hash"])):
        log_structured_event(
            "AUTH_LOGIN_FAILED",
            f"Intento fallido de inicio de sesión para {payload.email}",
            severity="WARNING",
            email=payload.email,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas. Verifique su correo corporativo y contraseña.",
        )

    role = "admin" if user_row["role"] == "admin" else "usuario"
    token = create_jwt_token(
        user_id=str(user_row["id"]),
        email=str(user_row["email"]),
        full_name=str(user_row["full_name"]),
        role=role,
        department=str(user_row["department"]),
    )
    log_structured_event(
        "AUTH_LOGIN_SUCCESS",
        f"Inicio de sesión exitoso para {user_row['email']} ({role})",
        severity="INFO",
        user_id=user_row["id"],
        role=role,
    )
    return LoginResponseDTO(
        access_token=token,
        user_id=str(user_row["id"]),
        email=str(user_row["email"]),
        full_name=str(user_row["full_name"]),
        role=role,
        department=str(user_row["department"]),
        expires_in_seconds=settings.jwt_expire_minutes * 60,
    )


@router.get("/me")
async def get_me_endpoint(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, str]:
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "department": current_user.department,
    }
