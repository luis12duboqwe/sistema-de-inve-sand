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


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    active = Column(Boolean, default=True, nullable=False, index=True)

    products = relationship("Product", back_populates="profile", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="profile", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
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
    activo = Column(Boolean, default=True, nullable=False, index=True)

    profile = relationship("Profile", back_populates="products")
    stock = relationship("Stock", back_populates="product", uselist=False, cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product")
    
    __table_args__ = (
        Index('idx_product_active_categoria', 'activo', 'categoria'),
        Index('idx_product_profile_active', 'profile_id', 'activo'),
    )

class Stock(Base):
    __tablename__ = "stock"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    cantidad_disponible = Column(Integer, default=0, nullable=False)

    product = relationship("Product", back_populates="stock")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False, index=True)
    canal = Column(String, nullable=False, index=True)
    metodo_pago = Column(String, nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    estado = Column(String, default="pendiente", nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    profile = relationship("Profile", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_order_profile_estado', 'profile_id', 'estado'),
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
