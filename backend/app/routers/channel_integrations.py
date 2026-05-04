from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.config_production import prod_settings
from app.database import get_db
from app.models import SalesProfile, ProcessedMessage
from app.routers.ai_intelligence import handle_message_without_n8n
from app.schemas import AIHandleMessageRequest


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/channels", tags=["Channel Integrations"])


@dataclass
class IncomingEvent:
    channel: str
    external_message_id: Optional[str]
    account_id: Optional[str]
    customer_id: str
    customer_name: Optional[str]
    text: str


def _is_configured(name: str) -> bool:
    value = getattr(prod_settings, name, "")
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return bool(value)


def _channel_health_snapshot() -> Dict[str, Any]:
    has_verify_token = any(
        [
            _is_configured("META_VERIFY_TOKEN"),
            _is_configured("WHATSAPP_VERIFY_TOKEN"),
            _is_configured("MESSENGER_VERIFY_TOKEN"),
            _is_configured("INSTAGRAM_VERIFY_TOKEN"),
        ]
    )
    has_sales_profile_default = any(
        [
            _is_configured("CHANNEL_DEFAULT_SALES_PROFILE_SLUG"),
            _is_configured("WHATSAPP_DEFAULT_SALES_PROFILE_SLUG"),
            _is_configured("MESSENGER_DEFAULT_SALES_PROFILE_SLUG"),
            _is_configured("INSTAGRAM_DEFAULT_SALES_PROFILE_SLUG"),
        ]
    )

    whatsapp_ready = _is_configured("WHATSAPP_ACCESS_TOKEN") and _is_configured("WHATSAPP_PHONE_NUMBER_ID")
    messenger_ready = _is_configured("META_PAGE_ACCESS_TOKEN")
    instagram_ready = _is_configured("META_PAGE_ACCESS_TOKEN")

    missing_global: List[str] = []
    if not has_verify_token:
        missing_global.append("META_VERIFY_TOKEN (o token verify por canal)")
    if not has_sales_profile_default:
        missing_global.append("CHANNEL_DEFAULT_SALES_PROFILE_SLUG (o slug por canal)")

    channels = {
        "whatsapp": {
            "ready": whatsapp_ready,
            "missing": [
                key
                for key, configured in {
                    "WHATSAPP_ACCESS_TOKEN": _is_configured("WHATSAPP_ACCESS_TOKEN"),
                    "WHATSAPP_PHONE_NUMBER_ID": _is_configured("WHATSAPP_PHONE_NUMBER_ID"),
                }.items()
                if not configured
            ],
        },
        "messenger": {
            "ready": messenger_ready,
            "missing": [] if messenger_ready else ["META_PAGE_ACCESS_TOKEN"],
        },
        "instagram": {
            "ready": instagram_ready,
            "missing": [] if instagram_ready else ["META_PAGE_ACCESS_TOKEN"],
        },
    }

    ready = has_verify_token and has_sales_profile_default and any(
        [channels["whatsapp"]["ready"], channels["messenger"]["ready"], channels["instagram"]["ready"]]
    )

    return {
        "status": "ok",
        "ready": ready,
        "global": {
            "has_verify_token": has_verify_token,
            "has_default_sales_profile": has_sales_profile_default,
            "signature_validation_enabled": _is_configured("META_APP_SECRET"),
            "message_ttl_seconds": int(getattr(prod_settings, "CHANNEL_MESSAGE_TTL_SECONDS", 600) or 600),
            "missing": missing_global,
        },
        "channels": channels,
    }


def _verify_token_for_channel(channel: str) -> str:
    channel_upper = channel.upper()
    specific_token = getattr(prod_settings, f"{channel_upper}_VERIFY_TOKEN", "")
    generic_token = getattr(prod_settings, "META_VERIFY_TOKEN", "")
    token = specific_token or generic_token
    if not token:
        raise HTTPException(
            status_code=503,
            detail=f"Falta configurar {channel_upper}_VERIFY_TOKEN o META_VERIFY_TOKEN",
        )
    return token


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


