"""Middleware que asegura correlación básica de logs mediante X-Request-ID."""

from __future__ import annotations

import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.utils.logging_config import LogContext

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Injecta un request_id en el contexto y cabecera de la respuesta."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        with LogContext(request_id=request_id):
            logger.debug(
                "Request recibido",
                extra={"method": request.method, "path": str(request.url)}
            )
            try:
                response: Response = await call_next(request)
            except Exception:
                logger.exception("Error procesando request")
                raise

        response.headers.setdefault("X-Request-ID", request_id)
        return response
