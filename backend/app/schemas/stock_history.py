"""Schemas relacionados al historial de movimientos de stock."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class StockHistoryBase(BaseModel):
    """Datos compartidos por las entradas de historial de stock."""

    product_id: int
    location_id: Optional[int] = None
    tipo_cambio: str  # venta, transferencia_salida, transferencia_entrada, ajuste, devolucion
    cantidad: int
    stock_anterior: int
    stock_nuevo: int
    referencia_id: Optional[int] = None
    referencia_tipo: Optional[str] = None
    notas: Optional[str] = None
    usuario: Optional[str] = None


class StockHistoryCreate(StockHistoryBase):
    """Payload para crear un registro de historial de stock."""

    pass


class StockHistoryResponse(StockHistoryBase):
    """Respuesta serializada para registros del historial."""

    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