def _channel_candidates(profile: SalesProfile, channel: str, account_id: Optional[str]) -> bool:
    integration = _extract_channel_integration(profile, channel)
    if not integration:
        return False

    if account_id:
        if channel == "whatsapp":
            configured_account = str(integration.get("phone_number_id") or "").strip()
            return bool(configured_account and hmac.compare_digest(configured_account, account_id))

        configured_ids = [
            str(integration.get("page_id") or "").strip(),
            str(integration.get("instagram_account_id") or "").strip(),
        ]
        return any(configured_id and hmac.compare_digest(configured_id, account_id) for configured_id in configured_ids)

    return True


def _resolve_profile_for_event(db: Session, event: IncomingEvent) -> tuple[str, Dict[str, Any]]:
    active_profiles = db.query(SalesProfile).filter(SalesProfile.active == True).all()

    for profile in active_profiles:
        if _channel_candidates(profile, event.channel, event.account_id):
            return str(profile.slug), _extract_channel_integration(profile, event.channel)

    return _resolve_default_sales_profile_slug(event.channel), {}


def _collect_channel_verify_tokens(db: Session, channel: str) -> List[str]:
    channel_upper = channel.upper()
    tokens = {
        str(getattr(prod_settings, f"{channel_upper}_VERIFY_TOKEN", "") or "").strip(),
        str(getattr(prod_settings, "META_VERIFY_TOKEN", "") or "").strip(),
    }

    active_profiles = db.query(SalesProfile).filter(SalesProfile.active == True).all()
    for profile in active_profiles:
        integration = _extract_channel_integration(profile, channel)
        token = str(integration.get("verify_token") or "").strip()
        if token:
            tokens.add(token)

    return [token for token in tokens if token]


def _resolve_default_sales_profile_slug(channel: str) -> str:
    channel_upper = channel.upper()
    specific = getattr(prod_settings, f"{channel_upper}_DEFAULT_SALES_PROFILE_SLUG", "")
    generic = getattr(prod_settings, "CHANNEL_DEFAULT_SALES_PROFILE_SLUG", "")
    value = (specific or generic).strip()
    if not value:
        raise HTTPException(
            status_code=503,
            detail=(
                "Falta configurar CHANNEL_DEFAULT_SALES_PROFILE_SLUG "
                f"o {channel_upper}_DEFAULT_SALES_PROFILE_SLUG"
            ),
        )
    return value


def _verify_meta_signature(raw_body: bytes, signature_header: Optional[str]) -> None:
    app_secret = (getattr(prod_settings, "META_APP_SECRET", "") or "").strip()
    if not app_secret:
        return

    if not signature_header:
        raise HTTPException(status_code=401, detail="Falta X-Hub-Signature-256")

    if not signature_header.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Formato de firma inválido")

    expected = hmac.new(
        app_secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    provided = signature_header.replace("sha256=", "", 1).strip()
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=401, detail="Firma inválida")


def _get_processed_message_cache(request: Request) -> Dict[str, datetime]:
    cache = getattr(request.app.state, "channel_processed_messages", None)
    if cache is None:
        cache = {}
        request.app.state.channel_processed_messages = cache
    return cache


def _is_duplicate_message(request: Request, message_id: Optional[str]) -> bool:
    if not message_id:
        return False

    ttl_seconds = int(getattr(prod_settings, "CHANNEL_MESSAGE_TTL_SECONDS", 600) or 600)
    ttl_seconds = max(60, ttl_seconds)
    now = datetime.now(UTC)
    expires = now + timedelta(seconds=ttl_seconds)

    cache = _get_processed_message_cache(request)
    expired_keys = [key for key, expiry in cache.items() if expiry <= now]
    for key in expired_keys:
        cache.pop(key, None)

    if message_id in cache:
        return True

    cache[message_id] = expires
    return False


