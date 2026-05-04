# pyright: reportAttributeAccessIssue=false, reportArgumentType=false, reportGeneralTypeIssues=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false

"""
Routers para gestión de solicitudes de fotos.

Workflow:
1. Cliente pide fotos → Bot llama a POST /api/photo-requests
2. Sistema crea solicitud → Notifica al agente encargado
3. Agente ve dashboard y carga fotos
4. Sistema envía fotos al cliente (transparente)
5. Agente marca como resuelto
"""

import logging
import json
import smtplib
import ssl
from pathlib import Path
from datetime import datetime, UTC
from email.message import EmailMessage
from urllib.parse import urljoin
from typing import List, Optional, Any, Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PhotoRequest, PhotoRequestMediaItem, SalesProfile, User, Product
from app.schemas.photos import (
    PhotoRequestCreate,
    PhotoRequestUpdate,
    PhotoRequestMediaCreate,
    PhotoRequestMediaResponse,
    PhotoRequestResponse,
    PhotoRequestDetailResponse,
    PhotoRequestSummaryResponse,
    NotifyAgentPayload,
)
from app.auth import check_permission
from app.config_production import prod_settings
from app.utils.s3_storage import get_storage_manager
from app.utils.websocket_manager import get_connection_manager
from app.dependencies.rate_limiting import check_photo_request_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/photo-requests", tags=["Photo Requests"])
UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads" / "photo-requests"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

OPEN_PHOTO_REQUEST_STATUSES = ["pending", "claimed", "awaiting_upload", "in_progress"]

# Initialize storage manager (S3 or local)
storage_manager = get_storage_manager()
ws_manager = get_connection_manager()


def _select_best_agent_for_photo_requests(db: Session) -> Optional[User]:
    active_users = db.query(User).filter(User.is_active == True).all()
    if not active_users:
        return None

    best_user: Optional[User] = None
    best_load: Optional[int] = None

    for user in active_users:
        current_load = db.query(PhotoRequest).filter(
            PhotoRequest.assigned_to_user_id == user.id,
            PhotoRequest.status.in_(OPEN_PHOTO_REQUEST_STATUSES),
        ).count()
        if best_load is None or current_load < best_load:
            best_user = user
            best_load = current_load

    return best_user


def create_photo_request_internal(
    db: Session,
    data: PhotoRequestCreate,
    sales_profile_slug: Optional[str] = None,
    channel: Optional[str] = None,
    customer_name: Optional[str] = None,
) -> PhotoRequest:
    sales_profile = None
    if sales_profile_slug:
        sales_profile = db.query(SalesProfile).filter(
            SalesProfile.slug == sales_profile_slug,
            SalesProfile.active == True,
        ).first()
    if not sales_profile:
        sales_profile = db.query(SalesProfile).filter(SalesProfile.active == True).first()
    if not sales_profile:
        raise HTTPException(status_code=400, detail="No hay perfiles de venta activos para crear la solicitud")

    product_name = data.product_name
    if data.product_id:
        product = db.query(Product).filter(Product.id == data.product_id).first()
        if product and product.nombre:
            product_name = str(product.nombre)

    assigned_user = _select_best_agent_for_photo_requests(db)

    new_request = PhotoRequest(
        customer_id=data.customer_id,
        product_id=data.product_id,
        product_name=product_name,
        color_requested=data.color_requested,
        size_requested=data.size_requested,
        additional_notes=data.additional_notes,
        customer_name=data.customer_name or customer_name,
        origin_channel=data.origin_channel or channel,
        sales_profile_id=sales_profile.id if sales_profile else None,
        assigned_to_user_id=assigned_user.id if assigned_user else None,
        status="pending",
        claimed_at=None,
        last_notified_at=None,
        notification_count=0,
    )

    if assigned_user:
        new_request.first_assigned_at = datetime.now(UTC)

    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    _notify_agent_of_request(
        db,
        new_request,
        sales_profile,
        channel or "unknown",
        customer_name,
    )

    return new_request


