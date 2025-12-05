from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum


class CategoriaEnum(str, Enum):
    """Categorías válidas para productos"""
    CELULAR = "celular"
    ACCESORIO = "accesorio"


class CondicionEnum(str, Enum):
    """Condiciones válidas para productos"""
    NUEVO = "nuevo"
    USADO = "usado"
    REACONDICIONADO = "reacondicionado"


class CanalEnum(str, Enum):
    """Canales de venta válidos"""
    WHATSAPP = "whatsapp"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"


class MetodoPagoEnum(str, Enum):
    """Métodos de pago válidos"""
    EFECTIVO = "efectivo"
    TRANSFERENCIA = "transferencia"
    TARJETA = "tarjeta"
    FINANCIAMIENTO = "financiamiento"


class EstadoOrdenEnum(str, Enum):
    """Estados válidos de una orden"""
    PENDIENTE = "pendiente"
    POR_ENTREGAR = "por_entregar"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"


class NivelSeriedadEnum(str, Enum):
    """Niveles de seriedad para FAQ"""
    NORMAL = "normal"
    IMPORTANTE = "importante"
    URGENTE = "urgente"


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
    categoria: CategoriaEnum
    marca: str
    modelo: str
    capacidad: Optional[str] = None
    condicion: CondicionEnum
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
    categoria: Optional[CategoriaEnum] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    capacidad: Optional[str] = None
    condicion: Optional[CondicionEnum] = None
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
    canal: CanalEnum
    customer_name: str
    customer_phone: str
    metodo_pago: MetodoPagoEnum
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
    estado: EstadoOrdenEnum


class OrderUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    canal: Optional[CanalEnum] = None
    metodo_pago: Optional[MetodoPagoEnum] = None
    items: Optional[List[OrderItemUpdate]] = None


class FAQEntryBase(BaseModel):
    pregunta_clave: str
    ejemplo_pregunta_cliente: Optional[str] = None
    respuesta: str
    categoria: str
    nivel_seriedad: NivelSeriedadEnum = NivelSeriedadEnum.NORMAL
    activa: bool = True
    created_by: Optional[str] = None


class FAQEntryCreate(FAQEntryBase):

    @field_validator("pregunta_clave", "respuesta")
    @classmethod
    def validate_not_empty(cls, value: str):
        if not value or not value.strip():
            raise ValueError("Este campo no puede estar vacío")
        return value


class FAQEntryUpdate(BaseModel):
    pregunta_clave: Optional[str] = None
    ejemplo_pregunta_cliente: Optional[str] = None
    respuesta: Optional[str] = None
    categoria: Optional[str] = None
    nivel_seriedad: Optional[str] = None
    activa: Optional[bool] = None


class FAQEntryResponse(BaseModel):
    id: int
    pregunta_clave: str
    ejemplo_pregunta_cliente: Optional[str]
    respuesta: str
    categoria: str
    nivel_seriedad: str
    activa: bool
    veces_usada: int
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
