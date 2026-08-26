"""Security-correct health and connection tests for Meta channel integrations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
import httpx
from sqlalchemy.orm import Session

from app.auth import check_permission, get_current_user_optional
from app.config_production import prod_settings
from app.database import get_db
from app.models import User
from app.routers.channel_integrations import _channel_health_snapshot_with_profiles
from app.sales_profile_lookup import find_sales_profile_by_slug
from app.utils.sales_profile_config import parse_sales_profile_config


router = APIRouter(prefix="/api/channels", tags=["Channel Integrations"])
META_GRAPH_BASE = "https://graph.facebook.com/v23.0"


def _app_secret_configured() -> bool:
    return bool((getattr(prod_settings, "META_APP_SECRET", "") or "").strip())


def _can_view_channel_health_details(user: User | None) -> bool:
    """Return whether the caller may inspect channel/profile diagnostics."""
    if user is None:
        return False
    if user.is_superuser:
        return True
    role = getattr(user, "role", None)
    permissions = getattr(role, "permissions", None) or []
    return any(getattr(permission, "slug", None) == "ai:manage" for permission in permissions)


def _redacted_channel_health(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Keep the polling contract without exposing integration configuration."""
    ready = bool(snapshot.get("ready"))
    redacted_channel = {"ready": ready, "missing": []}
    return {
        "status": "ok",
        "ready": ready,
        "global": {
            "has_verify_token": False,
            "has_default_sales_profile": False,
            "signature_validation_enabled": False,
            "message_ttl_seconds": 0,
            "missing": [],
        },
        "channels": {
            "whatsapp": dict(redacted_channel),
            "messenger": dict(redacted_channel),
            "instagram": dict(redacted_channel),
        },
        "profiles": [],
        "diagnostics_restricted": True,
    }