def _compute_priority_score(request: PhotoRequest) -> float:
    age_minutes = max(0.0, (datetime.now(UTC) - request.created_at.replace(tzinfo=UTC) if request.created_at and request.created_at.tzinfo is None else datetime.now(UTC) - request.created_at).total_seconds() / 60) if request.created_at else 0.0
    status_boost = {
        "pending": 30.0,
        "claimed": 20.0,
        "awaiting_upload": 15.0,
        "in_progress": 10.0,
        "completed": 0.0,
        "failed": 0.0,
        "declined": 0.0,
    }.get(str(request.status), 0.0)
    return round(age_minutes + status_boost + float(request.notification_count or 0) * 5.0, 2)


def _is_sla_breached(request: PhotoRequest, threshold_minutes: int = 15) -> bool:
    if not request.created_at or str(request.status) in {"completed", "failed", "declined"}:
        return False
    created_at = request.created_at.replace(tzinfo=UTC) if request.created_at.tzinfo is None else request.created_at.astimezone(UTC)
    return (datetime.now(UTC) - created_at).total_seconds() >= threshold_minutes * 60


def _serialize_photo_request_detail(db: Session, req: PhotoRequest) -> PhotoRequestDetailResponse:
    media_items = db.query(PhotoRequestMediaItem).filter(
        PhotoRequestMediaItem.photo_request_id == req.id
    ).all()

    base_payload = PhotoRequestResponse.model_validate(req).model_dump()
    detail = PhotoRequestDetailResponse.model_validate(base_payload)
    detail.media_items = [PhotoRequestMediaResponse.model_validate(m) for m in media_items]
    detail.priority_score = _compute_priority_score(req)
    detail.sla_breached = _is_sla_breached(req)

    if req.assigned_to_user:
        detail.assigned_to_user = {
            "id": req.assigned_to_user.id,
            "name": req.assigned_to_user.username,
            "email": req.assigned_to_user.email,
        }

    return detail


def _parse_json_object(raw: Optional[str]) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except (TypeError, json.JSONDecodeError):
        return {}
    return {}


def _extract_channel_integration(profile: SalesProfile, channel: str) -> Dict[str, Any]:
    config = _parse_json_object(profile.configuracion)
    integrations = config.get("channel_integrations") if isinstance(config.get("channel_integrations"), dict) else {}
    channel_data = integrations.get(channel) if isinstance(integrations, dict) else None
    if isinstance(channel_data, dict):
        return channel_data
    return {}


def _parse_profile_channels(profile: SalesProfile) -> List[str]:
    raw = (profile.canales or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item).strip().lower() for item in parsed if str(item).strip()]
    except (TypeError, json.JSONDecodeError):
        pass
    return [segment.strip().lower() for segment in raw.split(",") if segment.strip()]


def _resolve_request_channel(request: PhotoRequest, sales_profile: SalesProfile) -> str:
    notes = (request.additional_notes or "").lower()
    for channel in ["whatsapp", "messenger", "instagram", "facebook"]:
        if f"channel:{channel}" in notes or f"canal:{channel}" in notes:
            return "messenger" if channel == "facebook" else channel

    profile_channels = _parse_profile_channels(sales_profile)
    if profile_channels:
        first = profile_channels[0]
        return "messenger" if first == "facebook" else first

    return "whatsapp"


def _send_email_notification(assigned_user: User, payload: NotifyAgentPayload) -> bool:
    if not assigned_user.email:
        return False
    if not prod_settings.SMTP_HOST or not prod_settings.SMTP_USER or not prod_settings.SMTP_FROM:
        return False

    subject = f"📸 Nueva solicitud de fotos: {payload.product_name}"
    body = (
        "Se creó una nueva solicitud de fotos.\n\n"
        f"Solicitud ID: {payload.photo_request_id}\n"
        f"Cliente: {payload.customer_name or payload.customer_phone}\n"
        f"Canal: {payload.channel}\n"
        f"Producto: {payload.product_name}\n"
        f"Color: {payload.color_requested or 'No especificado'}\n"
    )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = prod_settings.SMTP_FROM
    message["To"] = assigned_user.email
    message.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP(prod_settings.SMTP_HOST, prod_settings.SMTP_PORT, timeout=10) as server:
        if prod_settings.SMTP_TLS:
            server.starttls(context=context)
        server.login(prod_settings.SMTP_USER, prod_settings.SMTP_PASSWORD)
        server.send_message(message)
    return True


