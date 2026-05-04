"""Schemas relacionados con la serialización de productos e IMEIs."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProductIMEIResponse(BaseModel):
    """Representa un registro de IMEI asociado a un producto."""

    id: int
    product_id: int
    location_id: Optional[int] = None
    supplier_id: Optional[int] = None
    imei: str
    vendido: bool
    order_id: Optional[int] = None
    transfer_id: Optional[int] = None
    received_at: datetime
    sold_at: Optional[datetime] = None
    acquisition_type: Optional[str] = None
    received_notes: Optional[str] = None
    received_by: Optional[str] = None
    created_at: datetime
    product_name: Optional[str] = None
    location_name: Optional[str] = None
    supplier_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class IMEIDetailResponse(ProductIMEIResponse):
    product_sku: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    status_label: Optional[str] = None
    warranty_months: Optional[int] = None
    warranty_expires_at: Optional[datetime] = None


__all__ = ["ProductIMEIResponse", "IMEIDetailResponse"]
