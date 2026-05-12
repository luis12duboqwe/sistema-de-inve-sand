from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Dict, List, Optional


class PhotoRequestCreate(BaseModel):
    """Crear una solicitud de fotos (llamado por bot cuando cliente pide)."""
    customer_id: str = Field(..., description="Teléfono o ID del cliente")
    product_id: Optional[int] = None
    product_name: str
    color_requested: Optional[str] = None
    size_requested: Optional[str] = None
    additional_notes: Optional[str] = None
    customer_name: Optional[str] = None
    origin_channel: Optional[str] = None


class PhotoRequestUpdate(BaseModel):
    """Actualizar estado de solicitud (por agente)."""
    status: Optional[str] = None  # in_progress, completed, failed, declined
    completion_notes: Optional[str] = None
    assigned_to_user_id: Optional[int] = None
    csat_score: Optional[int] = Field(None, ge=1, le=5)
    csat_feedback: Optional[str] = None


class PhotoRequestMediaCreate(BaseModel):
    """Cargar una foto/video para solicitud."""
    media_url: str
    media_type: str = Field("photo", description="photo, video, 360_view")
    metadata: Optional[Dict[str, Any]] = None


class PhotoRequestMediaResponse(BaseModel):
    id: int
    photo_request_id: int
    media_url: str
    media_type: str
    uploaded_by_user_id: Optional[int]
    uploaded_at: datetime
    sent_to_customer_at: Optional[datetime]
    customer_viewed: bool

    class Config:
        from_attributes = True


class PhotoRequestResponse(BaseModel):
    """Respuesta de solicitud de foto."""
    id: int
    customer_id: str
    product_id: Optional[int]
    product_name: str
    color_requested: Optional[str]
    size_requested: Optional[str]
    additional_notes: Optional[str]
    customer_name: Optional[str]
    origin_channel: Optional[str]
    
    status: str
    assigned_to_user_id: Optional[int]
    completion_notes: Optional[str]
    claimed_at: Optional[datetime]
    last_notified_at: Optional[datetime]
    notification_count: int = 0
    priority_score: Optional[float] = None
    sla_breached: Optional[bool] = None
    
    created_at: datetime
    resolved_at: Optional[datetime]
    agent_response_time_minutes: Optional[int] = None
    csat_score: Optional[int] = None
    csat_feedback: Optional[str] = None
    
    photo_urls: Optional[List[str]]  # URLs de fotos ya enviadas

    class Config:
        from_attributes = True


class PhotoRequestDetailResponse(PhotoRequestResponse):
    """Con más detalles para dashboard de agente."""
    media_items: List[PhotoRequestMediaResponse] = []
    assigned_to_user: Optional[Dict[str, Any]] = None  # {id, name, email}


class NotifyAgentPayload(BaseModel):
    """Payload para notificar al agente sobre nueva solicitud."""
    photo_request_id: int
    customer_phone: str
    product_name: str
    color_requested: Optional[str]
    sales_profile_slug: str
    channel: str  # whatsapp, messenger, instagram
    customer_name: Optional[str] = None


class PhotoRequestSummaryResponse(BaseModel):
    pending_total: int
    assigned_to_me: int
    overdue_total: int
    awaiting_upload_total: int


__all__ = [
    "PhotoRequestCreate",
    "PhotoRequestUpdate",
    "PhotoRequestMediaCreate",
    "PhotoRequestMediaResponse",
    "PhotoRequestResponse",
    "PhotoRequestDetailResponse",
    "NotifyAgentPayload",
]