def _notify_agent_of_request(
    db: Session,
    request: PhotoRequest,
    sales_profile: SalesProfile,
    channel: str,
    customer_name: Optional[str] = None,
):
    """
    Notifica al agente encargado sobre nueva solicitud de fotos.

    Actualmente usa email si SMTP está configurado; si no, deja la solicitud
    visible en el dashboard sin incrementar métricas de notificación.
    """
    if not request.assigned_to_user_id:
        logger.warning(f"No assigned agent for photo request {request.id}")
        return

    payload = NotifyAgentPayload(
        photo_request_id=request.id,
        customer_phone=request.customer_id,
        product_name=request.product_name,
        color_requested=request.color_requested,
        sales_profile_slug=sales_profile.slug if sales_profile else "unknown",
        channel=channel,
        customer_name=customer_name,
    )

    try:
        assigned_user = db.query(User).filter(User.id == request.assigned_to_user_id).first()
        if assigned_user and _send_email_notification(assigned_user, payload):
            request.last_notified_at = datetime.now(UTC)
            request.notification_count = int(request.notification_count or 0) + 1
            db.add(request)
            db.commit()
    except Exception as exc:
        logger.warning("No se pudo enviar notificación por email para request %s: %s", request.id, exc)

    logger.info(f"Notifying agent: {payload}")


@router.post("/create", response_model=PhotoRequestResponse)
async def create_photo_request(
    data: PhotoRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    sales_profile_slug: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    customer_name: Optional[str] = Query(None),
    rate_limit_info: Dict[str, Any] = Depends(check_photo_request_rate_limit),
):
    """
    Crear solicitud de fotos (llamado por bot cuando cliente pide).
    
    Workflow:
    1. Bot detecta en mensaje: "Quiero ver fotos del iPhone 15 en gris"
    2. Bot llama a este endpoint con los detalles
    3. Sistema crea PhotoRequest + notifica al agente encargado
    4. Bot responde al cliente: "Dame un momento, estoy tomando fotos..."
    
    Args:
        data: PhotoRequestCreate {customer_id, product_id, product_name, color_requested, ...}
        sales_profile_slug: Slug del perfil que recibió la solicitud
        channel: Sobre qué canal (whatsapp, messenger, instagram)
        customer_name: Nombre del cliente (para referencia)
    
    Returns:
        PhotoRequestResponse con ID de solicitud
    """
    new_request = create_photo_request_internal(
        db=db,
        data=data,
        sales_profile_slug=sales_profile_slug,
        channel=channel,
        customer_name=customer_name,
    )

    logger.info(
        f"Photo request created: {new_request.id} for customer {data.customer_id} "
        f"(product: {data.product_name}, color: {data.color_requested})"
    )

    return PhotoRequestResponse.model_validate(new_request)


@router.get("/summary", response_model=PhotoRequestSummaryResponse)
def get_photo_request_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("photo_requests:list")),
):
    requests = db.query(PhotoRequest).filter(PhotoRequest.status.in_(OPEN_PHOTO_REQUEST_STATUSES)).all()
    assigned_to_me = sum(1 for request in requests if request.assigned_to_user_id == current_user.id)
    overdue_total = sum(1 for request in requests if _is_sla_breached(request))
    awaiting_upload_total = sum(1 for request in requests if str(request.status) == "awaiting_upload")
    return PhotoRequestSummaryResponse(
        pending_total=len(requests),
        assigned_to_me=assigned_to_me,
        overdue_total=overdue_total,
        awaiting_upload_total=awaiting_upload_total,
    )


