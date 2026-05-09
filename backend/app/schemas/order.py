"""Esquemas Pydantic para órdenes, ítems, retomas y transferencias."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    ValidationInfo,
)

from app.utils.validators import InputValidator, ValidationError
from .product import ProductResponse


class CanalEnum(str, Enum):
    """Canales de venta válidos."""

    WHATSAPP = "whatsapp"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TIENDA = "tienda"


class MetodoPagoEnum(str, Enum):
    """Métodos de pago válidos."""

    EFECTIVO = "efectivo"
    TRANSFERENCIA = "transferencia"
    TARJETA = "tarjeta"
    FINANCIAMIENTO = "financiamiento"


class EstadoOrdenEnum(str, Enum):
    """Estados permitidos para una orden."""

    PENDIENTE = "pendiente"
    POR_ENTREGAR = "por_entregar"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"
    VALIDADA = "validada"  # Validada por admin en cierre de día


class EstadoTransferenciaEnum(str, Enum):
    """Estados de una transferencia de stock."""

    PENDIENTE = "pendiente"
    CONFIRMADA = "confirmada"
    RECHAZADA = "rechazada"
    CANCELADA = "cancelada"


class OrderItemCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    cantidad: int = Field(..., gt=0, le=1000)
    precio_unitario: Optional[Decimal] = Field(None, ge=0)
    costo_unitario: Optional[Decimal] = Field(None, ge=0)
    es_regalo_promocion: bool = False
    imeis: Optional[List[str]] = None

    @field_validator("cantidad")
    @classmethod
    def validate_cantidad(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("La cantidad debe ser mayor a 0")
        if value > 1000:
            raise ValueError(
                "La cantidad máxima permitida por item es 1000. Si necesita más, divida en múltiples órdenes."
            )
        return value


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    cantidad: int
    precio_unitario: Decimal
    costo_unitario: Optional[Decimal] = None
    es_regalo_promocion: bool
    product: ProductResponse
    imeis: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)


class OrderItemUpdate(BaseModel):
    product_id: int = Field(..., gt=0)
    cantidad: int = Field(..., gt=0, le=1000)
    precio_unitario: Optional[Decimal] = Field(None, ge=0)
    costo_unitario: Optional[Decimal] = Field(None, ge=0)
    es_regalo_promocion: bool = False
    imeis: Optional[List[str]] = None

    @field_validator("cantidad")
    @classmethod
    def validate_cantidad(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("La cantidad debe ser mayor a 0")
        if value > 1000:
            raise ValueError(
                "La cantidad máxima permitida por item es 1000. Si necesita más, divida en múltiples órdenes."
            )
        return value

    @field_validator("product_id")
    @classmethod
    def validate_product(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("El product_id debe ser mayor a 0")
        return value

    @field_validator("precio_unitario")
    @classmethod
    def validate_precio(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        if value is not None and value < 0:
            raise ValueError("El precio unitario no puede ser negativo")
        return value


class TradeInCreate(BaseModel):
    marca: str = Field(..., min_length=1)
    modelo: str = Field(..., min_length=1)
    color: Optional[str] = None
    capacidad: Optional[str] = None
    imei: Optional[str] = None
    condicion: str = Field(..., description="usado, dañado, para_repuestos")
    precio_venta: Optional[Decimal] = Field(None, gt=0)
    valor_estimado: Decimal = Field(..., gt=0)
    notas: Optional[str] = None

    @field_validator("marca")
    @classmethod
    def validate_marca(cls, value: str) -> str:
        try:
            validated = InputValidator.validate_text_field(
                value,
                "marca",
                min_length=1,
                max_length=InputValidator.MAX_LENGTHS["marca"],
            )
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
        if validated is None:
            raise ValueError("La marca es obligatoria")
        return validated

    @field_validator("modelo")
    @classmethod
    def validate_modelo(cls, value: str) -> str:
        try:
            validated = InputValidator.validate_text_field(
                value,
                "modelo",
                min_length=1,
                max_length=InputValidator.MAX_LENGTHS["modelo"],
            )
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
        if validated is None:
            raise ValueError("El modelo es obligatorio")
        return validated

    @field_validator("color", "capacidad")
    @classmethod
    def validate_color_capacidad(
        cls,
        value: Optional[str],
        info: ValidationInfo,
    ) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        field_name = info.field_name or "campo"
        max_length = InputValidator.MAX_LENGTHS.get(field_name, 100)
        if len(cleaned) > max_length:
            raise ValueError(f"El campo '{field_name}' no puede exceder {max_length} caracteres")
        return cleaned

    @field_validator("imei")
    @classmethod
    def validate_imei(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        try:
            return InputValidator.validate_imei(value)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc

    @field_validator("condicion")
    @classmethod
    def validate_condicion(cls, value: str) -> str:
        allowed = ["usado", "dañado", "para_repuestos", "nuevo"]
        if value not in allowed:
            raise ValueError(f"Condición inválida. Debe ser una de: {', '.join(allowed)}")
        return value

    @field_validator("notas")
    @classmethod
    def validate_notas(cls, value: Optional[str]) -> Optional[str]:
        if value and len(value.strip()) > 500:
            raise ValueError("Las notas de la retoma no pueden exceder 500 caracteres")
        return value.strip() if value else value


class TradeInResponse(BaseModel):
    id: int
    marca: str
    modelo: str
    color: Optional[str] = None
    capacidad: Optional[str] = None
    imei: Optional[str]
    condicion: str
    valor_estimado: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    profile_slug: Optional[str] = None
    sales_profile_slug: Optional[str] = None
    source_location_id: int = Field(..., gt=0)
    canal: CanalEnum
    customer_name: str = Field(...)
    customer_phone: str = Field(...)
    metodo_pago: MetodoPagoEnum
    transfer_bank_name: Optional[str] = Field(None, max_length=120)
    transfer_reference: Optional[str] = Field(None, max_length=120)
    items: List[OrderItemCreate] = Field(..., min_length=1)
    trade_ins: Optional[List[TradeInCreate]] = None
    notes: Optional[str] = Field(None)
    delivery_date: Optional[datetime] = None
    financing_data: Optional[Dict[str, Any]] = None

    @field_validator("customer_name")
    @classmethod
    def validate_customer_name(cls, value: str) -> str:
        try:
            validated = InputValidator.validate_text_field(
                value,
                "customer_name",
                min_length=1,
                max_length=InputValidator.MAX_LENGTHS["customer_name"],
            )
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
        if validated is None:
            raise ValueError("El nombre del cliente es obligatorio")
        return validated

    @field_validator("customer_phone")
    @classmethod
    def validate_customer_phone(cls, value: str) -> str:
        try:
            validated = InputValidator.validate_phone(value)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
        if validated is None:
            raise ValueError("El teléfono del cliente es obligatorio")
        return validated

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        try:
            return InputValidator.validate_text_field(
                value,
                "notas",
                required=False,
                max_length=InputValidator.MAX_LENGTHS["notas"],
            )
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc

    @field_validator("transfer_bank_name")
    @classmethod
    def validate_transfer_bank_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("transfer_reference")
    @classmethod
    def validate_transfer_reference(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if len(cleaned) > 120:
            raise ValueError("La referencia de transferencia no puede exceder 120 caracteres")
        return cleaned

    @field_validator("source_location_id")
    @classmethod
    def validate_location(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("source_location_id es obligatorio y debe ser mayor a 0 en V2.0")
        return value

    @model_validator(mode="after")
    def validate_profile_slug(self):
        if not self.sales_profile_slug and not self.profile_slug:
            raise ValueError("Debe proporcionar sales_profile_slug (V2.0) o profile_slug (legacy)")

        if self.metodo_pago == MetodoPagoEnum.TRANSFERENCIA:
            if not self.transfer_bank_name:
                raise ValueError("Debe indicar el banco cuando el método de pago es transferencia")
            if not self.transfer_reference:
                raise ValueError("Debe indicar el número de referencia cuando el método de pago es transferencia")
        return self


class OrderResponse(BaseModel):
    id: int
    profile_id: Optional[int] = None
    sales_profile_id: Optional[int] = None
    source_location_id: Optional[int] = None
    customer_name: str
    customer_phone: str
    canal: str
    metodo_pago: str
    transfer_bank_name: Optional[str] = None
    transfer_reference: Optional[str] = None
    total: Decimal
    financing_details: Optional[str] = None
    estado: str
    notes: Optional[str] = None
    delivery_date: Optional[datetime] = None
    created_at: datetime
    items: List[OrderItemResponse]
    trade_ins: Optional[List[TradeInResponse]] = None

    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    id: int
    profile_id: Optional[int] = None
    sales_profile_id: Optional[int] = None
    source_location_id: Optional[int] = None
    customer_name: str
    customer_phone: str
    canal: str
    metodo_pago: str
    transfer_bank_name: Optional[str] = None
    transfer_reference: Optional[str] = None
    total: Decimal
    estado: str
    notes: Optional[str] = None
    delivery_date: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdate(BaseModel):
    estado: EstadoOrdenEnum
    validation_code: Optional[str] = Field(None, min_length=1, description="Código de validación para completar ventas")


class OrderUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    canal: Optional[CanalEnum] = None
    metodo_pago: Optional[MetodoPagoEnum] = None
    transfer_bank_name: Optional[str] = Field(None, max_length=120)
    transfer_reference: Optional[str] = Field(None, max_length=120)
    items: Optional[List[OrderItemUpdate]] = Field(None, min_length=1)
    notes: Optional[str] = None
    delivery_date: Optional[datetime] = None
    source_location_id: Optional[int] = None

    @field_validator("items")
    @classmethod
    def validate_items(cls, value: Optional[List[OrderItemUpdate]]) -> Optional[List[OrderItemUpdate]]:
        if value is not None and len(value) == 0:
            raise ValueError("Si proporciona items, la lista debe contener al menos un producto")
        return value

    @field_validator("transfer_bank_name")
    @classmethod
    def validate_update_transfer_bank_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("transfer_reference")
    @classmethod
    def validate_update_transfer_reference(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("source_location_id")
    @classmethod
    def validate_location(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value <= 0:
            raise ValueError("source_location_id debe ser mayor a 0 cuando se envía")
        return value


class StockTransferCreate(BaseModel):
    product_id: int
    from_location_id: int = Field(..., description="ID de ubicación origen")
    to_location_id: int = Field(..., description="ID de ubicación destino")
    cantidad: int = Field(..., gt=0, le=10000)
    imeis: Optional[List[str]] = Field(None, description="Lista de IMEIs específicos a transferir")
    notas: Optional[str] = None
    created_by: Optional[str] = None

    @field_validator("to_location_id")
    @classmethod
    def validate_different_locations(cls, value: int, info: ValidationInfo) -> int:
        info_data = info.data
        data: Dict[str, Any] = dict(info_data.items()) if info_data else {}
        from_location_id: Optional[int] = data.get("from_location_id")
        if from_location_id is not None and value == from_location_id:
            raise ValueError("Las ubicaciones de origen y destino deben ser diferentes")
        return value

    @field_validator("imeis")
    @classmethod
    def validate_imeis_count(
        cls,
        value: Optional[List[str]],
        info: ValidationInfo,
    ) -> Optional[List[str]]:
        if value is None:
            return None
        info_data = info.data
        data: Dict[str, Any] = dict(info_data.items()) if info_data else {}
        cantidad_value: Optional[int] = data.get("cantidad")
        if isinstance(cantidad_value, int) and len(value) != cantidad_value:
            raise ValueError(
                f"La cantidad de IMEIs ({len(value)}) no coincide con la cantidad a transferir ({cantidad_value})"
            )
        return value

    @field_validator("notas")
    @classmethod
    def validate_notas(cls, value: Optional[str]) -> Optional[str]:
        if value and len(value) > 500:
            raise ValueError("Las notas no pueden exceder los 500 caracteres")
        return value


class StockTransferResponse(BaseModel):
    id: int
    product_id: int
    from_location_id: int
    to_location_id: int
    from_profile_id: Optional[int] = None
    to_profile_id: Optional[int] = None
    cantidad: int
    notas: Optional[str]
    estado: str
    received_quantity: Optional[int] = None
    missing_quantity: Optional[int] = None
    confirmed_at: Optional[datetime] = None
    confirmed_by: Optional[str] = None
    incident_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    created_by: Optional[str]
    imeis: Optional[List[str]] = None
    product_nombre: Optional[str] = None
    product_sku: Optional[str] = None
    from_location_name: Optional[str] = None
    to_location_name: Optional[str] = None
    from_profile_name: Optional[str] = None
    to_profile_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StockTransferConfirm(BaseModel):
    confirmed_by: Optional[str] = None
    scanned_imeis: Optional[List[str]] = None
    received_quantity: Optional[int] = Field(None, ge=0, description="Cantidad física recibida. Si se omite, se recibe todo.")
    incident_notes: Optional[str] = Field(None, max_length=500, description="Notas de incidencia si la recepción fue parcial o con observaciones")
    validation_code: Optional[str] = Field(None, min_length=1, description="Código de validación para confirmar transferencias")


class StockTransferReject(BaseModel):
    rejection_reason: str = Field(..., min_length=1)
    rejected_by: Optional[str] = None

    @field_validator("rejection_reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        if len(value) > 500:
            raise ValueError("La razón del rechazo no puede exceder los 500 caracteres")
        return value


class OrderSearchParams(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    amount_min: Optional[Decimal] = None
    amount_max: Optional[Decimal] = None
    customer_query: Optional[str] = None
    product_id: Optional[int] = None
    location_id: Optional[int] = Field(None, gt=0)
    estado: Optional[EstadoOrdenEnum] = None


class CustomerStats(BaseModel):
    customer_phone: str
    customer_name: str
    total_orders: int
    total_spent: Decimal
    average_order: Decimal
    first_order_date: datetime
    last_order_date: datetime
    id: Optional[int] = None
    is_troll: bool = False
    is_blocked: bool = False
    reputation_score: int = 100
    daily_message_count: int = 0


class CustomerHistory(CustomerStats):
    orders: List[OrderListResponse]


__all__ = [
    "CanalEnum",
    "MetodoPagoEnum",
    "EstadoOrdenEnum",
    "EstadoTransferenciaEnum",
    "OrderItemCreate",
    "OrderItemResponse",
    "OrderItemUpdate",
    "TradeInCreate",
    "TradeInResponse",
    "OrderCreate",
    "OrderResponse",
    "OrderListResponse",
    "OrderStatusUpdate",
    "OrderUpdate",
    "StockTransferCreate",
    "StockTransferResponse",
    "StockTransferConfirm",
    "StockTransferReject",
    "OrderSearchParams",
    "CustomerStats",
    "CustomerHistory",
]