def _is_duplicate_message_db(db: Session, message_id: Optional[str], channel: str, customer_phone: Optional[str] = None) -> bool:
    """
    Verifica si un mensaje ya fue procesado usando la base de datos.
    
    Esto permite deduplicación persistente entre reinicios del servidor.
    Los mensajes expirados se limpian automáticamente según TTL.
    """
    if not message_id:
        return False

    ttl_seconds = int(getattr(prod_settings, "CHANNEL_MESSAGE_TTL_SECONDS", 600) or 600)
    ttl_seconds = max(60, ttl_seconds)
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=ttl_seconds)

    try:
        # Limpiar mensajes expirados
        db.query(ProcessedMessage).filter(ProcessedMessage.expires_at <= now).delete()
        db.commit()
    except Exception as e:
        logger.warning(f"Error cleaning expired messages: {e}")
        db.rollback()

    # Verificar si ya existe
    existing = db.query(ProcessedMessage).filter(
        ProcessedMessage.message_id == message_id
    ).first()

    if existing:
        return True

    # Crear nuevo registro
    try:
        new_message = ProcessedMessage(
            message_id=message_id,
            channel=channel,
            customer_phone=customer_phone,
            expires_at=expires_at,
        )
        db.add(new_message)
        db.commit()
        return False
    except Exception as e:
        logger.warning(f"Error recording processed message: {e}")
        db.rollback()
        # En caso de error, fallback a cache en memoria
        return _is_duplicate_message(Request, message_id)


def _extract_whatsapp_events(payload: Dict[str, Any]) -> List[IncomingEvent]:
    events: List[IncomingEvent] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            metadata = value.get("metadata") or {}
            account_id = str(metadata.get("phone_number_id") or "").strip() or None
            contacts = value.get("contacts", [])
            name_by_waid = {
                str(contact.get("wa_id")): (contact.get("profile") or {}).get("name")
                for contact in contacts
                if contact.get("wa_id")
            }

            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue

                sender = str(message.get("from") or "").strip()
                text = ((message.get("text") or {}).get("body") or "").strip()
                if not sender or not text:
                    continue

                events.append(
                    IncomingEvent(
                        channel="whatsapp",
                        external_message_id=message.get("id"),
                        account_id=account_id,
                        customer_id=sender,
                        customer_name=name_by_waid.get(sender),
                        text=text,
                    )
                )
    return events


def _extract_meta_page_events(payload: Dict[str, Any], channel: str) -> List[IncomingEvent]:
    events: List[IncomingEvent] = []
    for entry in payload.get("entry", []):
        entry_id = str(entry.get("id") or "").strip()
        for event in entry.get("messaging", []):
            message = event.get("message") or {}
            text = (message.get("text") or "").strip()
            sender = str((event.get("sender") or {}).get("id") or "").strip()
            recipient_id = str((event.get("recipient") or {}).get("id") or "").strip()
            if not sender or not text:
                continue

            events.append(
                IncomingEvent(
                    channel=channel,
                    external_message_id=message.get("mid"),
                    account_id=entry_id or recipient_id or None,
                    customer_id=sender,
                    customer_name=None,
                    text=text,
                )
            )
    return events


def _normalize_channel_payload(payload: Dict[str, Any], channel: str) -> List[IncomingEvent]:
    if channel == "whatsapp":
        return _extract_whatsapp_events(payload)
    return _extract_meta_page_events(payload, channel=channel)


async def _send_whatsapp_reply(to_phone: str, text: str, integration_config: Optional[Dict[str, Any]] = None) -> None:
    integration_config = integration_config or {}
    token = str(integration_config.get("access_token") or getattr(prod_settings, "WHATSAPP_ACCESS_TOKEN", "") or "").strip()
    phone_number_id = str(integration_config.get("phone_number_id") or getattr(prod_settings, "WHATSAPP_PHONE_NUMBER_ID", "") or "").strip()
    if not token or not phone_number_id:
        raise HTTPException(
            status_code=503,
            detail="Falta configurar WHATSAPP_ACCESS_TOKEN y/o WHATSAPP_PHONE_NUMBER_ID",
        )

    url = f"https://graph.facebook.com/v23.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": text},
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"Error enviando WhatsApp: {response.status_code} {response.text}",
            )