@router.post("/{photo_request_id}/claim", response_model=PhotoRequestResponse)
async def claim_photo_request(
    photo_request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("photo_requests:update")),
):
    request = db.query(PhotoRequest).filter(PhotoRequest.id == photo_request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Photo request not found")

    request.assigned_to_user_id = current_user.id
    request.claimed_at = datetime.now(UTC)
    if str(request.status) == "pending":
        request.status = "claimed"
    db.add(request)
    db.commit()
    db.refresh(request)
    
    # Broadcast claim event to all connected clients
    await ws_manager.broadcast_photo_event(
        event_type="photo_request.claimed",
        photo_request_id=photo_request_id,
        payload={
            "claimed_by_user_id": current_user.id,
            "claimed_by_name": current_user.email,
            "new_status": request.status
        },
        user_id=current_user.id
    )
    
    return PhotoRequestResponse.model_validate(request)


@router.get("/pending", response_model=List[PhotoRequestDetailResponse])
def list_pending_photo_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("photo_requests:list")),
    assigned_to_me: bool = Query(False),
    status: Optional[str] = Query(None),
):
    """
    Dashboard para agentes: listar solicitudes pendientes.
    
    Args:
        assigned_to_me: Si True, solo mis solicitudes
        status: Filtrar por status (pending, in_progress, completed, failed)
    
    Returns:
        Lista de PhotoRequestDetailResponse con contexto completo
    """
    query = db.query(PhotoRequest)

    if assigned_to_me:
        query = query.filter(PhotoRequest.assigned_to_user_id == current_user.id)

    if status:
        query = query.filter(PhotoRequest.status == status)
    else:
        # Por defecto, mostrar no-resueltos
        query = query.filter(PhotoRequest.status.in_(OPEN_PHOTO_REQUEST_STATUSES))

    requests = query.limit(200).all()
    requests.sort(key=lambda req: (_is_sla_breached(req), _compute_priority_score(req)), reverse=True)
    return [_serialize_photo_request_detail(db, req) for req in requests[:100]]


@router.get("/{photo_request_id}", response_model=PhotoRequestDetailResponse)
def get_photo_request(
    photo_request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("photo_requests:read")),
):
    """Obtener detalle de una solicitud de fotos."""
    request = db.query(PhotoRequest).filter(PhotoRequest.id == photo_request_id).first()

    if not request:
        raise HTTPException(status_code=404, detail="Photo request not found")

    return _serialize_photo_request_detail(db, request)


@router.put("/{photo_request_id}", response_model=PhotoRequestResponse)
def update_photo_request(
    photo_request_id: int,
    data: PhotoRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("photo_requests:update")),
):
    """
    Actualizar estado de solicitud (por agente).
    
    Campos actualizables:
    - status: "in_progress", "completed", "failed", "declined"
    - completion_notes: notas sobre qué se hizo o por qué falló
    
    Cuando status="completed" debe haberse enviado media al cliente
    (usar endpoint /send-to-customer para completar ese flujo).
    """
    request = db.query(PhotoRequest).filter(PhotoRequest.id == photo_request_id).first()

    if not request:
        raise HTTPException(status_code=404, detail="Photo request not found")

    # Validar permisos
    if request.assigned_to_user_id and request.assigned_to_user_id != current_user.id:
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not assigned to you")

    if data.status:
        if data.status == "completed":
            unsent_media_count = db.query(PhotoRequestMediaItem).filter(
                PhotoRequestMediaItem.photo_request_id == photo_request_id,
                PhotoRequestMediaItem.sent_to_customer_at == None,
            ).count()
            if unsent_media_count > 0:
                raise HTTPException(
                    status_code=400,
                    detail="Hay fotos sin enviar al cliente. Usa /send-to-customer antes de completar.",
                )

        request.status = data.status

        if data.status == "completed":
            request.resolved_at = datetime.now(UTC)

        elif data.status in ["failed", "declined"]:
            request.resolved_at = datetime.now(UTC)

    if data.assigned_to_user_id is not None:
        request.assigned_to_user_id = data.assigned_to_user_id
        request.claimed_at = datetime.now(UTC)

    if data.completion_notes:
        request.completion_notes = data.completion_notes

    db.add(request)
    db.commit()
    db.refresh(request)

    logger.info(f"Photo request {photo_request_id} updated: status={request.status}")

    return PhotoRequestResponse.model_validate(request)


