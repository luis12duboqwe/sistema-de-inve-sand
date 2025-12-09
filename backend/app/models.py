from datetime import datetime
from sqlalchemy import Boolean, Column, Integer, String, Numeric, ForeignKey, DateTime, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """User model for authentication"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Location(Base):
    """Ubicación física (Tienda 1, Tienda 2, Tienda 3, Bodega, etc.)"""
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    tipo = Column(String, nullable=False, index=True)  # 'tienda', 'bodega', 'oficina'
    direccion = Column(Text, nullable=True)
    telefono = Column(String, nullable=True)
    activo = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relaciones
    stock_items = relationship("Stock", back_populates="location", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="source_location")
    
    __table_args__ = (
        Index('idx_location_tipo_activo', 'tipo', 'activo'),
    )


class SalesProfile(Base):
    """Perfil de venta (vendedor, bot de IA, canal online)
    Cada perfil puede manejar WhatsApp, Facebook, Instagram
    Todos los perfiles ven el inventario completo de todas las ubicaciones
    """
    __tablename__ = "sales_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    tipo = Column(String, nullable=False, index=True)  # 'bot_ia', 'vendedor_humano', 'sistema_automatico'
    canales = Column(Text, nullable=True)  # JSON: ["whatsapp", "facebook", "instagram"]
    active = Column(Boolean, default=True, nullable=False, index=True)
    configuracion = Column(Text, nullable=True)  # JSON: configuración específica del perfil
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # V2.0: Sin cascade para preservar historial de ventas
    orders = relationship("Order", back_populates="sales_profile")
    
    __table_args__ = (
        Index('idx_sales_profile_tipo_active', 'tipo', 'active'),
    )


# Mantener Profile por compatibilidad (alias temporal)
class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    active = Column(Boolean, default=True, nullable=False, index=True)

    # V2.0: Cambiado a back_populates sin cascade, Product.profile_id ahora es SET NULL
    products = relationship("Product", back_populates="profile")
    # V2.0: Sin cascade para preservar historial de órdenes legacy
    orders_legacy = relationship("Order", foreign_keys="Order.profile_id")
    # V2.0: Suppliers son globales, relación sin cascade
    suppliers = relationship("Supplier", back_populates="profile")


class Supplier(Base):
    """Modelo de Proveedor para gestión de reclamos y trazabilidad"""
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True)  # V2.0: Proveedores ahora son globales
    nombre = Column(String, nullable=False, index=True)
    contacto = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    email = Column(String, nullable=True)
    direccion = Column(Text, nullable=True)
    notas = Column(Text, nullable=True)
    activo = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    profile = relationship("Profile", back_populates="suppliers")
    products = relationship("Product", back_populates="supplier")
    
    __table_args__ = (
        Index('idx_supplier_profile_active', 'profile_id', 'activo'),
    )

class Product(Base):
    """Productos globales - visibles para todos los sales profiles
    El stock se maneja por ubicación
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True)  # V2.0: SET NULL en vez de CASCADE
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    sku = Column(String, unique=True, nullable=False, index=True)
    nombre = Column(String, nullable=False, index=True)
    categoria = Column(String, nullable=False, index=True)
    marca = Column(String, nullable=False, index=True)
    modelo = Column(String, nullable=False, index=True)
    capacidad = Column(String)
    condicion = Column(String, nullable=False)
    precio = Column(Numeric(10, 2), nullable=False)
    moneda = Column(String, default="HNL", nullable=False)
    garantia_meses = Column(Integer, default=0, nullable=False)
    garantia_condiciones = Column(Text, nullable=True)
    activo = Column(Boolean, default=True, nullable=False, index=True)

    profile = relationship("Profile", back_populates="products")  # Temporal - será eliminado
    supplier = relationship("Supplier", back_populates="products")
    stock_items = relationship("Stock", back_populates="product", cascade="all, delete-orphan")  # Stock por ubicación
    order_items = relationship("OrderItem", back_populates="product", passive_deletes='all')
    stock_history = relationship("StockHistory", back_populates="product", cascade="all, delete-orphan")
    imeis = relationship("ProductIMEI", back_populates="product", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_product_active_categoria', 'activo', 'categoria'),
        Index('idx_product_profile_active', 'profile_id', 'activo'),
        Index('idx_product_supplier', 'supplier_id'),
    )

class Stock(Base):
    """Stock por ubicación física - un producto puede tener stock en múltiples ubicaciones"""
    __tablename__ = "stock"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True)
    cantidad_disponible = Column(Integer, default=0, nullable=False)
    # NOTA: SQLite no soporta CHECK constraints de forma consistente
    # Se debe validar cantidad_disponible >= 0 en la lógica de aplicación
    # Todas las operaciones deben verificar esto antes de commit

    product = relationship("Product", back_populates="stock_items")
    location = relationship("Location", back_populates="stock_items")
    
    __table_args__ = (
        # Un producto solo puede tener un registro de stock por ubicación
        Index('idx_stock_product_location', 'product_id', 'location_id', unique=True),
        Index('idx_stock_location', 'location_id'),
        # CRÍTICO: Evitar stock negativo
        # Nota: SQLite no soporta CHECK constraints nativamente en todas las versiones
        # Se debe validar en la lógica de aplicación ANTES de cada db.commit()
    )


