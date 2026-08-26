"""
Endpoint de monitoreo y auditoría para canales de integración.

GET /api/channels/monitoring/metrics
GET /api/channels/monitoring/audit/{profile_slug}
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import check_permission
from app.channel_audit import channel_metrics
from app.database import get_db
from app.models import InteractionLog, ProcessedMessage, SalesProfile
from app.sales_profile_lookup import find_sales_profile_by_slug
from app.utils.sales_profile_config import parse_channels

router = APIRouter(
    prefix="/api/channels/monitoring",
    tags=["Channel Monitoring"],
    dependencies=[Depends(check_permission("reports:view"))],
)


@router.get("/metrics")
def get_channel_metrics() -> Dict[str, Any]:
    """Retorna métricas activas de canales."""
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "metrics": channel_metrics.get_summary(),
    }


@router.get("/audit/{sales_profile_slug}")
def get_profile_audit_log(
    sales_profile_slug: str,
    db: Session = Depends(get_db),
    hours: int = Query(24, ge=1, le=168),
    _ai_manager: Any = Depends(check_permission("ai:manage")),
) -> Dict[str, Any]:
    """Retorna log de auditoría para un perfil."""
    profile = find_sales_profile_by_slug(db, sales_profile_slug, active=True)

    if not profile:
        raise HTTPException(status_code=404, detail=f"Perfil {sales_profile_slug} no encontrado")

    cutoff_time = datetime.now(UTC) - timedelta(hours=hours)

    interactions = db.query(InteractionLog).filter(
        InteractionLog.sales_profile_id == profile.id,
        InteractionLog.created_at >= cutoff_time,
    ).order_by(InteractionLog.created_at.desc()).limit(100).all()

    processed_messages = db.query(ProcessedMessage).filter(
        ProcessedMessage.sales_profile_id == profile.id,
        ProcessedMessage.processed_at >= cutoff_time,
    ).order_by(ProcessedMessage.processed_at.desc()).limit(100).all()

    by_channel: Dict[str, List[Dict[str, str]]] = {}
    for msg in processed_messages:
        channel = str(msg.channel)
        if channel not in by_channel:
            by_channel[channel] = []
        by_channel[channel].append({
            "message_id": str(msg.message_id),
            "customer_phone": str(msg.customer_phone),
            "processed_at": msg.processed_at.isoformat(),
            "expires_at": msg.expires_at.isoformat(),
        })

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "sales_profile_slug": sales_profile_slug,
        "hours_range": hours,
        "interaction_count": len(interactions),
        "recent_interactions": [
            {
                "id": i.id,
                "role": i.role,
                "content": i.content[:100],
                "tokens_used": i.tokens_used,
                "created_at": i.created_at.isoformat(),
            }
            for i in interactions
        ],
        "processed_messages_count": len(processed_messages),
        "processed_messages_by_channel": {
            channel: {"count": len(msgs), "recent": msgs[:10]}
            for channel, msgs in by_channel.items()
        },
    }


@router.get("/status")
def get_channel_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retorna estado general del sistema de canales."""
    profiles = db.query(SalesProfile).filter(
        SalesProfile.active == True,
        SalesProfile.canales != None,
    ).all()

    profiles_with_channels: List[Dict[str, Any]] = []
    for profile in profiles:
        channels = parse_channels(profile.canales)
        if not channels:
            continue
        profiles_with_channels.append({
            "slug": str(profile.slug),
            "name": str(profile.name),
            "canales": channels,
            "tipo": str(profile.tipo),
        })

    cutoff_time = datetime.now(UTC) - timedelta(hours=24)
    recent_interactions = db.query(InteractionLog).filter(
        InteractionLog.created_at >= cutoff_time,
    ).count()

    recent_messages = db.query(ProcessedMessage).filter(
        ProcessedMessage.processed_at >= cutoff_time,
    ).count()

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "system_status": "operational",
        "profiles_with_channels": len(profiles_with_channels),
        "profiles": profiles_with_channels,
        "last_24h": {
            "interactions": recent_interactions,
            "messages_processed": recent_messages,
        },
        "metrics": channel_metrics.get_summary(),
    }
