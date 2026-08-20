"""Security-correct health and connection tests for Meta channel integrations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
import httpx
from sqlalchemy.orm import Session

from app.auth import check_permission
from app.config_production import prod_settings
from app.database import get_db
from app.models import SalesProfile, User
from app.routers.channel_integrations import _channel_health_snapshot_with_profiles
from app.utils.sales_profile_config import parse_sales_profile_config


router = APIRouter(prefix="/api/channels", tags=["Channel Integrations"])
META_GRAPH_BASE = "https://graph.facebook.com/v23.0"


def _app_secret_configured() -> bool:
    return bool((getattr(prod_settings, "META_APP_SECRET", "") or "").strip())


@router.get("/health")
def channels_health_integrity(db: Session = Depends(get_db)) -> Dict[str, Any]:
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
    return snapshot


def _connection_result(status: str, channel: str, slug: str, details: str) -> Dict[str, Any]:
    return {
        "status": status,
        "channel": channel,
        "sales_profile_slug": slug,
        "details": details,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.post("/test-connection/{sales_profile_slug}/{channel}")
async def test_channel_connection_integrity(
    sales_profile_slug: str,
    channel: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("ai:manage")),  # noqa: ARG001
) -> Dict[str, Any]:
    profile = db.query(SalesProfile).filter(
        SalesProfile.slug == sales_profile_slug,
        SalesProfile.active == True,
    ).first()
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

    if normalized_channel == "whatsapp":
        object_id = str(channel_config["phone_number_id"]).strip()
        token = str(channel_config["access_token"]).strip()
        fields = "id,display_phone_number,verified_name"
    elif normalized_channel == "messenger":
        object_id = str(channel_config["page_id"]).strip()
        token = str(channel_config["page_access_token"]).strip()
        fields = "id,name"
    else:
        object_id = str(channel_config["instagram_account_id"]).strip()
        token = str(channel_config["page_access_token"]).strip()
        fields = "id,username"

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                f"{META_GRAPH_BASE}/{object_id}",
                params={"fields": fields},
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.TimeoutException:
        return _connection_result("error", normalized_channel, sales_profile_slug, "Timeout conectando a Meta Graph API")
    except httpx.HTTPError:
        return _connection_result("error", normalized_channel, sales_profile_slug, "Error de red conectando a Meta Graph API")

    if response.status_code == 200:
        return _connection_result("success", normalized_channel, sales_profile_slug, f"Conexión exitosa a Meta Graph API para {normalized_channel}")
    if response.status_code in {401, 403}:
        return _connection_result("error", normalized_channel, sales_profile_slug, "Token sin autorización o inválido")
    return _connection_result("error", normalized_channel, sales_profile_slug, f"Meta Graph API respondió HTTP {response.status_code}")
