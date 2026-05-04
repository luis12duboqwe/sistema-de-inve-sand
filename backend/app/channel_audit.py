"""
Sistema de logging y auditoría para integración de canales.

Proporciona:
1. Logs estructurados de eventos de canal
2. Auditoría de cambios de configuración
3. Métricas de mensaje por canal/perfil
4. Debug información para troubleshooting

Uso:
    from app.channel_audit import log_channel_event, log_config_change
    
    log_channel_event(
        channel="whatsapp",
        event_type="message_received",
        sales_profile_slug="softmobile-bot",
        customer_id="1234567890",
        details={"message_id": "wamid_123", "text": "Hola"}
    )
"""

import json
import logging
from datetime import datetime, UTC
from typing import Any, Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ChannelEventType(str, Enum):
    """Tipos de eventos que se pueden auditar."""
    
    # Webhook events
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"
    MESSAGE_DUPLICATE = "message_duplicate"
    
    # Configuration
    CONFIG_CREATED = "config_created"
    CONFIG_UPDATED = "config_updated"
    CONFIG_DELETED = "config_deleted"
    CREDENTIALS_ROTATED = "credentials_rotated"
    
    # Validation
    CONNECTION_TESTED = "connection_tested"
    CONNECTION_SUCCESS = "connection_success"
    CONNECTION_FAILED = "connection_failed"
    
    # Errors
    WEBHOOK_VERIFICATION_FAILED = "webhook_verification_failed"
    INVALID_SIGNATURE = "invalid_signature"
    MISSING_CREDENTIALS = "missing_credentials"
    TOKEN_EXPIRED = "token_expired"
    API_ERROR = "api_error"
    ROUTING_ERROR = "routing_error"
    
    # Other
    PROFILE_ACTIVATED = "profile_activated"
    PROFILE_DEACTIVATED = "profile_deactivated"


def log_channel_event(
    channel: str,
    event_type: str | ChannelEventType,
    sales_profile_slug: Optional[str] = None,
    customer_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    severity: str = "info",
) -> None:
    """
    Registra un evento de canal con contexto estructurado.
    
    Args:
        channel: Nombre del canal (whatsapp, messenger, instagram)
        event_type: Tipo de evento (usar enum ChannelEventType)
        sales_profile_slug: Slug del perfil de venta (si aplica)
        customer_id: ID de cliente (teléfono o ID)
        details: Contexto adicional (JSON-serializable)
        severity: critical, error, warning, info, debug
    """
    event_type_value = event_type.value if isinstance(event_type, ChannelEventType) else event_type
    
    details = details or {}
    timestamp = datetime.now(UTC).isoformat()
    
    # Log basado en severity
    log_message = (
        f"[{channel.upper()}] {event_type_value} | "
        f"ts={timestamp} | "
        f"perfil={sales_profile_slug} | "
        f"customer={customer_id} | "
        f"details={json.dumps(details)}"
    )
    
    if severity == "critical":
        logger.critical(log_message)
    elif severity == "error":
        logger.error(log_message)
    elif severity == "warning":
        logger.warning(log_message)
    elif severity == "debug":
        logger.debug(log_message)
    else:  # info or default
        logger.info(log_message)


def log_webhook_received(
    channel: str,
    message_id: Optional[str],
    sales_profile_slug: Optional[str],
    customer_id: str,
    customer_name: Optional[str] = None,
    message_text: Optional[str] = None,
) -> None:
    """Registra recepción de mensaje de webhook."""
    details = {
        "message_id": message_id,
        "customer_name": customer_name,
        "message_preview": message_text[:50] if message_text else None,
    }
    log_channel_event(
        channel=channel,
        event_type=ChannelEventType.MESSAGE_RECEIVED,
        sales_profile_slug=sales_profile_slug,
        customer_id=customer_id,
        details=details,
    )


def log_webhook_sent(
    channel: str,
    message_id: Optional[str],
    sales_profile_slug: str,
    customer_id: str,
    message_text: Optional[str] = None,
) -> None:
    """Registra envío de mensaje de respuesta."""
    details = {
        "message_id": message_id,
        "message_preview": message_text[:50] if message_text else None,
    }
    log_channel_event(
        channel=channel,
        event_type=ChannelEventType.MESSAGE_SENT,
        sales_profile_slug=sales_profile_slug,
        customer_id=customer_id,
        details=details,
    )