async def _send_meta_page_reply(
    recipient_id: str,
    text: str,
    channel: str,
    integration_config: Optional[Dict[str, Any]] = None,
) -> None:
    integration_config = integration_config or {}
    token = str(integration_config.get("page_access_token") or getattr(prod_settings, "META_PAGE_ACCESS_TOKEN", "") or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Falta configurar META_PAGE_ACCESS_TOKEN")

    url = "https://graph.facebook.com/v23.0/me/messages"
    payload = {
        "messaging_type": "RESPONSE",
        "recipient": {"id": recipient_id},
        "message": {"text": text},
    }

    params = {"access_token": token}

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(url, params=params, json=payload)
        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"Error enviando respuesta {channel}: {response.status_code} {response.text}",
            )


async def _send_channel_reply(
    channel: str,
    recipient: str,
    text: str,
    integration_config: Optional[Dict[str, Any]] = None,
) -> None:
    if channel == "whatsapp":
        await _send_whatsapp_reply(recipient, text, integration_config)
        return
    await _send_meta_page_reply(recipient, text, channel, integration_config)


async def _process_incoming_event(
    event: IncomingEvent,
    db: Session,
) -> Dict[str, Any]:
    sales_profile_slug, integration_config = _resolve_profile_for_event(db, event)

    ai_payload = AIHandleMessageRequest(
        sales_profile_slug=sales_profile_slug,
        customer_phone=event.customer_id,
        customer_name=event.customer_name,
        message_content=event.text,
        order_intent=None,
    )

    ai_result = handle_message_without_n8n(ai_payload, db, None)
    await _send_channel_reply(event.channel, event.customer_id, ai_result.reply, integration_config)

    return {
        "channel": event.channel,
        "sales_profile_slug": sales_profile_slug,
        "account_id": event.account_id,
        "customer_id": event.customer_id,
        "external_message_id": event.external_message_id,
        "reply_preview": ai_result.reply[:120],
        "tokens_used": ai_result.tokens_used,
    }


async def _handle_channel_webhook(
    channel: str,
    request: Request,
    db: Session,
) -> Dict[str, Any]:
    raw_body = await request.body()
    signature_header = request.headers.get("X-Hub-Signature-256")
    _verify_meta_signature(raw_body, signature_header)

    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"JSON inválido: {exc}") from exc

    events = _normalize_channel_payload(payload, channel)
    processed: List[Dict[str, Any]] = []
    skipped_duplicates = 0
    failed: List[Dict[str, str]] = []

    for event in events:
        # Use DB-backed deduplication for persistent checking
        if _is_duplicate_message_db(db, event.external_message_id, channel, event.customer_id):
            skipped_duplicates += 1
            continue

        try:
            result = await _process_incoming_event(event, db)
            processed.append(result)
        except HTTPException as exc:
            logger.warning("Error de integración en %s: %s", channel, exc.detail)
            failed.append({"customer_id": event.customer_id, "error": str(exc.detail)})
        except Exception as exc:  # pragma: no cover - defensa final
            logger.exception("Error inesperado procesando mensaje de %s", channel)
            failed.append({"customer_id": event.customer_id, "error": str(exc)})

    return {
        "status": "ok",
        "channel": channel,
        "processed_count": len(processed),
        "skipped_duplicates": skipped_duplicates,
        "failed_count": len(failed),
        "processed": processed,
        "failed": failed,
    }


@router.get("/whatsapp/webhook")
def verify_whatsapp_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
    db: Session = Depends(get_db),
):
    valid_tokens = _collect_channel_verify_tokens(db, "whatsapp")
    if not valid_tokens:
        expected_token = _verify_token_for_channel("whatsapp")
        valid_tokens = [expected_token]

    is_valid = any(hmac.compare_digest(hub_verify_token, token) for token in valid_tokens)
    if hub_mode == "subscribe" and is_valid:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Webhook verify token inválido")


@router.get("/messenger/webhook")
def verify_messenger_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
    db: Session = Depends(get_db),
):
    valid_tokens = _collect_channel_verify_tokens(db, "messenger")
    if not valid_tokens:
        expected_token = _verify_token_for_channel("messenger")
        valid_tokens = [expected_token]

    is_valid = any(hmac.compare_digest(hub_verify_token, token) for token in valid_tokens)
    if hub_mode == "subscribe" and is_valid:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Webhook verify token inválido")


