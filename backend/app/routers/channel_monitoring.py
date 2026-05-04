"""
Endpoint de monitoreo y auditoría para canales de integración.

GET /api/channels/monitoring/metrics
GET /api/channels/monitoring/audit/{profile_slug}
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, UTC, timedelta
from app.database import get_db
from app.models import SalesProfile, InteractionLog, ProcessedMessage
from app.channel_audit import channel_metrics
from typing import Any, Dict, List

router = APIRouter(prefix="/api/channels/monitoring", tags=["Channel Monitoring"])


@router.get("/metrics")
def get_channel_metrics() -> Dict[str, Any]:
    """
    Retorna métricas activas de canales.
    
    Incluye:
    - Mensajes recibidos por canal/perfil
    - Mensajes enviados por canal/perfil
    - Mensajes duplicados deduplicados
    - Errores de API
    """
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "metrics": channel_metrics.get_summary(),
    }


@router.get("/audit/{sales_profile_slug}")
def get_profile_audit_log(
    sales_profile_slug: str,
    db: Session = Depends(get_db),
    hours: int = Query(24, ge=1, le=168),
) -> Dict[str, Any]:
    """
    Retorna log de auditoría para un perfil.
    
    Incluye:
    - Últimas interacciones (últimas N horas)
    - Mensajes procesados / duplicados
    - Cambios de configuración (si se guardó)
    
    Args:
        sales_profile_slug: Slug del perfil
        hours: Rango de horas a buscar (default 24, max 7 días)
    """
    # Validar perfil existe
    profile = db.query(SalesProfile).filter(
        SalesProfile.slug == sales_profile_slug,
        SalesProfile.active == True
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail=f"Perfil {sales_profile_slug} no encontrado")
    
    cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
    
    # Últimas interacciones
    interactions = db.query(InteractionLog).filter(
        InteractionLog.sales_profile_id == profile.id,
        InteractionLog.created_at >= cutoff_time
    ).order_by(InteractionLog.created_at.desc()).limit(100).all()
    
    # Mensajes procesados (del último día por defecto)
    processed_messages = db.query(ProcessedMessage).filter(
        ProcessedMessage.sales_profile_id == profile.id,
        ProcessedMessage.processed_at >= cutoff_time
    ).order_by(ProcessedMessage.processed_at.desc()).limit(100).all()
    
    # Agrupar por canal
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
                "content": i.content[:100],  # Preview
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
    """
    Retorna estado general del sistema de canales.
    
    Incluye:
    - Profiles activos con canales configurados
    - Últimas interacciones globales
    - Métricas agregadas
    """
    # Profiles con canales
    profiles = db.query(SalesProfile).filter(
        SalesProfile.active == True,
        SalesProfile.canales != None
    ).all()
    
    profiles_with_channels: List[Dict[str, Any]] = []
    for p in profiles:
        canales_raw = str(p.canales or "").strip()
        if canales_raw:
            canales = [canal.strip() for canal in canales_raw.split(',') if canal.strip()]
            profiles_with_channels.append({
                "slug": str(p.slug),
                "name": str(p.name),
                "canales": canales,
                "tipo": str(p.tipo),
            })
    
    # Últimas 24h
    cutoff_time = datetime.now(UTC) - timedelta(hours=24)
    recent_interactions = db.query(InteractionLog).filter(
        InteractionLog.created_at >= cutoff_time
    ).count()
    
    recent_messages = db.query(ProcessedMessage).filter(
        ProcessedMessage.processed_at >= cutoff_time
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