@router.post("/{photo_request_id}/media")
def upload_media_to_request(
    photo_request_id: int,
    data: PhotoRequestMediaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("photo_requests:upload")),
) -> PhotoRequestMediaResponse:
    """
    Agente carga una foto/video para la solicitud.
    
    Args:
        media_url: URL de la imagen (S3, Cloudinary, etc.)
        media_type: "photo", "video", "360_view"
        metadata: {width, height, camera_angle, etc}
    
    Returns:
        PhotoRequestMediaResponse
    """
    request = db.query(PhotoRequest).filter(PhotoRequest.id == photo_request_id).first()

    if not request:
        raise HTTPException(status_code=404, detail="Photo request not found")

    # Crear media item
    media = PhotoRequestMediaItem(
        photo_request_id=photo_request_id,
        media_url=data.media_url,
        media_type=data.media_type,
        media_metadata=data.metadata or {},
        uploaded_by_user_id=current_user.id,
    )

    db.add(media)

    # Actualizar status a in_progress si estaba pending
    if request.status == "pending":
        request.status = "awaiting_upload"

    if request.status in {"claimed", "awaiting_upload"}:
        request.status = "in_progress"

    db.add(request)
    db.commit()
    db.refresh(media)

    logger.info(f"Media uploaded for request {photo_request_id}: {data.media_url}")

    return PhotoRequestMediaResponse.model_validate(media)


