from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Generic, TypeVar
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
import math


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


class EstadoTransferenciaEnum(str, Enum):
    """Estados de una transferencia de stock"""
    PENDIENTE = "pendiente"
    CONFIRMADA = "confirmada"
    RECHAZADA = "rechazada"
    CANCELADA = "cancelada"


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


# Supplier Schemas
class SupplierBase(BaseModel):
    nombre: str
    contacto: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    notas: Optional[str] = None
    activo: bool = True


class SupplierCreate(SupplierBase):
    profile_id: int


class SupplierUpdate(BaseModel):
    nombre: Optional[str] = None
    contacto: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    notas: Optional[str] = None
    activo: Optional[bool] = None


class SupplierResponse(SupplierBase):
    id: int
    profile_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    profile_id: int
    supplier_id: Optional[int] = None
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
    garantia_condiciones: Optional[str] = None  # Condiciones de garantía del proveedor
    activo: bool = True
    imei: Optional[str] = None  # DEPRECATED: Usar imeis para nuevos productos
    imeis: Optional[List[str]] = None  # Array de IMEIs para múltiples unidades

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
    garantia_condiciones: Optional[str] = None
    activo: Optional[bool] = None
    supplier_id: Optional[int] = None
    imei: Optional[str] = None
    imeis: Optional[List[str]] = None

    class Config:
        from_attributes = True


class StockUpdate(BaseModel):
    cantidad_disponible: int = Field(..., ge=0)

class ProductResponse(BaseModel):
    id: int
    profile_id: int
    supplier_id: Optional[int]
    sku: str
    nombre: str
    categoria: str
    marca: str
    modelo: str
    capacidad: Optional[str]
    condicion: str
    precio: Decimal
    moneda: str
    garantia_meses: int
    activo: bool
    imei: Optional[str]  # Mantener por compatibilidad
    imeis: Optional[List[str]] = None  # Array de IMEIs disponibles
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
    notes: Optional[str] = None  # Notas adicionales de la orden
    delivery_date: Optional[datetime] = None  # Fecha de entrega programada
    
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
    notes: Optional[str] = None
    delivery_date: Optional[datetime] = None
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
    notes: Optional[str] = None
    delivery_date: Optional[datetime] = None
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
    notes: Optional[str] = None
    delivery_date: Optional[datetime] = None


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


# Stock History Schemas
class StockHistoryBase(BaseModel):
    """Base schema para historial de stock"""
    product_id: int
    tipo_cambio: str  # 'venta', 'transferencia_salida', 'transferencia_entrada', 'ajuste', 'devolucion'
    cantidad: int
    stock_anterior: int
    stock_nuevo: int
    referencia_id: Optional[int] = None
    referencia_tipo: Optional[str] = None
    notas: Optional[str] = None
    usuario: Optional[str] = None


class StockHistoryCreate(StockHistoryBase):
    """Schema para crear registro de historial de stock"""
    pass


class StockHistoryResponse(StockHistoryBase):
    """Schema de respuesta para historial de stock"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Pagination schema
T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema"""
    items: List[T]
    total: int
    page: int
    per_page: int
    pages: int


# Customer schemas
class CustomerStats(BaseModel):
    """Customer statistics schema"""
    customer_phone: str
    customer_name: str
    total_orders: int
    total_spent: Decimal
    average_order: Decimal
    first_order_date: datetime
    last_order_date: datetime


class CustomerHistory(CustomerStats):
    """Customer history with order list"""
    orders: List[OrderListResponse]


# Advanced search schemas
class OrderSearchParams(BaseModel):
    """Advanced order search parameters"""
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    amount_min: Optional[Decimal] = None
    amount_max: Optional[Decimal] = None
    customer_query: Optional[str] = None  # Search in name or phone
    product_id: Optional[int] = None
    estado: Optional[EstadoOrdenEnum] = None


# Dashboard/Analytics schemas
class DashboardStats(BaseModel):
    """Dashboard KPIs"""
    active_products: int
    total_products: int
    low_stock_count: int  # Products with stock < 10
    out_of_stock_count: int  # Products with stock = 0
    total_inventory_value: Decimal
    pending_orders: int
    total_orders_today: int
    total_revenue_today: Decimal
    total_revenue_month: Decimal
    total_revenue_last_month: Decimal


class TopProduct(BaseModel):
    """Top selling product"""
    product_id: int
    product_name: str
    units_sold: int
    total_revenue: Decimal


class SalesReport(BaseModel):
    """Sales analytics report"""
    period_start: date
    period_end: date
    total_orders: int
    total_revenue: Decimal
    average_order_value: Decimal
    top_products: List[TopProduct]


class InventoryAlert(BaseModel):
    """Inventory stock alert"""
    product_id: int
    product_name: str
    sku: str
    current_stock: int
    category: str
    alert_level: str  # "critical", "low", "out_of_stock"


# Authentication schemas
class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Data contained in JWT token"""
    username: Optional[str] = None


class UserBase(BaseModel):
    """Base user schema"""
    username: str
    email: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str):
        if len(value) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return value
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str):
        if len(value) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if not value.isalnum():
            raise ValueError("Username must contain only alphanumeric characters")
        return value


class UserUpdate(BaseModel):
    """Schema for updating user information"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user responses"""
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserInDB(UserResponse):
    """User schema as stored in database"""
    hashed_password: str


# Stock Transfer Schemas
class StockTransferCreate(BaseModel):
    """Schema para crear una transferencia de stock"""
    product_id: int
    from_profile_slug: str
    to_profile_slug: str
    cantidad: int = Field(..., gt=0, description="Cantidad a transferir")
    notas: Optional[str] = None
    created_by: Optional[str] = None


class StockTransferResponse(BaseModel):
    """Schema para la respuesta de una transferencia de stock"""
    id: int
    product_id: int
    from_profile_id: int
    to_profile_id: int
    cantidad: int
    notas: Optional[str]
    estado: str
    confirmed_at: Optional[datetime] = None
    confirmed_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    created_by: Optional[str]
    
    # Información adicional del producto
    product_nombre: Optional[str] = None
    product_sku: Optional[str] = None
    from_profile_name: Optional[str] = None
    to_profile_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class StockTransferConfirm(BaseModel):
    """Schema para confirmar una transferencia"""
    confirmed_by: Optional[str] = None


class StockTransferReject(BaseModel):
    """Schema para rechazar una transferencia"""
    rejection_reason: str = Field(..., min_length=1, description="Razón del rechazo")
    rejected_by: Optional[str] = None
