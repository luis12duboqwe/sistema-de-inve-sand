"""Guards for bootstrap and destructive endpoints in production."""

from __future__ import annotations

import os
import re
import secrets

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


_PRODUCT_PURGE_PATH = re.compile(r"^/api/super-admin/products/\d+/purge$")


def _is_production() -> bool:
    return settings.environment == "production" and not settings.debug


def _secure_match(provided: str | None, expected: str | None) -> bool:
    if not provided or not expected:
        return False
    return secrets.compare_digest(provided, expected)


class ProductionGuardMiddleware(BaseHTTPMiddleware):
    """Protect endpoints that must never be open by default in production."""

    async def dispatch(self, request: Request, call_next):
        if not _is_production():
            return await call_next(request)

        path = request.url.path

        if path == "/api/auth/setup" and request.method == "POST":
            if not settings.setup_token:
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": "Inicialización bloqueada: SETUP_TOKEN no configurado"
                    },
                )

            if not _secure_match(
                request.headers.get("X-Setup-Token"), settings.setup_token
            ):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Token de inicialización inválido"},
                )

        if request.method == "POST" and _PRODUCT_PURGE_PATH.match(path):
            purge_enabled = (
                os.getenv("ENABLE_DESTRUCTIVE_PURGE", "false").strip().lower()
                == "true"
            )
            if not purge_enabled:
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": (
                            "La purga destructiva está deshabilitada en producción. "
                            "Desactive el producto en lugar de borrar su historial."
                        )
                    },
                )

            confirmed = (
                request.headers.get("X-Confirm-Destructive-Operation", "").strip()
                == "PURGE_PRODUCT"
            )
            token_valid = _secure_match(
                request.headers.get("X-Destructive-Operation-Token"),
                settings.destructive_operation_token,
            )
            if not confirmed or not token_valid:
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": (
                            "La operación destructiva requiere confirmación explícita "
                            "y un token administrativo separado."
                        )
                    },
                )

        return await call_next(request)
