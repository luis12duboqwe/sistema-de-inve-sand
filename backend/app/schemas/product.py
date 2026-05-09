"""Esquemas Pydantic relacionados con productos e inventario."""

from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .location import LocationResponse


class CategoriaEnum(str, Enum):
    """Categorías válidas para productos."""

    CELULAR = "celular"
    ACCESORIO = "accesorio"


class CondicionEnum(str, Enum):
    """Condiciones válidas para productos."""

    NUEVO = "nuevo"
    USADO = "usado"
    REACONDICIONADO = "reacondicionado"


class StockByLocationBase(BaseModel):
    product_id: int
    location_id: int
    cantidad_disponible: int = Field(0, ge=0)
    cantidad_reservada: int = Field(0, ge=0)
    cantidad_defectuosa: int = Field(0, ge=0)


class StockByLocationCreate(StockByLocationBase):
    pass


class StockByLocationUpdate(BaseModel):
    cantidad_disponible: int = Field(..., ge=0)
    cantidad_reservada: Optional[int] = Field(None, ge=0)


class StockByLocationResponse(StockByLocationBase):
    id: int
    stock_libre: int = Field(0, ge=0)
    en_transito_salida: int = Field(0, ge=0)
    en_transito_entrada: int = Field(0, ge=0)
    location: Optional[LocationResponse] = None

    model_config = ConfigDict(from_attributes=True)


class IMEIWithLocation(BaseModel):
    imei: str
    location_id: int


class ProductBase(BaseModel):
    profile_id: Optional[int] = None
    supplier_id: Optional[int] = None
    sku: str = Field(..., min_length=1)
    nombre: str = Field(..., min_length=1)
    categoria: CategoriaEnum
    marca: str = Field(..., min_length=1)
    modelo: str = Field(..., min_length=1)
    color: Optional[str] = None
    capacidad: Optional[str] = None
    condicion: CondicionEnum
    precio: Decimal = Field(..., gt=0, le=Decimal("1000000"))
    costo: Decimal = Field(Decimal("0.00"), ge=0)
    moneda: str = "Lps"
    garantia_meses: int = Field(0, ge=0, le=120)
    garantia_condiciones: Optional[str] = None
    activo: bool = True
    is_serialized: bool = False
    imei: Optional[str] = None
    imeis: Optional[List[str]] = None

    @field_validator("precio")
    @classmethod
    def validate_precio_positivo(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("El precio debe ser mayor a 0")
        if value > Decimal("1000000"):
            raise ValueError("El precio máximo permitido es 1,000,000. Verifique el valor ingresado.")
        return value


class ProductCreate(ProductBase):
    cantidad_inicial: int = Field(0, ge=0, le=100000, alias="stock_inicial")
    initial_location_id: Optional[int] = None
    imeis_con_ubicacion: Optional[List[IMEIWithLocation]] = None

    @field_validator("cantidad_inicial")
    @classmethod
    def validate_stock_inicial(cls, value: int) -> int:
        if value < 0:
            raise ValueError("El stock inicial no puede ser negativo")
        if value > 100000:
            raise ValueError("El stock inicial máximo permitido es 100,000 unidades. Verifique el valor.")
        return value

    model_config = ConfigDict(populate_by_name=True)


class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    nombre: Optional[str] = None
    categoria: Optional[CategoriaEnum] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    color: Optional[str] = None
    capacidad: Optional[str] = None
    condicion: Optional[CondicionEnum] = None
    precio: Optional[Decimal] = None
    costo: Optional[Decimal] = None
    moneda: Optional[str] = None
    garantia_meses: Optional[int] = None
    garantia_condiciones: Optional[str] = None
    is_serialized: Optional[bool] = None
    activo: Optional[bool] = None
    supplier_id: Optional[int] = None
    imei: Optional[str] = None
    imeis: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)


class ProductRestockRequest(BaseModel):
    location_id: int
    cantidad: int = Field(..., gt=0, le=100000)
    supplier_id: Optional[int] = None
    notas: Optional[str] = None
    imeis: Optional[List[str]] = None


class ProductResponse(BaseModel):
    id: int
    profile_id: Optional[int] = None
    supplier_id: Optional[int] = None
    sku: str
    nombre: str
    categoria: str
    marca: str
    modelo: str
    color: Optional[str] = None
    capacidad: Optional[str] = None
    condicion: str
    precio: Decimal
    costo: Decimal
    moneda: str
    garantia_meses: int
    garantia_condiciones: Optional[str] = None
    activo: bool
    is_serialized: bool = False
    imei: Optional[str] = None
    imeis: Optional[List[str]] = None
    stock_disponible: int
    stock_items: Optional[List[StockByLocationResponse]] = None

    model_config = ConfigDict(from_attributes=True)


class StockUpdate(BaseModel):
    cantidad_disponible: int = Field(..., ge=0)


__all__ = [
    "CategoriaEnum",
    "CondicionEnum",
    "StockByLocationBase",
    "StockByLocationCreate",
    "StockByLocationUpdate",
    "StockByLocationResponse",
    "IMEIWithLocation",
    "ProductBase",
    "ProductCreate",
    "ProductRestockRequest",
    "ProductUpdate",
    "ProductResponse",
    "StockUpdate",
]
