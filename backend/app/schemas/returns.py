"""Esquemas para devoluciones e historial de IMEIs."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReturnConditionEnum(str, Enum):
    NUEVO = "nuevo"
    DEFECTUOSO = "defectuoso"
    ABIERTO = "abierto"


class ReturnActionEnum(str, Enum):
    REFUND = "refund"
    WARRANTY_EXCHANGE = "warranty_exchange"
    STORE_CREDIT = "store_credit"


class ReturnItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    condition: ReturnConditionEnum
    action: ReturnActionEnum
    imei: Optional[str] = None

    @field_validator("imei")
    @classmethod
    def validate_imei(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned.isdigit() or not (14 <= len(cleaned) <= 17):
            raise ValueError("IMEI debe ser numérico y de 14-17 dígitos")
        return cleaned


class ReturnCreate(BaseModel):
    order_id: int
    reason: Optional[str] = None
    created_by: Optional[str] = None
    items: List[ReturnItemCreate] = Field(..., min_length=1)

    @field_validator("reason")
    @classmethod
    def validate_reason_length(cls, value: Optional[str]) -> Optional[str]:
        if value and len(value) > 500:
            raise ValueError("La razón no puede exceder 500 caracteres")
        return value


class ReturnItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    condition: str
    action: str
    imei: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ReturnResponse(BaseModel):
    id: int
    order_id: int
    created_at: datetime
    reason: Optional[str]
    status: str
    created_by: Optional[str]
    items: List[ReturnItemResponse]

    model_config = ConfigDict(from_attributes=True)


class IMEIHistoryResponse(BaseModel):
    id: int
    imei: str
    product_id: int
    location_id: Optional[int]
    event_type: str
    reference_id: Optional[int]
    reference_type: Optional[str]
    notes: Optional[str]
    created_at: datetime
    created_by: Optional[str]
    product_name: Optional[str] = None
    location_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "ReturnConditionEnum",
    "ReturnActionEnum",
    "ReturnItemCreate",
    "ReturnCreate",
    "ReturnItemResponse",
    "ReturnResponse",
    "IMEIHistoryResponse",
]
