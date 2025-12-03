from datetime import datetime
from sqlalchemy import Boolean, Column, Integer, String, Numeric, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    active = Column(Boolean, default=True, nullable=False)

    products = relationship("Product", back_populates="profile")
    orders = relationship("Order", back_populates="profile")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    sku = Column(String, unique=True, nullable=False, index=True)
    nombre = Column(String, nullable=False)
    categoria = Column(String, nullable=False)
    marca = Column(String, nullable=False)
    modelo = Column(String, nullable=False)
    capacidad = Column(String)
    condicion = Column(String, nullable=False)
    precio = Column(Numeric(10, 2), nullable=False)
    moneda = Column(String, default="HNL", nullable=False)
    garantia_meses = Column(Integer, default=0, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

    profile = relationship("Profile", back_populates="products")
    stock = relationship("Stock", back_populates="product", uselist=False)
    order_items = relationship("OrderItem", back_populates="product")

class Stock(Base):
    __tablename__ = "stock"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), unique=True, nullable=False)
    cantidad_disponible = Column(Integer, default=0, nullable=False)

    product = relationship("Product", back_populates="stock")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    canal = Column(String, nullable=False)
    metodo_pago = Column(String, nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    estado = Column(String, default="pendiente", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    profile = relationship("Profile", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    es_regalo_promocion = Column(Boolean, default=False, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class FAQEntry(Base):
    __tablename__ = "faq_entries"

    id = Column(Integer, primary_key=True, index=True)
    pregunta_clave = Column(String(255), nullable=False)
    ejemplo_pregunta_cliente = Column(Text, nullable=True)
    respuesta = Column(Text, nullable=False)
    categoria = Column(String(50), nullable=False)
    nivel_seriedad = Column(String(20), nullable=False, default="normal")
    activa = Column(Boolean, default=True)
    veces_usada = Column(Integer, default=0)
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