@router.post("/{photo_request_id}/upload-file", response_model=PhotoRequestMediaResponse)
async def upload_binary_media_to_request(
    photo_request_id: int,
    request_http: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("photo_requests:upload")),
) -> PhotoRequestMediaResponse:
    request = db.query(PhotoRequest).filter(PhotoRequest.id == photo_request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Photo request not found")

    max_size_bytes = int(prod_settings.MAX_UPLOAD_SIZE_MB) * 1024 * 1024
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    if len(contents) > max_size_bytes:
        raise HTTPException(status_code=400, detail=f"Archivo excede el máximo de {prod_settings.MAX_UPLOAD_SIZE_MB}MB")

    try:
        # Upload to S3 or local storage
        media_url = await storage_manager.upload_file(
            file_content=contents,
            filename=file.filename or "image.jpg",
            photo_request_id=photo_request_id,
            content_type=file.content_type or "application/octet-stream"
        )
        
        storage_type = "s3" if storage_manager.enable_s3 else "local"
        
        media = PhotoRequestMediaItem(
            photo_request_id=photo_request_id,
            media_url=media_url,
            media_type="photo" if (file.content_type or "").startswith("image/") else "video",
            file_size_bytes=len(contents),
            media_metadata={
                "filename": file.filename,
                "content_type": file.content_type,
                "storage": storage_type,
            },
            uploaded_by_user_id=current_user.id,
        )

        db.add(media)
        if request.status in {"pending", "claimed", "awaiting_upload"}:
            request.status = "in_progress"
        db.add(request)
        db.commit()
        db.refresh(media)
        
        # Broadcast upload event
        await ws_manager.broadcast_photo_event(
            event_type="photo_request.media_uploaded",
            photo_request_id=photo_request_id,
            payload={
                "media_id": media.id,
                "media_type": media.media_type,
                "uploaded_by_user_id": current_user.id,
                "new_status": request.status
            },
            user_id=current_user.id
        )
        
        return PhotoRequestMediaResponse.model_validate(media)
        
    except Exception as e:
        logger.error(f"Upload failed for request {photo_request_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/{photo_request_id}/send-to-customer")
async def send_photos_to_customer(
    photo_request_id: int,
    request_http: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("photo_requests:send")),
):
    """
    ACCIÓN CRÍTICA: Enviar fotos al cliente por el canal original.
    
    Este endpoint:
    1. Obtiene todas las fotos cargadas en la solicitud
    2. Obtiene el perfil de venta + channel original
    3. Envía las fotos directamente al cliente (pareciera que del bot)
    4. Marca media items como enviados
    5. Marca solicitud como completed
    
    Da la ilusión de que el bot fue quien tomó las fotos,
    pero en realidad fue el agente.
    """
    request = db.query(PhotoRequest).filter(PhotoRequest.id == photo_request_id).first()

    if not request:
        raise HTTPException(status_code=404, detail="Photo request not found")

    # Obtener media items
    media_items = db.query(PhotoRequestMediaItem).filter(
        PhotoRequestMediaItem.photo_request_id == photo_request_id,
        PhotoRequestMediaItem.sent_to_customer_at == None  # No enviados
    ).all()

    if not media_items:
        raise HTTPException(status_code=400, detail="No media items to send")

    # Obtener perfil de venta
    sales_profile = db.query(SalesProfile).filter(
        SalesProfile.id == request.sales_profile_id
    ).first()

    if not sales_profile:
        raise HTTPException(status_code=400, detail="Sales profile not found")

    channel = _resolve_request_channel(request, sales_profile)
    integration_config = _extract_channel_integration(sales_profile, channel)

    def _public_media_url(media_url: str) -> str:
        if media_url.startswith(("http://", "https://")):
            return media_url
        return urljoin(str(request_http.base_url), media_url.lstrip("/"))

    def _outbound_media_type(media_type: str) -> str:
        return "video" if str(media_type).lower() == "video" else "image"

    async def _send_whatsapp_media_items() -> None:
        token = str(integration_config.get("access_token") or getattr(prod_settings, "WHATSAPP_ACCESS_TOKEN", "") or "").strip()
        phone_number_id = str(integration_config.get("phone_number_id") or getattr(prod_settings, "WHATSAPP_PHONE_NUMBER_ID", "") or "").strip()
        if not token or not phone_number_id:
            raise HTTPException(status_code=503, detail="Falta configurar credenciales de WhatsApp")

        url = f"https://graph.facebook.com/v23.0/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            for media in media_items:
                outbound_type = _outbound_media_type(media.media_type)
                payload = {
                    "messaging_product": "whatsapp",
                    "to": request.customer_id,
                    "type": outbound_type,
                    outbound_type: {"link": _public_media_url(media.media_url)},
                }
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code >= 400:
                    raise HTTPException(status_code=502, detail=f"Error enviando media por WhatsApp: {response.text}")

            caption = f"Aquí tienes las fotos de {request.product_name}{f' en {request.color_requested}' if request.color_requested else ''}."
            text_payload = {
                "messaging_product": "whatsapp",
                "to": request.customer_id,
                "type": "text",
                "text": {"body": caption},
            }
            response = await client.post(url, headers=headers, json=text_payload)
            if response.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"Error enviando texto por WhatsApp: {response.text}")

    async def _send_meta_page_media_items(meta_channel: str) -> None:
        token = str(integration_config.get("page_access_token") or getattr(prod_settings, "META_PAGE_ACCESS_TOKEN", "") or "").strip()
        if not token:
            raise HTTPException(status_code=503, detail="Falta configurar META_PAGE_ACCESS_TOKEN")

        url = "https://graph.facebook.com/v23.0/me/messages"
        params = {"access_token": token}

        async with httpx.AsyncClient(timeout=20.0) as client:
            for media in media_items:
                outbound_type = _outbound_media_type(media.media_type)
                payload = {
                    "messaging_type": "RESPONSE",
                    "recipient": {"id": request.customer_id},
                    "message": {
                        "attachment": {
                            "type": outbound_type,
                            "payload": {"url": _public_media_url(media.media_url), "is_reusable": True},
                        }
                    },
                }
                response = await client.post(url, params=params, json=payload)
                if response.status_code >= 400:
                    raise HTTPException(status_code=502, detail=f"Error enviando media por {meta_channel}: {response.text}")

            caption = f"Aquí tienes las fotos de {request.product_name}{f' en {request.color_requested}' if request.color_requested else ''}."
            text_payload = {
                "messaging_type": "RESPONSE",
                "recipient": {"id": request.customer_id},
                "message": {"text": caption},
            }
            response = await client.post(url, params=params, json=text_payload)
            if response.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"Error enviando texto por {meta_channel}: {response.text}")

    try:
        logger.info(
            "Sending %s photos to customer %s via channel %s",
            len(media_items),
            request.customer_id,
            channel,
        )

        if channel == "whatsapp":
            await _send_whatsapp_media_items()
        elif channel in ["messenger", "instagram", "facebook"]:
            await _send_meta_page_media_items(channel)
        else:
            raise HTTPException(status_code=400, detail=f"Canal no soportado para envío de media: {channel}")

        for media in media_items:
            media.sent_to_customer_at = datetime.now(UTC)
            media.customer_viewed = False
            db.add(media)

        request.status = "completed"
        request.resolved_at = datetime.now(UTC)
        request.photo_urls = [m.media_url for m in media_items]

        db.add(request)
        db.commit()

        return {
            "status": "success",
            "message": f"Enviadas {len(media_items)} fotos al cliente",
            "photo_request_id": photo_request_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending photos: {e}")
        raise HTTPException(status_code=500, detail="Error interno enviando fotos al cliente")


__all__ = ["router"]
