from datetime import datetime
from sqlalchemy import Boolean, Column, Integer, String, Numeric, ForeignKey, DateTime, Text, Index, Table, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# Association table for Role-Permission many-to-many relationship
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete="CASCADE"), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete="CASCADE"), primary_key=True)
)

class Permission(Base):
    """Permisos granulares del sistema (ej: 'products:create', 'inventory:view')"""
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, nullable=False, index=True) # ej: products:create
    description = Column(String, nullable=False) # ej: Crear nuevos productos
    module = Column(String, nullable=False) # ej: products, orders, settings

class Role(Base):
    """Roles de usuario (Admin, Gerente, Vendedor, Invitado)"""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    is_system_role = Column(Boolean, default=False) # Si es True, no se puede borrar (ej: Admin)
    
    permissions = relationship("Permission", secondary=role_permissions, backref="roles")
    users = relationship("User", back_populates="role")

class User(Base):
    """User model for authentication"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=True, index=True) # Email opcional
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False) # Fallback para acceso total
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    role = relationship("Role", back_populates="users")


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
    settings = Column(Text, nullable=True)  # V2.0: Added for legacy compatibility

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
    color = Column(String, nullable=True, index=True)  # V2.1: Color específico (ej. Sierra Blue)
    capacidad = Column(String)
    condicion = Column(String, nullable=False)
    precio = Column(Numeric(10, 2), nullable=False)
    costo = Column(Numeric(10, 2), default=0, nullable=False)  # V2.0: Costo para reportes financieros
    moneda = Column(String, default="Lps", nullable=False)
    garantia_meses = Column(Integer, default=0, nullable=False)
    garantia_condiciones = Column(Text, nullable=True)
    activo = Column(Boolean, default=True, nullable=False, index=True)
    is_serialized = Column(Boolean, default=False, nullable=False)  # V2.0: Control explícito de serialización

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
    cantidad_reservada = Column(Integer, default=0, nullable=False)  # V2.0: Stock reservado en transferencias pendientes
    cantidad_defectuosa = Column(Integer, default=0, nullable=False)  # V2.0: Stock defectuoso/merma
    # NOTA: SQLite no soporta CHECK constraints de forma consistente
    # Se debe validar cantidad_disponible >= 0 en la lógica de aplicación
    # Todas las operaciones deben verificar esto antes de commit
    # Stock real disponible para venta = cantidad_disponible - cantidad_reservada

    product = relationship("Product", back_populates="stock_items")
    location = relationship("Location", back_populates="stock_items")
    
    __table_args__ = (
        # Un producto solo puede tener un registro de stock por ubicación
        Index('idx_stock_product_location', 'product_id', 'location_id', unique=True),
        Index('idx_stock_location', 'location_id'),
        # CRÍTICO: Evitar stock negativo
        CheckConstraint('cantidad_disponible >= 0', name='check_stock_positive'),
        CheckConstraint('cantidad_reservada >= 0', name='check_reserved_positive'),
        CheckConstraint('cantidad_defectuosa >= 0', name='check_defective_positive'),
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
    transfer_id = Column(Integer, ForeignKey("stock_transfers.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    product = relationship("Product", back_populates="imeis")
    location = relationship("Location")
    order = relationship("Order", backref="imeis_vendidos")
    transfer = relationship("StockTransfer", backref="imeis_en_transito")
    
    __table_args__ = (
        Index('idx_product_imei_vendido', 'product_id', 'vendido'),
        Index('idx_product_imei_location', 'location_id'),
        Index('idx_product_imei_transfer', 'transfer_id'),
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
    financing_details = Column(Text, nullable=True)  # JSON: {bank_id, bank_name, months, rate, surcharge, monthly_payment}
    estado = Column(String, default="pendiente", nullable=False, index=True)
    notes = Column(Text, nullable=True)
    delivery_date = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    sales_profile = relationship("SalesProfile", back_populates="orders")
    source_location = relationship("Location", back_populates="orders")
    profile = relationship("Profile", foreign_keys=[profile_id], back_populates="orders_legacy")  # Temporal
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    trade_ins = relationship("TradeIn", back_populates="order", cascade="all, delete-orphan")
    
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


class TradeIn(Base):
    """Registro de equipos recibidos como parte de pago (Trade-In)"""
    __tablename__ = "trade_ins"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    marca = Column(String, nullable=False)
    modelo = Column(String, nullable=False)
    color = Column(String, nullable=True)      # V2.1: Nuevo campo
    capacidad = Column(String, nullable=True)  # V2.1: Nuevo campo
    imei = Column(String, nullable=True)  # Puede ser null si no es celular
    condicion = Column(String, nullable=False)  # 'usado', 'dañado', 'para_repuestos'
    valor_estimado = Column(Numeric(10, 2), nullable=False)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order = relationship("Order", back_populates="trade_ins")


class IMEIHistory(Base):
    """Historial completo del ciclo de vida de un IMEI"""
    __tablename__ = "imei_history"

    id = Column(Integer, primary_key=True, index=True)
    imei = Column(String, index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    event_type = Column(String, nullable=False) # 'ingreso', 'venta', 'transferencia', 'devolucion', 'retoma'
    reference_id = Column(Integer, nullable=True) # order_id, transfer_id
    reference_type = Column(String, nullable=True) # 'order', 'transfer', 'stock_adjustment'
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    created_by = Column(String, nullable=True)

    product = relationship("Product")
    location = relationship("Location")
    
    __table_args__ = (
        Index('idx_imei_history_imei', 'imei'),
        Index('idx_imei_history_product', 'product_id'),
        Index('idx_imei_history_date', 'created_at'),
    )


class Return(Base):
    """Registro de devoluciones y garantías (RMA)"""
    __tablename__ = "returns"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reason = Column(String, nullable=True)
    status = Column(String, default="completed", nullable=False) # completed, pending
    created_by = Column(String, nullable=True)
    
    order = relationship("Order", backref="returns")
    items = relationship("ReturnItem", back_populates="return_obj", cascade="all, delete-orphan")


class ReturnItem(Base):
    """Items individuales dentro de una devolución"""
    __tablename__ = "return_items"

    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(Integer, ForeignKey("returns.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    condition = Column(String, nullable=False) # 'nuevo', 'defectuoso', 'abierto'
    action = Column(String, nullable=False) # 'refund', 'warranty_exchange', 'store_credit'
    imei = Column(String, nullable=True)
    
    return_obj = relationship("Return", back_populates="items")
    product = relationship("Product")


# ==========================================
# MÓDULO DE INTELIGENCIA ARTIFICIAL (V2.1)
# ==========================================

class Customer(Base):
    """
    Cliente enriquecido para gestión de relaciones (CRM) y detección de trolls.
    Centraliza la información de clientes que antes solo vivía en las órdenes.
    """
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Campos de Inteligencia / Seguridad
    is_troll = Column(Boolean, default=False, index=True)
    is_blocked = Column(Boolean, default=False, index=True)
    reputation_score = Column(Integer, default=100)  # 0-100
    daily_message_count = Column(Integer, default=0)
    last_interaction_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    interactions = relationship("InteractionLog", back_populates="customer", cascade="all, delete-orphan")


class AIProfileConfig(Base):
    """
    Configuración de personalidad y reglas para cada Bot de IA.
    Vinculado 1:1 con SalesProfile.
    """
    __tablename__ = "ai_profile_configs"

    id = Column(Integer, primary_key=True, index=True)
    sales_profile_id = Column(Integer, ForeignKey("sales_profiles.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Configuración del Modelo
    model_name = Column(String, default="gpt-4o")
    temperature = Column(Numeric(3, 2), default=0.7)
    
    # Personalidad
    system_prompt = Column(Text, nullable=False)  # La "Biblia" del bot
    initial_greeting = Column(Text, nullable=True)
    voice_tone = Column(String, nullable=True)  # formal, amigable, etc.
    
    # Reglas de Negocio
    context_rules = Column(Text, nullable=True)  # JSON: filtros de inventario, etc.
    is_active = Column(Boolean, default=True)

    # Personalización Avanzada (V2.2)
    business_description = Column(Text, nullable=True)
    sales_goal = Column(String, nullable=True)
    negotiation_style = Column(String, nullable=True)
    max_discount_rate = Column(Numeric(5, 4), default=0.0) # 0.10 = 10%
    fallback_human_trigger = Column(String, nullable=True)
    
    # Notificaciones (V2.1)
    admin_notification_phone = Column(String, nullable=True)  # WhatsApp del admin para alertas
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sales_profile = relationship("SalesProfile", backref="ai_config")


class InteractionLog(Base):
    """
    Historial de conversaciones entre Clientes y Bots.
    Permite auditoría y reentrenamiento.
    """
    __tablename__ = "interaction_logs"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    sales_profile_id = Column(Integer, ForeignKey("sales_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    role = Column(String, nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, default=0)
    
    # Atribución de Venta
    converted_order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    customer = relationship("Customer", back_populates="interactions")
    sales_profile = relationship("SalesProfile")
    converted_order = relationship("Order")


class TrainingQueue(Base):
    """
    Cola de aprendizaje (Human-in-the-loop).
    Preguntas que la IA no supo responder y requieren intervención humana.
    """
    __tablename__ = "training_queue"

    id = Column(Integer, primary_key=True, index=True)
    sales_profile_id = Column(Integer, ForeignKey("sales_profiles.id", ondelete="SET NULL"), nullable=True)
    
    customer_question = Column(Text, nullable=False)
    ai_proposed_answer = Column(Text, nullable=True)
    admin_correction = Column(Text, nullable=True)
    
    status = Column(String, default="pending", index=True)  # pending, approved, rejected, converted_to_faq
    
    sales_profile = relationship("SalesProfile")


class Bank(Base):
    """Bancos para extrafinanciamiento"""
    __tablename__ = "banks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    active = Column(Boolean, default=True, nullable=False)
    normal_card_rate = Column(Numeric(5, 4), default=0.0, nullable=False) # Tasa para tarjeta normal (no extra)
    
    financing_options = relationship("FinancingOption", back_populates="bank", cascade="all, delete-orphan")


class FinancingOption(Base):
    """Opciones de financiamiento (Plazos y Tasas) por Banco"""
    __tablename__ = "financing_options"

    id = Column(Integer, primary_key=True, index=True)
    bank_id = Column(Integer, ForeignKey("banks.id", ondelete="CASCADE"), nullable=False, index=True)
    months = Column(Integer, nullable=False) # 3, 6, 9, 12, 18, 24
    rate = Column(Numeric(5, 4), nullable=False) # Porcentaje de recargo (ej. 0.05 para 5%)
    active = Column(Boolean, default=True, nullable=False)

    bank = relationship("Bank", back_populates="financing_options")


class TradeInPolicy(Base):
    """
    Políticas de Retoma (Trade-In) aprendibles/configurables.
    Define qué marcas/modelos se aceptan o rechazan.
    """
    __tablename__ = "trade_in_policies"

    id = Column(Integer, primary_key=True, index=True)
    rule_type = Column(String, default="model_rejection") # model_rejection, brand_rejection, condition_rejection
    pattern = Column(String, nullable=False) # e.g., "iPhone XR", "Xiaomi", "Pantalla quebrada"
    action = Column(String, default="reject") # reject, accept_with_conditions
    reason = Column(String, nullable=True) # "No tiene mercado", "Muy viejo"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