def log_config_change(
    channel: str,
    event_type: ChannelEventType,
    sales_profile_slug: str,
    changed_fields: Optional[Dict[str, tuple[Any, Any]]] = None,
    changed_by: Optional[str] = None,
) -> None:
    """
    Registra cambios de configuración de canal.
    
    Args:
        channel: Canal afectado
        event_type: CONFIG_CREATED, CONFIG_UPDATED, CONFIG_DELETED
        sales_profile_slug: Perfil afectado
        changed_fields: Dict {field: (old_value, new_value)} - no debe incluir tokens!
        changed_by: Usuario que realizó el cambio (admin, system, etc)
    """
    changed_fields = changed_fields or {}
    
    # Nunca loguear valores de tokens, solo que fueron cambiados
    sanitized_changes: Dict[str, tuple[Any, Any]] = {}
    for key, (old_val, new_val) in changed_fields.items():
        if any(x in key.lower() for x in ["token", "password", "secret", "key"]):
            sanitized_changes[key] = ("***REDACTED***", "***REDACTED***")
        else:
            sanitized_changes[key] = (old_val, new_val)
    
    details: Dict[str, Any] = {
        "changed_fields": sanitized_changes,
        "changed_by": changed_by or "system",
    }
    
    log_channel_event(
        channel=channel,
        event_type=event_type,
        sales_profile_slug=sales_profile_slug,
        details=details,
        severity="warning",
    )


def log_connection_test(
    channel: str,
    sales_profile_slug: str,
    success: bool,
    error: Optional[str] = None,
) -> None:
    """Registra resultado de test de conexión."""
    event_type = (
        ChannelEventType.CONNECTION_SUCCESS
        if success
        else ChannelEventType.CONNECTION_FAILED
    )
    details: Dict[str, Any] = {"error": error} if error else {}
    
    log_channel_event(
        channel=channel,
        event_type=event_type,
        sales_profile_slug=sales_profile_slug,
        details=details,
        severity="info" if success else "error",
    )


def log_routing_error(
    channel: str,
    event_type: ChannelEventType,
    account_id: Optional[str],
    customer_id: Optional[str],
    error_message: str,
) -> None:
    """Registra error de enrutamiento de mensaje."""
    details: Dict[str, Any] = {
        "account_id": account_id,
        "error": error_message,
    }
    log_channel_event(
        channel=channel,
        event_type=event_type,
        customer_id=customer_id,
        details=details,
        severity="error",
    )


def log_duplicate_message(
    channel: str,
    message_id: str,
    sales_profile_slug: Optional[str],
    customer_id: Optional[str],
) -> None:
    """Registra mensaje duplicado / deduplicado."""
    details = {"message_id": message_id}
    log_channel_event(
        channel=channel,
        event_type=ChannelEventType.MESSAGE_DUPLICATE,
        sales_profile_slug=sales_profile_slug,
        customer_id=customer_id,
        details=details,
        severity="debug",
    )


class ChannelMetrics:
    """
    Colector de métricas simples para canales.
    
    Uso:
        from app.channel_audit import channel_metrics
        
        channel_metrics.increment_messages_received("whatsapp", "softmobile-bot")
        count = channel_metrics.get_messages_received("whatsapp")
    """
    
    def __init__(self) -> None:
        self.messages_received: Dict[str, int] = {}  # {channel: count}
        self.messages_sent: Dict[str, int] = {}
        self.duplicate_messages: Dict[str, int] = {}
        self.api_errors: Dict[str, int] = {}
        self.profiles_count: Dict[str, int] = {}

    def increment_messages_received(self, channel: str, profile: Optional[str] = None) -> None:
        key = f"{channel}:{profile}" if profile else channel
        self.messages_received[key] = self.messages_received.get(key, 0) + 1

    def increment_messages_sent(self, channel: str, profile: Optional[str] = None) -> None:
        key = f"{channel}:{profile}" if profile else channel
        self.messages_sent[key] = self.messages_sent.get(key, 0) + 1

    def increment_duplicates(self, channel: str) -> None:
        self.duplicate_messages[channel] = self.duplicate_messages.get(channel, 0) + 1

    def increment_api_errors(self, channel: str) -> None:
        self.api_errors[channel] = self.api_errors.get(channel, 0) + 1

    def get_summary(self) -> Dict[str, Any]:
        return {
            "messages_received": dict(self.messages_received),
            "messages_sent": dict(self.messages_sent),
            "duplicate_messages": dict(self.duplicate_messages),
            "api_errors": dict(self.api_errors),
        }

    def reset(self) -> None:
        self.messages_received.clear()
        self.messages_sent.clear()
        self.duplicate_messages.clear()
        self.api_errors.clear()


# Instancia global de métricas
channel_metrics = ChannelMetrics()
