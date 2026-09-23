"""Middleware que asegura correlación básica de logs mediante X-Request-ID."""

from __future__ import annotations

import logging
import os
import re
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.utils.logging_config import LogContext

logger = logging.getLogger(__name__)

_RELEASE_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _get_release_sha() -> str:
    """Devuelve el SHA de release sólo cuando tiene formato Git completo válido."""
    value = (os.getenv("APP_BUILD_SHA") or "unknown").strip().lower()
    if _RELEASE_SHA_PATTERN.fullmatch(value):
        return value
    return "unknown"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Injecta un request_id y la identidad del release en la respuesta."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        with LogContext(request_id=request_id):
            logger.debug(
                "Request recibido",
                extra={"method": request.method, "path": str(request.url)},
            )
            try:
                response: Response = await call_next(request)
            except Exception:
                logger.exception("Error procesando request")
                raise

        response.headers.setdefault("X-Request-ID", request_id)
        response.headers.setdefault("X-Release-SHA", _get_release_sha())
        return response
