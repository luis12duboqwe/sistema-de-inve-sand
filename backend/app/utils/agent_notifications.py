"""
Agent notification system for photo requests and urgent alerts.

Supports WhatsApp notifications to designated admin phone numbers.
"""

import logging
from typing import Optional, List, Callable, Awaitable, Any
from datetime import datetime

logger = logging.getLogger(__name__)


async def notify_agent_photo_request_created(
    photo_request_id: int,
    product_name: str,
    customer_name: str,
    color_requested: Optional[str],
    origin_channel: str,
    assigned_to_user_email: str,
    admin_phones: List[str],
    send_message_func: Optional[Callable[..., Awaitable[Any]]] = None,
) -> Optional[bool]:
    """
    Notify agents when a new photo request is created via WhatsApp.
    
    Args:
        photo_request_id: ID of the photo request
        product_name: Name of product requested
        customer_name: Customer name
        color_requested: Color/variant requested
        origin_channel: Where request came from (whatsapp, facebook, instagram)
        assigned_to_user_email: Assigned agent email
        admin_phones: List of admin phone numbers to notify
        send_message_func: Async function to send WhatsApp message
    """
    if not admin_phones or not send_message_func:
        logger.warning("Admin phones or send function not configured for photo request notifications")
        return
    
    color_info = f" ({color_requested})" if color_requested else ""
    message = (
        f"📸 *Nueva Solicitud de Fotos*\n"
        f"ID: #{photo_request_id}\n"
        f"Producto: {product_name}{color_info}\n"
        f"Cliente: {customer_name}\n"
        f"Canal: {origin_channel.upper()}\n"
        f"Asignado a: {assigned_to_user_email}\n"
        f"Hora: {datetime.now().strftime('%H:%M:%S')}\n"
        f"\n⏱️  *Establece un límite de 30 minutos para responder*"
    )
    
    for phone in admin_phones:
        try:
            await send_message_func(phone, message)
            logger.info(f"✅ Notified agent {phone} about photo request #{photo_request_id}")
        except Exception as e:
            logger.error(f"Failed to notify agent {phone}: {e}")
    
    return True


async def notify_sla_breach(
    photo_request_id: int,
    product_name: str,
    customer_name: str,
    time_pending_minutes: int,
    assigned_to_user_email: str,
    admin_phones: List[str],
    send_message_func: Optional[Callable[..., Awaitable[Any]]] = None,
) -> None:
    """
    Alert when photo request SLA is breached (>2 hours without response).
    """
    if not admin_phones or not send_message_func:
        return
    
    message = (
        f"⚠️  *SLA VENCIDA - Solicitud de Fotos*\n"
        f"ID: #{photo_request_id}\n"
        f"Producto: {product_name}\n"
        f"Cliente: {customer_name}\n"
        f"Tiempo pendiente: {time_pending_minutes} minutos\n"
        f"Asignado a: {assigned_to_user_email}\n"
        f"\n🚨 *Requiere atención inmediata*"
    )
    
    for phone in admin_phones:
        try:
            await send_message_func(phone, message)
            logger.warning(f"⚠️  SLA breach notification sent to {phone} for request #{photo_request_id}")
        except Exception as e:
            logger.error(f"Failed to send SLA breach notification to {phone}: {e}")


async def notify_media_uploaded(
    photo_request_id: int,
    product_name: str,
    customer_name: str,
    uploaded_by: str,
    admin_phones: List[str],
    send_message_func: Optional[Callable[..., Awaitable[Any]]] = None,
) -> None:
    """
    Notify when media is uploaded to a photo request.
    """
    if not admin_phones or not send_message_func:
        return
    
    message = (
        f"📤 *Foto Cargada*\n"
        f"Solicitud ID: #{photo_request_id}\n"
        f"Producto: {product_name}\n"
        f"Cliente: {customer_name}\n"
        f"Cargado por: {uploaded_by}\n"
        f"\n💡 Próximo paso: *Enviar al cliente cuando esté listo*"
    )
    
    for phone in admin_phones:
        try:
            await send_message_func(phone, message)
            logger.info(f"Media upload notification sent to {phone}")
        except Exception as e:
            logger.error(f"Failed to notify admin {phone}: {e}")
