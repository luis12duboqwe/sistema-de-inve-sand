from pydantic import BaseModel, Field, field_validator, model_validator
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


class TipoUbicacionEnum(str, Enum):
    """Tipos de ubicación física"""
    TIENDA = "tienda"
    BODEGA = "bodega"
    OFICINA = "oficina"


class TipoSalesProfileEnum(str, Enum):
    """Tipos de perfil de venta"""
    BOT_IA = "bot_ia"
    VENDEDOR_HUMANO = "vendedor_humano"
    SISTEMA_AUTOMATICO = "sistema_automatico"


class ReturnConditionEnum(str, Enum):
    """Condición del producto devuelto"""
    NUEVO = "nuevo"
    DEFECTUOSO = "defectuoso"
    ABIERTO = "abierto"


class ReturnActionEnum(str, Enum):
    """Acción a tomar con la devolución"""
    REFUND = "refund" # Reembolso
    WARRANTY_EXCHANGE = "warranty_exchange" # Cambio por garantía
    STORE_CREDIT = "store_credit" # Crédito en tienda


# ============= LOCATION SCHEMAS =============
class LocationBase(BaseModel):
    nombre: str = Field(..., min_length=1, description="Nombre no puede estar vacío")
    tipo: TipoUbicacionEnum
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    activo: bool = True


class LocationCreate(LocationBase):
    pass

# ============= RBAC SCHEMAS =============
class PermissionBase(BaseModel):
    slug: str
    description: str
    module: str

class PermissionResponse(PermissionBase):
    id: int
    class Config:
        from_attributes = True

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    permissions: List[str] # List of permission slugs

class RoleResponse(RoleBase):
    id: int
    is_system_role: bool
    permissions: List[PermissionResponse]
    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str
    role_id: Optional[int] = None

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
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role_id: Optional[int] = None

class UserResponse(UserBase):
    id: int
    is_superuser: bool
    role: Optional[RoleResponse] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True



class LocationUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, description="Nombre no puede estar vacío si se proporciona")
    tipo: Optional[TipoUbicacionEnum] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    activo: Optional[bool] = None


class LocationResponse(LocationBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============= SALES PROFILE SCHEMAS =============
class SalesProfileBase(BaseModel):
    name: str = Field(..., min_length=1, description="Nombre no puede estar vacío")
    slug: str = Field(..., min_length=1, description="Slug no puede estar vacío")
    tipo: TipoSalesProfileEnum
    canales: Optional[List[str]] = None  # ["whatsapp", "facebook", "instagram"]
    active: bool = True
    configuracion: Optional[dict] = None


class SalesProfileCreate(SalesProfileBase):
    pass


class SalesProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="Nombre no puede estar vacío si se proporciona")
    slug: Optional[str] = Field(None, min_length=1, description="Slug no puede estar vacío si se proporciona")
    tipo: Optional[TipoSalesProfileEnum] = None
    canales: Optional[List[str]] = None
    active: Optional[bool] = None
    configuracion: Optional[dict] = None


class SalesProfileResponse(SalesProfileBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============= STOCK BY LOCATION SCHEMAS =============
class StockByLocationBase(BaseModel):
    product_id: int
    location_id: int
    cantidad_disponible: int = Field(0, ge=0)
    cantidad_reservada: int = Field(0, ge=0)  # V2.0: Stock reservado en transferencias pendientes
    cantidad_defectuosa: int = Field(0, ge=0)  # V2.0: Stock defectuoso/merma


class StockByLocationCreate(StockByLocationBase):
    pass


class StockByLocationUpdate(BaseModel):
    cantidad_disponible: int = Field(..., ge=0)
    cantidad_reservada: Optional[int] = Field(None, ge=0)  # Opcional para actualizaciones


class StockByLocationResponse(StockByLocationBase):
    id: int
    location: Optional[LocationResponse] = None

    class Config:
        from_attributes = True


class ProfileBase(BaseModel):
    name: str = Field(..., min_length=1, description="Nombre no puede estar vacío")
    slug: str = Field(..., min_length=1, description="Slug no puede estar vacío")
    active: bool = True
    settings: Optional[str] = None  # JSON string

class ProfileCreate(ProfileBase):
    pass

class ProfileResponse(ProfileBase):
    id: int

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="Nombre no puede estar vacío si se proporciona")
    slug: Optional[str] = Field(None, min_length=1, description="Slug no puede estar vacío si se proporciona")
    active: Optional[bool] = None
    settings: Optional[str] = None


