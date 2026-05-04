"""
Audit trail for customer memory changes and analytics events.
"""

import logging
from datetime import datetime, UTC
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


from app.database import Base


class CustomerMemoryAudit(Base):
    """Audit log for customer memory changes."""
    __tablename__ = "customer_memory_audit"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, index=True, nullable=False)
    field_name = Column(String(100), nullable=False)  # e.g., "conversation_summary", "last_referenced_product"
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    changed_by_user_id = Column(Integer, nullable=True)
    changed_by_system = Column(String(50), nullable=True)  # e.g., "ai_intelligence", "manual"
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class AnalyticsEvent(Base):
    """Analytics events for SLA, performance, and business metrics."""
    __tablename__ = "analytics_events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), index=True, nullable=False)  # e.g., "photo_request_created", "sla_breached"
    entity_type = Column(String(50), nullable=False)  # e.g., "photo_request", "order"
    entity_id = Column(Integer, nullable=False)
    value = Column(Integer, nullable=True)  # e.g., response_time_seconds
    metadata = Column(JSON, nullable=True)  # e.g., {"product_name": "iPhone 15", "channel": "whatsapp"}
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)


def log_memory_change(
    db: Session,
    customer_id: int,
    field_name: str,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    changed_by_user_id: Optional[int] = None,
    changed_by_system: Optional[str] = None,
    reason: Optional[str] = None
):
    """Log a change to customer memory."""
    try:
        audit = CustomerMemoryAudit(
            customer_id=customer_id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            changed_by_user_id=changed_by_user_id,
            changed_by_system=changed_by_system,
            reason=reason
        )
        db.add(audit)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log memory change: {e}")
        db.rollback()


def log_analytics_event(
    db: Session,
    event_type: str,
    entity_type: str,
    entity_id: int,
    value: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Log an analytics event."""
    try:
        event = AnalyticsEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            value=value,
            metadata=metadata
        )
        db.add(event)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log analytics event: {e}")
        db.rollback()