class ProductIMEI(Base):
    """Tabla para registrar múltiples IMEIs para productos con stock > 1
    Ahora también registra la ubicación del IMEI
    """
    __tablename__ = "product_imeis"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True)
    imei = Column(String, unique=True, nullable=False, index=True)
    vendido = Column(Boolean, default=False, nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    product = relationship("Product", back_populates="imeis")
    location = relationship("Location")
    order = relationship("Order", backref="imeis_vendidos")
    
    __table_args__ = (
        Index('idx_product_imei_vendido', 'product_id', 'vendido'),
        Index('idx_product_imei_location', 'location_id'),
    )

class Order(Base):
    """Órdenes de venta
    - sales_profile_id: Qué perfil/vendedor realizó la venta
    - source_location_id: De qué ubicación se tomó el stock
    - profile_id: Temporal, mantiene compatibilidad
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    sales_profile_id = Column(Integer, ForeignKey("sales_profiles.id", ondelete="SET NULL"), nullable=True, index=True)  # V2.0: Preservar órdenes
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True)  # LEGACY: Preservar órdenes
    source_location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False, index=True)
    canal = Column(String, nullable=False, index=True)
    metodo_pago = Column(String, nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    estado = Column(String, default="pendiente", nullable=False, index=True)
    notes = Column(Text, nullable=True)
    delivery_date = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    sales_profile = relationship("SalesProfile", back_populates="orders")
    source_location = relationship("Location", back_populates="orders")
    profile = relationship("Profile", foreign_keys=[profile_id], back_populates="orders_legacy")  # Temporal
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_order_sales_profile_estado', 'sales_profile_id', 'estado'),
        Index('idx_order_source_location', 'source_location_id'),
        Index('idx_order_delivery_date', 'delivery_date'),
    )

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    es_regalo_promocion = Column(Boolean, default=False, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class StockTransfer(Base):
    """Modelo para registrar transferencias de stock entre UBICACIONES (no perfiles)
    Ahora las transferencias son entre tiendas/bodegas físicas
    """
    __tablename__ = "stock_transfers"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    from_location_id = Column(Integer, ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False, index=True)
    to_location_id = Column(Integer, ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False, index=True)
    # Campos legacy para compatibilidad
    from_profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="RESTRICT"), nullable=True, index=True)
    to_profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="RESTRICT"), nullable=True, index=True)
    cantidad = Column(Integer, nullable=False)
    notas = Column(Text, nullable=True)
    estado = Column(String(20), default="pendiente", nullable=False, index=True)  # pendiente, confirmada, rechazada, cancelada
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    confirmed_by = Column(String(100), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    created_by = Column(String(100), nullable=True)

    # Relationships
    product = relationship("Product", foreign_keys=[product_id])
    from_location = relationship("Location", foreign_keys=[from_location_id])
    to_location = relationship("Location", foreign_keys=[to_location_id])
    from_profile = relationship("Profile", foreign_keys=[from_profile_id])
    to_profile = relationship("Profile", foreign_keys=[to_profile_id])
    
    __table_args__ = (
        Index('idx_transfer_product', 'product_id'),
        Index('idx_transfer_from_location', 'from_location_id'),
        Index('idx_transfer_to_location', 'to_location_id'),
        Index('idx_transfer_created', 'created_at'),
        Index('idx_transfer_estado', 'estado'),
    )


class StockHistory(Base):
    """Historial de cambios de stock para trazabilidad completa
    Ahora incluye información de ubicación
    """
    __tablename__ = "stock_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True)
    tipo_cambio = Column(String(50), nullable=False, index=True)  # 'venta', 'transferencia_salida', 'transferencia_entrada', 'ajuste', 'devolucion'
    cantidad = Column(Integer, nullable=False)  # Positivo para entrada, negativo para salida
    stock_anterior = Column(Integer, nullable=False)
    stock_nuevo = Column(Integer, nullable=False)
    referencia_id = Column(Integer, nullable=True)  # ID de orden, transferencia, etc.
    referencia_tipo = Column(String(50), nullable=True)  # 'order', 'transfer', 'adjustment'
    notas = Column(Text, nullable=True)
    usuario = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    product = relationship("Product", foreign_keys=[product_id])
    location = relationship("Location")
    
    __table_args__ = (
        Index('idx_stock_history_product_date', 'product_id', 'created_at'),
        Index('idx_stock_history_tipo', 'tipo_cambio'),
        Index('idx_stock_history_referencia', 'referencia_tipo', 'referencia_id'),
        Index('idx_stock_history_location', 'location_id'),
    )


class FAQEntry(Base):
    __tablename__ = "faq_entries"

    id = Column(Integer, primary_key=True, index=True)
    pregunta_clave = Column(String(255), nullable=False, index=True)
    ejemplo_pregunta_cliente = Column(Text, nullable=True)
    respuesta = Column(Text, nullable=False)
    categoria = Column(String(50), nullable=False, index=True)
    nivel_seriedad = Column(String(20), nullable=False, default="normal", index=True)
    activa = Column(Boolean, default=True, index=True)
    veces_usada = Column(Integer, default=0, index=True)
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_faq_activa_veces_usada', 'activa', 'veces_usada'),
    )