# Supplier Schemas
class SupplierBase(BaseModel):
    nombre: str = Field(..., min_length=1, description="Nombre no puede estar vacío")
    contacto: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    notas: Optional[str] = None
    activo: bool = True


class SupplierCreate(SupplierBase):
    profile_id: Optional[int] = None  # V2.0: Deprecated, proveedores son globales


class SupplierUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, description="Nombre no puede estar vacío si se proporciona")
    contacto: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    notas: Optional[str] = None
    activo: Optional[bool] = None


class SupplierResponse(SupplierBase):
    id: int
    profile_id: Optional[int] = None  # V2.0: Deprecated, proveedores son globales
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============= IMEI SCHEMAS =============
class IMEIWithLocation(BaseModel):
    """Schema para IMEIs con ubicación asignada - V2.0"""
    imei: str
    location_id: int


# ============= PRODUCT SCHEMAS =============
class ProductBase(BaseModel):
    profile_id: Optional[int] = None  # V2.0: Opcional, productos son globales
    supplier_id: Optional[int] = None
    sku: str = Field(..., min_length=1, description="SKU no puede estar vacío")
    nombre: str = Field(..., min_length=1, description="Nombre no puede estar vacío")
    categoria: CategoriaEnum
    marca: str = Field(..., min_length=1, description="Marca no puede estar vacía")
    modelo: str = Field(..., min_length=1, description="Modelo no puede estar vacío")
    color: Optional[str] = None  # V2.1: Color específico
    capacidad: Optional[str] = None
    condicion: CondicionEnum
    precio: Decimal = Field(..., gt=0, le=1000000, description="Precio debe ser mayor a 0 y menor a 1,000,000")
    costo: Decimal = Field(0, ge=0, description="Costo del producto")
    moneda: str = "HNL"
    garantia_meses: int = Field(0, ge=0, le=120, description="Garantía en meses debe ser entre 0 y 120 (10 años)")
    garantia_condiciones: Optional[str] = None  # Condiciones de garantía del proveedor
    activo: bool = True
    is_serialized: bool = False  # V2.0: Control explícito de serialización
    imei: Optional[str] = None  # DEPRECATED: Usar imeis_con_ubicacion para nuevos productos V2.0
    imeis: Optional[List[str]] = None  # DEPRECATED: Usar imeis_con_ubicacion para V2.0
    
    @field_validator('precio')
    @classmethod
    def validate_precio_positivo(cls, v):
        if v <= 0:
            raise ValueError('El precio debe ser mayor a 0')
        if v > 1000000:
            raise ValueError('El precio máximo permitido es 1,000,000. Verifique el valor ingresado.')
        return v

class ProductCreate(ProductBase):
    cantidad_inicial: int = Field(0, ge=0, le=100000, alias="stock_inicial", description="Stock inicial (máximo 100,000 unidades)")
    initial_location_id: Optional[int] = None  # V2.0: Ubicación inicial del stock
    imeis_con_ubicacion: Optional[List[IMEIWithLocation]] = None  # V2.0: IMEIs con ubicación asignada
    
    @field_validator('cantidad_inicial')
    @classmethod
    def validate_stock_inicial(cls, v):
        if v < 0:
            raise ValueError('El stock inicial no puede ser negativo')
        if v > 100000:
            raise ValueError('El stock inicial máximo permitido es 100,000 unidades. Verifique el valor.')
        return v

    model_config = {
        "populate_by_name": True
    }


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
    is_serialized: Optional[bool] = None  # V2.0: Control explícito de serialización
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
    profile_id: Optional[int] = None  # V2.0: Opcional
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
    garantia_condiciones: Optional[str] = None  # Condiciones de garantía del proveedor
    activo: bool
    is_serialized: bool = False  # V2.0: Control explícito de serialización
    imei: Optional[str] = None  # Mantener por compatibilidad
    imeis: Optional[List[str]] = None  # Array de IMEIs disponibles
    stock_disponible: int
    stock_items: Optional[List[StockByLocationResponse]] = None  # V2.0: Stock por ubicación

    class Config:
        from_attributes = True

class OrderItemCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    cantidad: int = Field(..., gt=0, le=1000, description="Cantidad debe ser mayor a 0 y menor o igual a 1000")
    precio_unitario: Optional[Decimal] = Field(None, ge=0, description="Precio unitario personalizado (descuento/negociación)")
    es_regalo_promocion: bool = False
    imeis: Optional[List[str]] = None  # V2.0: IMEIs específicos para productos serializados
    
    @field_validator('cantidad')
    @classmethod
    def validate_cantidad_positiva(cls, v):
        if v <= 0:
            raise ValueError('La cantidad debe ser mayor a 0')
        if v > 1000:
            raise ValueError('La cantidad máxima permitida por item es 1000. Si necesita más, divida en múltiples órdenes.')
        return v

class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    cantidad: int
    precio_unitario: Decimal
    es_regalo_promocion: bool
    product: ProductResponse
    imeis: Optional[List[str]] = None  # V2.0: IMEIs vendidos en este item

    class Config:
        from_attributes = True


class OrderItemUpdate(BaseModel):
    product_id: int = Field(..., gt=0)
    cantidad: int = Field(..., gt=0, le=1000, description="Cantidad debe ser mayor a 0 y menor o igual a 1000")
    es_regalo_promocion: bool = False
    imeis: Optional[List[str]] = None  # V2.0: IMEIs específicos para productos serializados
    
    @field_validator('cantidad')
    @classmethod
    def validate_cantidad_positiva(cls, v):
        if v <= 0:
            raise ValueError('La cantidad debe ser mayor a 0')
        if v > 1000:
            raise ValueError('La cantidad máxima permitida por item es 1000. Si necesita más, divida en múltiples órdenes.')
        return v
    
    @field_validator('product_id')
    @classmethod
    def validate_product_id_positivo(cls, v):
        if v <= 0:
            raise ValueError('El product_id debe ser mayor a 0')
        return v

class TradeInCreate(BaseModel):
    """Schema para crear un registro de Trade-In"""
    marca: str = Field(..., min_length=1)
    modelo: str = Field(..., min_length=1)
    color: Optional[str] = None      # V2.1
    capacidad: Optional[str] = None  # V2.1
    imei: Optional[str] = None       # V2.1: Opcional al ingreso (se valida en revisión)
    condicion: str = Field(..., description="usado, dañado, para_repuestos")
    precio_venta: Optional[Decimal] = Field(None, gt=0, description="Precio de venta sugerido para el producto resultante")
    valor_estimado: Decimal = Field(..., gt=0)
    notas: Optional[str] = None

    @field_validator('condicion')
    @classmethod
    def validate_condicion(cls, v):
        allowed = ['usado', 'dañado', 'para_repuestos', 'nuevo']
        if v not in allowed:
            raise ValueError(f'Condición inválida. Debe ser una de: {", ".join(allowed)}')
        return v

