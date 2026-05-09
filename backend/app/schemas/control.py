from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserLocationAccessUpsert(BaseModel):
    location_id: int
    can_view: bool = True
    can_edit: bool = False
    can_close_cash: bool = False
    can_count_stock: bool = False
    can_receive_purchase: bool = False


class UserLocationAccessResponse(UserLocationAccessUpsert):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    location_id: Optional[int] = None
    before_data: Optional[Dict[str, Any]] = None
    after_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class PurchaseReceiptItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., ge=1)
    unit_cost: Decimal = Field(Decimal("0"), ge=0)
    imeis: Optional[List[str]] = None
    notes: Optional[str] = None

    @field_validator("imeis")
    @classmethod
    def normalize_imeis(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return value
        cleaned = [imei.strip() for imei in value if imei and imei.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("La lista de IMEIs contiene duplicados")
        return cleaned


class PurchaseReceiptCreate(BaseModel):
    supplier_id: Optional[int] = None
    location_id: int
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    items: List[PurchaseReceiptItemCreate] = Field(..., min_length=1)


class PurchaseReceiptItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_cost: Decimal
    imeis: Optional[List[str]] = None
    notes: Optional[str] = None


class PurchaseReceiptResponse(BaseModel):
    id: int
    supplier_id: Optional[int] = None
    location_id: int
    invoice_number: Optional[str] = None
    status: str
    total_cost: Decimal
    notes: Optional[str] = None
    received_by: Optional[str] = None
    received_at: datetime
    created_at: datetime
    items: List[PurchaseReceiptItemResponse] = []


class InventoryCountItemCreate(BaseModel):
    product_id: int
    counted_quantity: int = Field(..., ge=0)
    imeis: List[str] = []
    notes: Optional[str] = None


class InventoryCountCreate(BaseModel):
    location_id: int
    notes: Optional[str] = None
    items: List[InventoryCountItemCreate] = Field(..., min_length=1)


class InventoryCountItemResponse(BaseModel):
    id: int
    product_id: int
    expected_quantity: int
    counted_quantity: int
    difference: int
    imeis: List[str] = []
    notes: Optional[str] = None


class InventoryCountResponse(BaseModel):
    id: int
    location_id: int
    status: str
    notes: Optional[str] = None
    counted_by: Optional[str] = None
    approved_by: Optional[str] = None
    counted_at: datetime
    approved_at: Optional[datetime] = None
    created_at: datetime
    items: List[InventoryCountItemResponse] = []


class InventoryCountApproveRequest(BaseModel):
    notes: Optional[str] = None


class LocationDailyCloseCreate(BaseModel):
    location_id: int
    close_date: datetime
    cash_counted: Decimal = Field(..., ge=0)
    transfer_total: Decimal = Field(Decimal("0"), ge=0)
    card_total: Decimal = Field(Decimal("0"), ge=0)
    financing_total: Decimal = Field(Decimal("0"), ge=0)
    notes: Optional[str] = None


class LocationDailyCloseResponse(BaseModel):
    id: int
    location_id: int
    close_date: datetime
    cash_expected: Decimal
    transfer_expected: Decimal = Decimal("0")
    card_expected: Decimal = Decimal("0")
    financing_expected: Decimal = Decimal("0")
    cash_counted: Decimal
    transfer_total: Decimal
    card_total: Decimal
    financing_total: Decimal
    difference: Decimal
    status: str
    notes: Optional[str] = None
    closed_by: Optional[str] = None
    approved_by: Optional[str] = None
    closed_at: datetime
    approved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "UserLocationAccessUpsert",
    "UserLocationAccessResponse",
    "AuditLogResponse",
    "PurchaseReceiptCreate",
    "PurchaseReceiptResponse",
    "InventoryCountCreate",
    "InventoryCountResponse",
    "InventoryCountApproveRequest",
    "LocationDailyCloseCreate",
    "LocationDailyCloseResponse",
]