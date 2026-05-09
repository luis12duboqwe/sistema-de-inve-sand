"""Esquemas para el cierre de día y validación de ventas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class DailyCloseValidateRequest(BaseModel):
    """Solicitud de validación de cierre de día."""
    validation_code: str = Field(..., min_length=1, description="Código de validación configurado por el admin")
    order_ids: List[int] = Field(..., min_length=1, description="IDs de órdenes a validar")
    location_id: Optional[int] = Field(None, gt=0, description="Ubicación a cerrar/validar")
    notas: Optional[str] = Field(None, max_length=500)


class DailyCloseConfigRequest(BaseModel):
    """Configurar o cambiar el código de validación."""
    new_code: str = Field(..., min_length=6, max_length=64, description="Nuevo código de validación (6-64 caracteres)")
    confirm_code: str = Field(..., description="Confirmar el nuevo código")
    current_code: Optional[str] = Field(None, description="Código actual (requerido si ya existe uno)")


class DailyCloseOrderSummary(BaseModel):
    """Resumen de una orden pendiente de validación."""
    id: int
    customer_name: str
    customer_phone: str
    canal: str
    metodo_pago: str
    total: float
    estado: str
    source_location_id: Optional[int] = None
    source_location_name: Optional[str] = None
    created_at: datetime
    items_count: int
    items_summary: str  # Ej: "iPhone 14 x1, Cargador x2"


class DailyCloseValidateResponse(BaseModel):
    """Respuesta al validar el cierre de día."""
    validated_count: int
    validated_orders: List[int]
    total_ventas: float
    mensaje: str


class DailyCloseConfigResponse(BaseModel):
    """Estado actual de la configuración del cierre de día."""
    configured: bool
    mensaje: str
