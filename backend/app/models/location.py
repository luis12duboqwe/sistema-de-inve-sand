from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from app.database import Base
from app.location_identity import (
    location_name_hash,
    location_name_key,
    normalize_location_name,
)
from app.sales_profile_identity import (
    normalize_sales_profile_slug,
    sales_profile_slug_hash,
    sales_profile_slug_key,
)
from app.supplier_identity import (
    normalize_supplier_name,
    supplier_name_hash,
    supplier_name_key,
)


class Location(Base):
    """Ubicación física (tienda, bodega, oficina)."""

    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    nombre_normalized = Column(Text, nullable=False)
    nombre_key_hash = Column(String(64), nullable=False, unique=True, index=True)
    tipo = Column(String, nullable=False, index=True)
    direccion = Column(Text, nullable=True)
    telefono = Column(String, nullable=True)
    activo = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    stock_items = relationship("Stock", back_populates="location", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="source_location")

    __table_args__ = (Index("idx_location_tipo_activo", "tipo", "activo"),)

    @validates("nombre")
    def _canonicalize_nombre(self, _key: str, value: str) -> str:
        normalized = normalize_location_name(value)
        self.nombre_normalized = location_name_key(normalized)
        self.nombre_key_hash = location_name_hash(normalized)
        return normalized


class SalesProfile(Base):
    """Perfil de venta (vendedor humano, bot IA, integraciones)."""

    __tablename__ = "sales_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    slug_normalized = Column(Text, nullable=False)
    slug_key_hash = Column(String(64), nullable=False, unique=True, index=True)
    tipo = Column(String, nullable=False, index=True)
    canales = Column(Text, nullable=True)
    active = Column(Boolean, default=True, nullable=False, index=True)
    configuracion = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    orders = relationship("Order", back_populates="sales_profile")

    __table_args__ = (Index("idx_sales_profile_tipo_active", "tipo", "active"),)

    @validates("slug")
    def _canonicalize_slug(self, _key: str, value: str) -> str:
        normalized = normalize_sales_profile_slug(value)
        self.slug_normalized = sales_profile_slug_key(normalized)
        self.slug_key_hash = sales_profile_slug_hash(normalized)
        return normalized


class Profile(Base):
    """Modelo legacy para compatibilidad (V1 perfiles)."""

    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    active = Column(Boolean, default=True, nullable=False, index=True)
    settings = Column(Text, nullable=True)

    products = relationship("Product", back_populates="profile")
    orders_legacy = relationship("Order", foreign_keys="Order.profile_id")
    suppliers = relationship("Supplier", back_populates="profile")


class Supplier(Base):
    """Proveedor para trazabilidad y garantías."""

    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    # Persist the full canonical identity for diagnostics/migration verification.
    nombre_normalized = Column(Text, nullable=False)
    # Fixed-size digest owns DB-level uniqueness consistently on PostgreSQL/SQLite.
    nombre_key_hash = Column(String(64), nullable=False, unique=True, index=True)
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

    __table_args__ = (Index("idx_supplier_profile_active", "profile_id", "activo"),)

    @validates("nombre")
    def _canonicalize_nombre(self, _key: str, value: str) -> str:
        normalized = normalize_supplier_name(value)
        self.nombre_normalized = supplier_name_key(normalized)
        self.nombre_key_hash = supplier_name_hash(normalized)
        return normalized


__all__ = ["Location", "SalesProfile", "Profile", "Supplier"]