class TradeInResponse(BaseModel):
    """Schema de respuesta para Trade-In"""
    id: int
    marca: str
    modelo: str
    color: Optional[str] = None
    capacidad: Optional[str] = None
    imei: Optional[str]
    condicion: str
    valor_estimado: Decimal
    created_at: datetime

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    profile_slug: Optional[str] = None  # LEGACY: Compatibilidad con V1, usar sales_profile_slug en su lugar
    sales_profile_slug: Optional[str] = None  # V2.0: Slug del perfil de venta (bot/vendedor)
    source_location_id: int = Field(..., description="V2.0: ID de la ubicación de donde sale el stock (OBLIGATORIO)")
    canal: CanalEnum
    customer_name: str = Field(..., min_length=1, description="Nombre del cliente no puede estar vacío")
    customer_phone: str
    metodo_pago: MetodoPagoEnum
    items: List[OrderItemCreate] = Field(..., min_length=1, description="Debe contener al menos un producto")
    trade_ins: Optional[List[TradeInCreate]] = None  # V2.0: Equipos recibidos en parte de pago
    notes: Optional[str] = None  # Notas adicionales de la orden
    delivery_date: Optional[datetime] = None  # Fecha de entrega programada
    
    # V2.1: Datos de financiamiento (opcional)
    financing_data: Optional[dict] = Field(None, description="Datos de financiamiento: {bank_id, months}")
    
    @field_validator('customer_phone')
    @classmethod
    def validate_phone_is_string(cls, v):
        if v is None:
            raise ValueError('customer_phone cannot be None')
        return str(v).strip()
    
    @field_validator('source_location_id')
    @classmethod
    def validate_location_required(cls, v):
        if v is None or v <= 0:
            raise ValueError('source_location_id es obligatorio y debe ser mayor a 0 en V2.0')
        return v

    @model_validator(mode='after')
    def validate_at_least_one_slug(self):
        if not self.sales_profile_slug and not self.profile_slug:
            raise ValueError('Debe proporcionar sales_profile_slug (V2.0) o profile_slug (legacy)')
        return self

class OrderResponse(BaseModel):
    id: int
    profile_id: Optional[int] = None  # LEGACY: ID del perfil antiguo (V1)
    sales_profile_id: Optional[int] = None  # V2.0: ID del perfil de venta (bot/vendedor)
    source_location_id: Optional[int] = None  # V2.0: ID de la ubicación origen del stock
    customer_name: str
    customer_phone: str
    canal: str
    metodo_pago: str
    total: Decimal
    financing_details: Optional[str] = None # JSON string
    estado: str
    notes: Optional[str] = None
    delivery_date: Optional[datetime] = None
    created_at: datetime
    items: List[OrderItemResponse]
    trade_ins: Optional[List[TradeInResponse]] = None

    class Config:
        from_attributes = True

class OrderListResponse(BaseModel):
    id: int
    profile_id: Optional[int] = None  # LEGACY
    sales_profile_id: Optional[int] = None  # V2.0
    source_location_id: Optional[int] = None  # V2.0
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
    items: Optional[List[OrderItemUpdate]] = Field(None, min_length=1, description="Si se proporciona, debe contener al menos un producto")
    notes: Optional[str] = None
    delivery_date: Optional[datetime] = None
    
    @field_validator('items')
    @classmethod
    def validate_items_not_empty(cls, v):
        if v is not None and len(v) == 0:
            raise ValueError('Si proporciona items, la lista debe contener al menos un producto')
        return v


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




# Stock Transfer Schemas
class StockTransferCreate(BaseModel):
    """Schema para crear una transferencia de stock entre ubicaciones (V2.0)"""
    product_id: int
    from_location_id: int = Field(..., description="ID de ubicación origen")
    to_location_id: int = Field(..., description="ID de ubicación destino")
    cantidad: int = Field(..., gt=0, le=10000, description="Cantidad a transferir (máxima 10,000 unidades por transferencia)")
    imeis: Optional[List[str]] = Field(None, description="Lista de IMEIs específicos a transferir (opcional)")
    notas: Optional[str] = None
    created_by: Optional[str] = None
    
    @field_validator('to_location_id')
    @classmethod
    def validate_different_locations(cls, v, info):
        if 'from_location_id' in info.data and v == info.data['from_location_id']:
            raise ValueError('Las ubicaciones de origen y destino deben ser diferentes')
        return v

    @field_validator('imeis')
    @classmethod
    def validate_imeis_count(cls, v, info):
        if v is not None and 'cantidad' in info.data:
            if len(v) != info.data['cantidad']:
                raise ValueError(f'La cantidad de IMEIs ({len(v)}) no coincide con la cantidad a transferir ({info.data["cantidad"]})')
        return v