@router.get("/health")
def channels_health_integrity(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    snapshot = _channel_health_snapshot_with_profiles(db)
    signature_enabled = _app_secret_configured()
    global_info = snapshot.setdefault("global", {})
    global_info["signature_validation_enabled"] = signature_enabled
    missing = list(global_info.get("missing") or [])
    if not signature_enabled:
        missing.append("META_APP_SECRET")
    global_info["missing"] = sorted(set(missing))

    # Meta owns the three supported webhook channels. In production no one of them
    # is considered ready unless webhook signatures can be authenticated.
    if prod_settings.is_production() and not signature_enabled:
        snapshot["ready"] = False
        for info in (snapshot.get("channels") or {}).values():
            if isinstance(info, dict):
                info["ready"] = False
                channel_missing = list(info.get("missing") or [])
                channel_missing.append("META_APP_SECRET")
                info["missing"] = sorted(set(channel_missing))

    if not _can_view_channel_health_details(current_user):
        return _redacted_channel_health(snapshot)
    return snapshot


def _connection_result(status: str, channel: str, slug: str, details: str) -> Dict[str, Any]:
    return {
        "status": status,
        "channel": channel,
        "sales_profile_slug": slug,
        "details": details,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def _meta_failure_result(
    response: httpx.Response,
    *,
    channel: str,
    slug: str,
    capability_check: bool = False,
) -> Dict[str, Any]:
    if response.status_code in {401, 403}:
        detail = "Token sin autorización o inválido"
    elif capability_check:
        detail = (
            "Meta no confirmó permisos/capacidad de mensajería "
            f"(HTTP {response.status_code})"
        )
    else:
        detail = f"Meta Graph API respondió HTTP {response.status_code}"
    return _connection_result("error", channel, slug, detail)


async def _test_page_messaging_capability(
    client: httpx.AsyncClient,
    *,
    channel: str,
    slug: str,
    configured_object_id: str,
    token: str,
) -> Dict[str, Any]:
    """Validate Page-token ownership and read-only messaging capability.

    Meta's Conversations API requires the same messaging permissions/tasks used
    by Messenger/Instagram messaging. Querying one conversation page therefore
    gives us a non-destructive capability probe without sending a customer
    message. Instagram's Facebook-Login flow is anchored to the Facebook Page,
    so ``/me`` is also used to verify that the configured IG professional account
    is actually linked to the Page represented by the supplied Page token.
    """
    if channel == "messenger":
        identity_fields = "id,name"
    else:
        identity_fields = "id,name,instagram_business_account"

    identity_response = await client.get(
        f"{META_GRAPH_BASE}/me",
        params={"fields": identity_fields},
        headers={"Authorization": f"Bearer {token}"},
    )
    if identity_response.status_code != 200:
        return _meta_failure_result(
            identity_response,
            channel=channel,
            slug=slug,
        )

    try:
        identity = identity_response.json()
    except ValueError:
        return _connection_result(
            "error",
            channel,
            slug,
            "Meta Graph API devolvió una respuesta de identidad inválida",
        )
    if not isinstance(identity, dict):
        return _connection_result(
            "error",
            channel,
            slug,
            "Meta Graph API devolvió una respuesta de identidad inválida",
        )

    page_id = str(identity.get("id") or "").strip()
    if not page_id:
        return _connection_result(
            "error",
            channel,
            slug,
            "El Page Access Token no resolvió una Page válida",
        )

    if channel == "messenger":
        if page_id != configured_object_id:
            return _connection_result(
                "error",
                channel,
                slug,
                "El Page Access Token pertenece a una Page distinta del page_id configurado",
            )
        conversation_params: Dict[str, str] = {"limit": "1"}
    else:
        linked_instagram = identity.get("instagram_business_account")
        linked_instagram_id = (
            str(linked_instagram.get("id") or "").strip()
            if isinstance(linked_instagram, dict)
            else ""
        )
        if not linked_instagram_id:
            return _connection_result(
                "error",
                channel,
                slug,
                "La Page del token no tiene una cuenta profesional de Instagram vinculada",
            )
        if linked_instagram_id != configured_object_id:
            return _connection_result(
                "error",
                channel,
                slug,
                "La cuenta de Instagram vinculada no coincide con instagram_account_id",
            )
        conversation_params = {"platform": "instagram", "limit": "1"}

    capability_response = await client.get(
        f"{META_GRAPH_BASE}/{page_id}/conversations",
        params=conversation_params,
        headers={"Authorization": f"Bearer {token}"},
    )
    if capability_response.status_code != 200:
        return _meta_failure_result(
            capability_response,
            channel=channel,
            slug=slug,
            capability_check=True,
        )

    return _connection_result(
        "success",
        channel,
        slug,
        f"Conexión y capacidad de mensajería verificadas para {channel}",
    )


@router.post("/test-connection/{sales_profile_slug}/{channel}")
async def test_channel_connection_integrity(
    sales_profile_slug: str,
    channel: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("ai:manage")),  # noqa: ARG001
) -> Dict[str, Any]:
    profile = find_sales_profile_by_slug(db, sales_profile_slug, active=True)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Perfil {sales_profile_slug} no encontrado")

    normalized_channel = channel.lower()
    if normalized_channel == "facebook":
        normalized_channel = "messenger"
    if normalized_channel not in {"whatsapp", "messenger", "instagram"}:
        raise HTTPException(status_code=400, detail=f"Canal inválido: {channel}")

    config = parse_sales_profile_config(profile.configuracion, decrypt_secrets=True)
    integrations = config.get("channel_integrations", {}) if isinstance(config, dict) else {}
    channel_config = integrations.get(normalized_channel, {}) if isinstance(integrations, dict) else {}
    if not isinstance(channel_config, dict) or not channel_config:
        return _connection_result("error", normalized_channel, sales_profile_slug, f"Canal {normalized_channel} no configurado en el perfil")

    required_fields = {
        "whatsapp": ["phone_number_id", "access_token"],
        "messenger": ["page_id", "page_access_token"],
        "instagram": ["instagram_account_id", "page_access_token"],
    }
    missing = [field for field in required_fields[normalized_channel] if not str(channel_config.get(field) or "").strip()]
    if missing:
        return _connection_result("error", normalized_channel, sales_profile_slug, f"Campos faltantes: {', '.join(missing)}")

    if prod_settings.is_production() and not _app_secret_configured():
        return _connection_result("error", normalized_channel, sales_profile_slug, "Falta META_APP_SECRET para validar firmas de webhook en producción")

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            if normalized_channel == "whatsapp":
                object_id = str(channel_config["phone_number_id"]).strip()
                token = str(channel_config["access_token"]).strip()
                response = await client.get(
                    f"{META_GRAPH_BASE}/{object_id}",
                    params={"fields": "id,display_phone_number,verified_name"},
                    headers={"Authorization": f"Bearer {token}"},
                )
                if response.status_code == 200:
                    return _connection_result(
                        "success",
                        normalized_channel,
                        sales_profile_slug,
                        "Identidad de WhatsApp verificada en Meta Graph API",
                    )
                return _meta_failure_result(
                    response,
                    channel=normalized_channel,
                    slug=sales_profile_slug,
                )

            if normalized_channel == "messenger":
                object_id = str(channel_config["page_id"]).strip()
            else:
                object_id = str(channel_config["instagram_account_id"]).strip()
            token = str(channel_config["page_access_token"]).strip()
            return await _test_page_messaging_capability(
                client,
                channel=normalized_channel,
                slug=sales_profile_slug,
                configured_object_id=object_id,
                token=token,
            )
    except httpx.TimeoutException:
        return _connection_result("error", normalized_channel, sales_profile_slug, "Timeout conectando a Meta Graph API")
    except httpx.HTTPError:
        return _connection_result("error", normalized_channel, sales_profile_slug, "Error de red conectando a Meta Graph API")
