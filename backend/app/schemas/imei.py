"""Schemas relacionados con la serialización de productos e IMEIs."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProductIMEIResponse(BaseModel):
    """Representa un registro de IMEI asociado a un producto."""

    id: int
    product_id: int
    location_id: Optional[int] = None
    imei: str
    vendido: bool
    order_id: Optional[int] = None
    transfer_id: Optional[int] = None
    created_at: datetime
    product_name: Optional[str] = None
    location_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


__all__ = ["ProductIMEIResponse"]