class StockTransferResponse(BaseModel):
    """Schema para la respuesta de una transferencia de stock (V2.0)"""
    id: int
    product_id: int
    from_location_id: int
    to_location_id: int
    from_profile_id: Optional[int] = None  # Legacy V1, puede ser None
    to_profile_id: Optional[int] = None  # Legacy V1, puede ser None
    cantidad: int
    notas: Optional[str]
    estado: str
    confirmed_at: Optional[datetime] = None
    confirmed_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    created_by: Optional[str]
    imeis: Optional[List[str]] = None  # V2.0: Lista de IMEIs transferidos
    
    # Información adicional del producto y ubicaciones
    product_nombre: Optional[str] = None
    product_sku: Optional[str] = None
    from_location_name: Optional[str] = None
    to_location_name: Optional[str] = None
    # Legacy (compatibilidad V1)
    from_profile_name: Optional[str] = None
    to_profile_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class StockTransferConfirm(BaseModel):
    """Schema para confirmar una transferencia"""
    confirmed_by: Optional[str] = None
    scanned_imeis: Optional[List[str]] = None  # V2.0: Validación de recepción física


class StockTransferReject(BaseModel):
    """Schema para rechazar una transferencia"""
    rejection_reason: str = Field(..., min_length=1, description="Razón del rechazo")
    rejected_by: Optional[str] = None


# ============= RETURN SCHEMAS =============

class ReturnItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    condition: ReturnConditionEnum
    action: ReturnActionEnum
    imei: Optional[str] = None

class ReturnCreate(BaseModel):
    order_id: int
    reason: Optional[str] = None
    created_by: Optional[str] = None
    items: List[ReturnItemCreate]

class ReturnItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    condition: str
    action: str
    imei: Optional[str]
    
    class Config:
        from_attributes = True

class ReturnResponse(BaseModel):
    id: int
    order_id: int
    created_at: datetime
    reason: Optional[str]
    status: str
    created_by: Optional[str]
    items: List[ReturnItemResponse]
    
    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True


# ============= FINANCING SCHEMAS =============

class FinancingOptionBase(BaseModel):
    months: int = Field(..., gt=0, description="Plazo en meses")
    rate: Decimal = Field(..., ge=0, description="Tasa de recargo (ej. 0.05 para 5%)")
    active: bool = True

class FinancingOptionCreate(FinancingOptionBase):
    pass

class FinancingOptionResponse(FinancingOptionBase):
    id: int
    bank_id: int
    
    class Config:
        from_attributes = True

class BankBase(BaseModel):
    name: str = Field(..., min_length=1)
    active: bool = True
    normal_card_rate: float = Field(0.0, ge=0, le=1, description="Tasa para tarjeta normal (0.0 - 1.0)")

class BankCreate(BankBase):
    financing_options: Optional[List[FinancingOptionCreate]] = None

class BankUpdate(BaseModel):
    name: Optional[str] = None
    active: Optional[bool] = None
    normal_card_rate: Optional[float] = Field(None, ge=0, le=1)

class BankResponse(BankBase):
    id: int
    financing_options: List[FinancingOptionResponse] = []
    
    class Config:
        from_attributes = True


# Trade-In Policies
class TradeInPolicyBase(BaseModel):
    rule_type: str = Field(..., description="model_rejection, brand_rejection, condition_rejection")
    pattern: str = Field(..., min_length=1, description="Patrón a buscar (ej. 'iPhone 7', 'Xiaomi')")
    action: str = Field("reject", description="reject, accept_with_conditions")
    reason: Optional[str] = None
    is_active: bool = True

class TradeInPolicyCreate(TradeInPolicyBase):
    pass

class TradeInPolicyResponse(TradeInPolicyBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

