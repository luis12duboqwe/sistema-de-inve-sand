from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

class ProfileBase(BaseModel):
    name: str
    slug: str
    active: bool = True

class ProfileCreate(ProfileBase):
    pass

class ProfileResponse(ProfileBase):
    id: int

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    active: Optional[bool] = None

class ProductBase(BaseModel):
    profile_id: int
    sku: str
    nombre: str
    categoria: str = Field(..., pattern="^(celular|accesorio)$")
    marca: str
    modelo: str
    capacidad: Optional[str] = None
    condicion: str
    precio: Decimal
    moneda: str = "HNL"
    garantia_meses: int = 0
    activo: bool = True

class ProductCreate(ProductBase):
    cantidad_inicial: int = Field(0, alias="stock_inicial")

    model_config = {
        "populate_by_name": True
    }


class ProductUpdate(BaseModel):
    nombre: Optional[str] = None
    categoria: Optional[str] = Field(None, pattern="^(celular|accesorio)$")
    marca: Optional[str] = None
    modelo: Optional[str] = None
    capacidad: Optional[str] = None
    condicion: Optional[str] = None
    precio: Optional[Decimal] = None
    moneda: Optional[str] = None
    garantia_meses: Optional[int] = None
    activo: Optional[bool] = None

    class Config:
        from_attributes = True


class StockUpdate(BaseModel):
    cantidad_disponible: int = Field(..., ge=0)

class ProductResponse(BaseModel):
    id: int
    nombre: str
    categoria: str
    marca: str
    modelo: str
    capacidad: Optional[str]
    condicion: str
    precio: Decimal
    moneda: str
    garantia_meses: int
    stock_disponible: int

    class Config:
        from_attributes = True

class OrderItemCreate(BaseModel):
    product_id: int
    cantidad: int = Field(..., gt=0)
    es_regalo_promocion: bool = False

class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    cantidad: int
    precio_unitario: Decimal
    es_regalo_promocion: bool
    product: ProductResponse

    class Config:
        from_attributes = True


class OrderItemUpdate(BaseModel):
    product_id: int
    cantidad: int = Field(..., gt=0)
    es_regalo_promocion: bool = False

class OrderCreate(BaseModel):
    profile_slug: str
    canal: str = Field(..., pattern="^(whatsapp|facebook|instagram)$")
    customer_name: str
    customer_phone: str
    metodo_pago: str = Field(..., pattern="^(efectivo|transferencia|tarjeta|financiamiento)$")
    items: List[OrderItemCreate]
    
    @field_validator('customer_phone')
    @classmethod
    def validate_phone_is_string(cls, v):
        if v is None:
            raise ValueError('customer_phone cannot be None')
        return str(v).strip()

class OrderResponse(BaseModel):
    id: int
    profile_id: int
    customer_name: str
    customer_phone: str
    canal: str
    metodo_pago: str
    total: Decimal
    estado: str
    created_at: datetime
    items: List[OrderItemResponse]

    class Config:
        from_attributes = True

class OrderListResponse(BaseModel):
    id: int
    profile_id: int
    customer_name: str
    customer_phone: str
    canal: str
    metodo_pago: str
    total: Decimal
    estado: str
    created_at: datetime

    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    estado: str = Field(..., pattern="^(pendiente|por_entregar|completada|cancelada)$")


class OrderUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    canal: Optional[str] = Field(None, pattern="^(whatsapp|facebook|instagram)$")
    metodo_pago: Optional[str] = Field(None, pattern="^(efectivo|transferencia|tarjeta|financiamiento)$")
    items: Optional[List[OrderItemUpdate]] = None
