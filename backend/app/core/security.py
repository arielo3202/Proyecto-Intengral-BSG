from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Literal

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.observability import log_structured_event

RoleType = Literal["usuario", "admin"]
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(slots=True)
class AuthenticatedUser:
    user_id: str
    email: str
    full_name: str
    role: RoleType
    department: str


def hash_password(plain_password: str, salt: str | None = None) -> str:
    """Genera hash seguro PBKDF2-HMAC-SHA256 con 310,000 iteraciones (recomendación OWASP)."""
    active_salt = salt or secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        active_salt.encode("utf-8"),
        310_000,
    ).hex()
    return f"pbkdf2_sha256$310000${active_salt}${derived}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        parts = stored_hash.split("$")
        if len(parts) != 4:
            return False
        _, iterations_str, salt, expected_hex = parts
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations_str),
        ).hex()
        return hmac.compare_digest(derived, expected_hex)
    except Exception:
        return False


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(encoded: str) -> bytes:
    padding = "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(encoded + padding)


def create_jwt_token(
    user_id: str,
    email: str,
    full_name: str,
    role: RoleType,
    department: str,
    expires_minutes: int | None = None,
) -> str:
    """
    Crea un token JWT estándar RFC 7519.
    Soporta PyJWT si está instalado o implementación criptográfica nativa HMAC-SHA256 (HS256)
    para máxima portabilidad en cualquier entorno Python 3.14.
    """
    now = int(time.time())
    exp = now + int((expires_minutes or settings.jwt_expire_minutes) * 60)
    header = {"alg": settings.jwt_algorithm, "typ": "JWT"}
    payload = {
        "sub": user_id,
        "email": email,
        "full_name": full_name,
        "role": role,
        "department": department,
        "iat": now,
        "exp": exp,
        "iss": "techcorp-latam-auth",
    }

    try:
        import jwt  # type: ignore

        signing_key = (
            settings.jwt_private_key_pem
            if settings.jwt_algorithm == "RS256" and settings.jwt_private_key_pem
            else settings.jwt_secret_key
        )
        return str(jwt.encode(payload, signing_key, algorithm=settings.jwt_algorithm))
    except ImportError:
        header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        signature = hmac.new(
            settings.jwt_secret_key.encode("utf-8"), signing_input, hashlib.sha256
        ).digest()
        return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"


def decode_jwt_token(token: str) -> AuthenticatedUser:
    """Valida firma criptográfica, expiración y estructura de claims del JWT."""
    try:
        try:
            import jwt  # type: ignore

            verify_key = (
                settings.jwt_public_key_pem
                if settings.jwt_algorithm == "RS256" and settings.jwt_public_key_pem
                else settings.jwt_secret_key
            )
            payload = jwt.decode(
                token,
                verify_key,
                algorithms=[settings.jwt_algorithm],
                issuer="techcorp-latam-auth",
            )
        except ImportError:
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Formato JWT inválido")
            header_b64, payload_b64, sig_b64 = parts
            signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
            expected_sig = hmac.new(
                settings.jwt_secret_key.encode("utf-8"), signing_input, hashlib.sha256
            ).digest()
            actual_sig = _b64url_decode(sig_b64)
            if not hmac.compare_digest(expected_sig, actual_sig):
                raise ValueError("Firma JWT inválida")
            payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
            if int(payload.get("exp", 0)) < int(time.time()):
                raise ValueError("Token JWT expirado")

        role = payload.get("role")
        if role not in ("usuario", "admin"):
            raise ValueError("Rol inválido en JWT")

        return AuthenticatedUser(
            user_id=str(payload["sub"]),
            email=str(payload["email"]),
            full_name=str(payload.get("full_name", "")),
            role=role,
            department=str(payload.get("department", "General")),
        )
    except Exception as exc:
        log_structured_event(
            "AUTH_TOKEN_REJECTED",
            f"Intento de acceso con token inválido: {exc}",
            severity="WARNING",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token JWT inválido o expirado. Por favor inicie sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere cabecera Authorization: Bearer <JWT>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_jwt_token(credentials.credentials)


async def require_admin_role(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Guardia RBAC estricta: Bloquea a cualquier rol 'usuario' de acceder a endpoints técnicos o de costos."""
    if current_user.role != "admin":
        log_structured_event(
            "RBAC_ACCESS_DENIED",
            "Usuario sin privilegios intentó acceder a recurso exclusivo de Administrador",
            severity="WARNING",
            user_id=current_user.user_id,
            role=current_user.role,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: Se requiere rol 'admin' para consultar telemetría, auditoría o costos.",
        )
    return current_user
