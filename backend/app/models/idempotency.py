"""Persist successful business-request idempotency claims in the same transaction."""
from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.sql import func

from app.database import Base


class BusinessRequestKey(Base):
    __tablename__ = "business_request_keys"

    key_digest = Column(String(64), primary_key=True)
    payload_digest = Column(String(64), nullable=False)
    response_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