@router.get("/instagram/webhook")
def verify_instagram_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
    db: Session = Depends(get_db),
):
    valid_tokens = _collect_channel_verify_tokens(db, "instagram")
    if not valid_tokens:
        expected_token = _verify_token_for_channel("instagram")
        valid_tokens = [expected_token]

    is_valid = any(hmac.compare_digest(hub_verify_token, token) for token in valid_tokens)
    if hub_mode == "subscribe" and is_valid:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Webhook verify token inválido")


def _channel_health_snapshot_with_profiles(db: Session) -> Dict[str, Any]:
    snapshot = _channel_health_snapshot()

    profile_checks: List[Dict[str, Any]] = []
    active_profiles = db.query(SalesProfile).filter(SalesProfile.active == True).all()
    for profile in active_profiles:
        profile_config = _parse_json_object(profile.configuracion)
        integrations = profile_config.get("channel_integrations") if isinstance(profile_config.get("channel_integrations"), dict) else {}
        if not isinstance(integrations, dict) or not integrations:
            continue

        channels_info: Dict[str, Dict[str, Any]] = {}
        for channel in ["whatsapp", "messenger", "instagram"]:
            channel_config = integrations.get(channel)
            if not isinstance(channel_config, dict):
                continue

            if channel == "whatsapp":
                missing = [
                    key
                    for key in ["phone_number_id", "access_token"]
                    if not str(channel_config.get(key) or "").strip()
                ]
                has_mapping = bool(str(channel_config.get("phone_number_id") or "").strip())
            elif channel == "messenger":
                missing = [
                    key
                    for key in ["page_id", "page_access_token"]
                    if not str(channel_config.get(key) or "").strip()
                ]
                has_mapping = bool(str(channel_config.get("page_id") or "").strip())
            else:
                missing = [
                    key
                    for key in ["instagram_account_id", "page_access_token"]
                    if not str(channel_config.get(key) or "").strip()
                ]
                has_mapping = bool(str(channel_config.get("instagram_account_id") or "").strip())

            channels_info[channel] = {
                "ready": len(missing) == 0,
                "has_mapping": has_mapping,
                "missing": missing,
            }

        if channels_info:
            profile_checks.append(
                {
                    "sales_profile_slug": profile.slug,
                    "sales_profile_name": profile.name,
                    "channels": channels_info,
                }
            )

    snapshot["profiles"] = profile_checks
    return snapshot


@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    return await _handle_channel_webhook("whatsapp", request, db)


@router.post("/messenger/webhook")
async def messenger_webhook(request: Request, db: Session = Depends(get_db)):
    return await _handle_channel_webhook("messenger", request, db)


@router.post("/instagram/webhook")
async def instagram_webhook(request: Request, db: Session = Depends(get_db)):
    return await _handle_channel_webhook("instagram", request, db)


