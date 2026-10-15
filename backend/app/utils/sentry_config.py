"""
Configuración de Sentry para monitoreo de errores en producción.

Sentry detecta automáticamente:
- Excepciones no capturadas
- Errores HTTP 500
- Performance issues
- Transacciones lentas
- Error rates anormales

Setup:
1. Crear cuenta en https://sentry.io (gratuito hasta 5000 eventos/mes)
2. Crear proyecto "Python/FastAPI"
3. Copiar DSN
4. Agregar a .env: SENTRY_DSN=https://...@sentry.io/...
5. Reiniciar servidor
"""

import logging
import os
from typing import Any, Literal, Mapping, Optional

logger = logging.getLogger(__name__)

SentryLevel = Literal["debug", "info", "warning", "error", "fatal", "critical"]

sentry_sdk: Any | None = None
FastApiIntegration: Any | None = None
SqlalchemyIntegration: Any | None = None
LoggingIntegration: Any | None = None
_sentry_available = False

try:
    import sentry_sdk as _sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_sdk = _sentry_sdk
    _sentry_available = True
except ImportError:
    _sentry_available = False
    logger.debug("sentry-sdk no instalado. Para habilitar: pip install sentry-sdk[fastapi]")


def init_sentry() -> None:
    """Compatibility entrypoint: delegate to the single canonical Sentry owner.

    Older utilities used to call sentry_sdk.init a second time using a
    conflicting DSN/sampling/PII configuration. Never reinitialize it here.
    """
    from app.utils.observability import initialize_observability

    initialize_observability()


def capture_exception(exc: Exception, context: Optional[Mapping[str, Any]] = None) -> Optional[str]:
    """
    Captura una excepción en Sentry manualmente.
    
    Args:
        exc: La excepción a capturar
        context: Dict con información adicional
        
    Returns:
        ID de evento Sentry (para referenciar en logs)
    """
    if not _sentry_available or sentry_sdk is None:
        logger.debug(f"Captura de excepción local: {exc}")
        return None
    
    if context:
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_context(key, value)
            event_id = sentry_sdk.capture_exception(exc)
    else:
        event_id = sentry_sdk.capture_exception(exc)
    
    return str(event_id) if event_id else None


def capture_message(
    message: str,
    level: SentryLevel = "info",
    context: Optional[Mapping[str, Any]] = None,
) -> Optional[str]:
    """
    Captura un mensaje en Sentry.
    
    Args:
        message: Mensaje a capturar
        level: 'debug', 'info', 'warning', 'error', 'fatal'
        context: Dict con información adicional
        
    Returns:
        ID de evento Sentry
    """
    if not _sentry_available or sentry_sdk is None:
        logger.debug(f"Captura de mensaje local [{level}]: {message}")
        return None
    
    if context:
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_context(key, value)
            event_id = sentry_sdk.capture_message(message, level=level)
    else:
        event_id = sentry_sdk.capture_message(message, level=level)
    
    return str(event_id) if event_id else None


def set_user_context(user_id: int, username: str, email: Optional[str] = None) -> None:
    """
    Establece contexto de usuario en Sentry para tracking.
    
    Llamar en función de login después de autenticar.
    """
    if not _sentry_available or sentry_sdk is None:
        logger.debug(f"Contexto de usuario local: {username} ({user_id})")
        return
    
    with sentry_sdk.push_scope() as scope:
        scope.set_user({
            "id": str(user_id),
            "username": username,
            "email": email or ""
        })


# ============================================================================
# Ejemplos de uso en aplicación
# ============================================================================

# En main.py:
# from app.utils.sentry_config import init_sentry
# init_sentry()

# En routers/auth.py (después de login):
# from app.utils.sentry_config import set_user_context
# set_user_context(user.id, user.username, user.email)

# En cualquier ruta para capturar excepción:
# from app.utils.sentry_config import capture_exception
# try:
#     ...
# except Exception as e:
#     event_id = capture_exception(e, {"order_id": 123})
#     logger.error(f"Error en orden (Sentry: {event_id})")

# Para mensajes importantes:
# from app.utils.sentry_config import capture_message
# capture_message("Stock bajo en producto X", level="warning", context={
#     "product_id": 42,
#     "current_stock": 5,
#     "threshold": 10
# })
