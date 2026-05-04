from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


def _utcnow() -> datetime:
    """Genera timestamps conscientes de zona horaria para columnas UTC."""
    return datetime.now(timezone.utc)


class Product(Base):
    """Productos globales visibles para todos los perfiles de venta."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    sku = Column(String, unique=True, nullable=False, index=True)
    nombre = Column(String, nullable=False, index=True)
    categoria = Column(String, nullable=False, index=True)
    marca = Column(String, nullable=False, index=True)
    modelo = Column(String, nullable=False, index=True)
    color = Column(String, nullable=True, index=True)
    capacidad = Column(String)
    condicion = Column(String, nullable=False)
    precio = Column(Numeric(10, 2), nullable=False)
    costo = Column(Numeric(10, 2), default=0, nullable=False)
    moneda = Column(String, default="Lps", nullable=False)
    garantia_meses = Column(Integer, default=0, nullable=False)
    garantia_condiciones = Column(Text, nullable=True)
    activo = Column(Boolean, default=True, nullable=False, index=True)
    is_serialized = Column(Boolean, default=False, nullable=False)

    profile = relationship("Profile", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")
    stock_items = relationship("Stock", back_populates="product", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product", passive_deletes="all")
    stock_history = relationship("StockHistory", back_populates="product", cascade="all, delete-orphan")
    imeis = relationship("ProductIMEI", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_product_active_categoria", "activo", "categoria"),
        Index("idx_product_profile_active", "profile_id", "activo"),
        Index("idx_product_supplier", "supplier_id"),
    )


class Stock(Base):
    """Stock por ubicación física."""

    __tablename__ = "stock"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True)
    cantidad_disponible = Column(Integer, default=0, nullable=False)
    cantidad_reservada = Column(Integer, default=0, nullable=False)
    cantidad_defectuosa = Column(Integer, default=0, nullable=False)

    product = relationship("Product", back_populates="stock_items")
    location = relationship("Location", back_populates="stock_items")

    __table_args__ = (
        Index("idx_stock_product_location", "product_id", "location_id", unique=True),
        Index("idx_stock_location", "location_id"),
        CheckConstraint("cantidad_disponible >= 0", name="check_stock_positive"),
        CheckConstraint("cantidad_reservada >= 0", name="check_reserved_positive"),
        CheckConstraint("cantidad_defectuosa >= 0", name="check_defective_positive"),
    )


class ProductIMEI(Base):
    """Registro de múltiples IMEIs asociados a productos."""

    __tablename__ = "product_imeis"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    imei = Column(String, unique=True, nullable=False, index=True)
    vendido = Column(Boolean, default=False, nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    transfer_id = Column(Integer, ForeignKey("stock_transfers.id", ondelete="SET NULL"), nullable=True, index=True)
    received_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
    sold_at = Column(DateTime(timezone=True), nullable=True, index=True)
    acquisition_type = Column(String(50), nullable=True, index=True)
    received_notes = Column(Text, nullable=True)
    received_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    product = relationship("Product", back_populates="imeis")
    location = relationship("Location")
    supplier = relationship("Supplier")
    order = relationship("Order", backref="imeis_vendidos")
    transfer = relationship("StockTransfer", backref="imeis_en_transito")

    __table_args__ = (
        Index("idx_product_imei_vendido", "product_id", "vendido"),
        Index("idx_product_imei_location", "location_id"),
        Index("idx_product_imei_transfer", "transfer_id"),
        Index("idx_product_imei_supplier", "supplier_id"),
    )


class StockHistory(Base):
    """Historial de movimientos de stock para auditoría."""

    __tablename__ = "stock_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True)
    tipo_cambio = Column(String(50), nullable=False, index=True)
    cantidad = Column(Integer, nullable=False)
    stock_anterior = Column(Integer, nullable=False)
    stock_nuevo = Column(Integer, nullable=False)
    referencia_id = Column(Integer, nullable=True)
    referencia_tipo = Column(String(50), nullable=True)
    notas = Column(Text, nullable=True)
    usuario = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    product = relationship("Product", foreign_keys=[product_id])
    location = relationship("Location")

    __table_args__ = (
        Index("idx_stock_history_product_date", "product_id", "created_at"),
        Index("idx_stock_history_tipo", "tipo_cambio"),
        Index("idx_stock_history_referencia", "referencia_tipo", "referencia_id"),
        Index("idx_stock_history_location", "location_id"),
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
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (Index("idx_faq_activa_veces_usada", "activa", "veces_usada"),)


class IMEIHistory(Base):
    """Historial completo del ciclo de vida de un IMEI."""

    __tablename__ = "imei_history"

    id = Column(Integer, primary_key=True, index=True)
    imei = Column(String, index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String, nullable=False)
    reference_id = Column(Integer, nullable=True)
    reference_type = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    created_by = Column(String, nullable=True)

    product = relationship("Product")
    location = relationship("Location")
    supplier = relationship("Supplier")

    __table_args__ = (
        Index("idx_imei_history_imei", "imei"),
        Index("idx_imei_history_product", "product_id"),
        Index("idx_imei_history_date", "created_at"),
    )


__all__ = [
    "Product",
    "Stock",
    "ProductIMEI",
    "StockHistory",
    "FAQEntry",
    "IMEIHistory",
]