@router.get("/health")
def channels_health(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Diagnóstico de configuración para integración automática de canales."""
    return _channel_health_snapshot_with_profiles(db)


@router.post("/test-connection/{sales_profile_slug}/{channel}")
async def test_channel_connection(
    sales_profile_slug: str,
    channel: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Prueba la conexión a un canal específico para un perfil.
    
    Valida que:
    1. El perfil existe y está activo
    2. El canal está configurado en el perfil
    3. Las credenciales permiten conectar a Meta API
    
    Returns:
        {
            "status": "success" | "error",
            "channel": "whatsapp" | "messenger" | "instagram",
            "sales_profile_slug": "...",
            "details": "Descripción del resultado",
            "timestamp": "ISO 8601"
        }
    """
    profile = db.query(SalesProfile).filter(
        SalesProfile.slug == sales_profile_slug,
        SalesProfile.active == True
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail=f"Perfil {sales_profile_slug} no encontrado")
    
    channel_lower = channel.lower()
    if channel_lower not in ["whatsapp", "messenger", "instagram", "facebook"]:
        raise HTTPException(status_code=400, detail=f"Canal inválido: {channel}")
    
    # Normalize channel name
    if channel_lower == "facebook":
        channel_lower = "messenger"
    
    # Extract config
    config = json.loads(profile.configuracion) if profile.configuracion else {}
    integrations = config.get("channel_integrations", {})
    channel_config = integrations.get(channel_lower, {})
    
    if not channel_config:
        return {
            "status": "error",
            "channel": channel_lower,
            "sales_profile_slug": sales_profile_slug,
            "details": f"Canal {channel_lower} no configurado en el perfil",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    
    # Validate required fields exist
    required_fields = {
        "whatsapp": ["phone_number_id", "access_token"],
        "messenger": ["page_id", "page_access_token"],
        "instagram": ["instagram_account_id", "access_token"],
    }
    
    missing = [f for f in required_fields.get(channel_lower, []) if not channel_config.get(f)]
    if missing:
        return {
            "status": "error",
            "channel": channel_lower,
            "sales_profile_slug": sales_profile_slug,
            "details": f"Campos faltantes: {', '.join(missing)}",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    
    # Test actual API connection
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            if channel_lower == "whatsapp":
                # Test WhatsApp API
                phone_id = channel_config.get("phone_number_id")
                token = channel_config.get("access_token")
                # Simple validation: get phone number info
                resp = await client.get(
                    f"https://graph.instagram.com/v18.0/{phone_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if resp.status_code == 200:
                    return {
                        "status": "success",
                        "channel": channel_lower,
                        "sales_profile_slug": sales_profile_slug,
                        "details": "Conexión exitosa a Meta Graph API para WhatsApp",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                elif resp.status_code == 401:
                    return {
                        "status": "error",
                        "channel": channel_lower,
                        "sales_profile_slug": sales_profile_slug,
                        "details": "Token de acceso inválido (401 Unauthorized)",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                else:
                    return {
                        "status": "error",
                        "channel": channel_lower,
                        "sales_profile_slug": sales_profile_slug,
                        "details": f"Error de API: {resp.status_code} {resp.text[:100]}",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
            
            elif channel_lower == "messenger":
                # Test Messenger API
                page_id = channel_config.get("page_id")
                token = channel_config.get("page_access_token")
                resp = await client.get(
                    f"https://graph.facebook.com/v18.0/{page_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if resp.status_code == 200:
                    return {
                        "status": "success",
                        "channel": channel_lower,
                        "sales_profile_slug": sales_profile_slug,
                        "details": "Conexión exitosa a Meta Graph API para Messenger",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                elif resp.status_code == 401:
                    return {
                        "status": "error",
                        "channel": channel_lower,
                        "sales_profile_slug": sales_profile_slug,
                        "details": "Token de acceso inválido (401 Unauthorized)",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                else:
                    return {
                        "status": "error",
                        "channel": channel_lower,
                        "sales_profile_slug": sales_profile_slug,
                        "details": f"Error de API: {resp.status_code} {resp.text[:100]}",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
            
            elif channel_lower == "instagram":
                # Test Instagram API
                account_id = channel_config.get("instagram_account_id")
                token = channel_config.get("access_token")
                resp = await client.get(
                    f"https://graph.instagram.com/v18.0/{account_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if resp.status_code == 200:
                    return {
                        "status": "success",
                        "channel": channel_lower,
                        "sales_profile_slug": sales_profile_slug,
                        "details": "Conexión exitosa a Meta Graph API para Instagram",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                elif resp.status_code == 401:
                    return {
                        "status": "error",
                        "channel": channel_lower,
                        "sales_profile_slug": sales_profile_slug,
                        "details": "Token de acceso inválido (401 Unauthorized)",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                else:
                    return {
                        "status": "error",
                        "channel": channel_lower,
                        "sales_profile_slug": sales_profile_slug,
                        "details": f"Error de API: {resp.status_code} {resp.text[:100]}",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
    
    except httpx.TimeoutException:
        return {
            "status": "error",
            "channel": channel_lower,
            "sales_profile_slug": sales_profile_slug,
            "details": "Timeout conectando a Meta API (5 segundos)",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "channel": channel_lower,
            "sales_profile_slug": sales_profile_slug,
            "details": f"Error inesperado: {str(e)[:100]}",
            "timestamp": datetime.now(UTC).isoformat(),
        }
