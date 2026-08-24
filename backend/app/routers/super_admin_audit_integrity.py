"""Canonical filtering for Super Admin audit-log queries."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, User
from app.routers import super_admin as legacy_super_admin
from app.routers.super_admin import get_current_superuser_audited


router = APIRouter(prefix="/api/super-admin", tags=["super_admin"])
_LIKE_ESCAPE = "\\"


def _escape_ilike_literal(value: str) -> str:
    """Escape user text so SQL LIKE metacharacters remain literal text."""
    return (
        value.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2)
        .replace("%", f"{_LIKE_ESCAPE}%")
        .replace("_", f"{_LIKE_ESCAPE}_")
    )


def _parse_audit_datetime(value: str, field_name: str) -> tuple[datetime, str]:
    raw = value.strip()
    if not raw:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} debe usar formato ISO 8601 válido",
        )
    try:
        return datetime.fromisoformat(raw), raw
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} debe usar formato ISO 8601 válido",
        ) from exc


@router.get("/audit-logs")
def list_super_admin_audit_logs_integrity(
    username: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    location_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    super_admin_only: bool = Query(True),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_audited),
):
    query = db.query(AuditLog)

    if super_admin_only:
        prefix = _escape_ilike_literal("super_admin.")
        query = query.filter(
            AuditLog.action.ilike(f"{prefix}%", escape=_LIKE_ESCAPE)
        )

    if username:
        normalized_username = username.strip()
        if normalized_username:
            username_pattern = _escape_ilike_literal(normalized_username)
            query = query.filter(
                AuditLog.username.ilike(
                    f"%{username_pattern}%",
                    escape=_LIKE_ESCAPE,
                )
            )

    if action:
        normalized_action = action.strip()
        if normalized_action:
            action_pattern = _escape_ilike_literal(normalized_action)
            query = query.filter(
                AuditLog.action.ilike(
                    f"%{action_pattern}%",
                    escape=_LIKE_ESCAPE,
                )
            )

    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(AuditLog.entity_id == entity_id)
    if location_id is not None:
        query = query.filter(AuditLog.location_id == location_id)

    if start_date is not None:
        parsed_start, _ = _parse_audit_datetime(start_date, "start_date")
        query = query.filter(AuditLog.created_at >= parsed_start)

    if end_date is not None:
        parsed_end, raw_end = _parse_audit_datetime(end_date, "end_date")
        if len(raw_end) == 10:
            query = query.filter(AuditLog.created_at < parsed_end + timedelta(days=1))
        else:
            query = query.filter(AuditLog.created_at <= parsed_end)

    rows = query.order_by(desc(AuditLog.created_at)).limit(limit).all()
    return {
        "items": [legacy_super_admin._serialize_audit(row) for row in rows],
        "total": len(rows),
    }


__all__ = [
    "_escape_ilike_literal",
    "_parse_audit_datetime",
    "list_super_admin_audit_logs_integrity",
    "router",
]
