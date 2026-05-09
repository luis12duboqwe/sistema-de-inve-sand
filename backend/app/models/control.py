from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class UserLocationAccess(Base):
    """Alcance operativo de un usuario por ubicación."""

    __tablename__ = "user_location_access"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True)
    can_view = Column(Boolean, default=True, nullable=False)
    can_edit = Column(Boolean, default=False, nullable=False)
    can_close_cash = Column(Boolean, default=False, nullable=False)
    can_count_stock = Column(Boolean, default=False, nullable=False)
    can_receive_purchase = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    location = relationship("Location")

    __table_args__ = (
        UniqueConstraint("user_id", "location_id", name="uq_user_location_access"),
        Index("idx_user_location_access_user", "user_id"),
        Index("idx_user_location_access_location", "location_id"),
    )


class AuditLog(Base):
    """Bitácora genérica para acciones críticas."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(100), nullable=True, index=True)
    action = Column(String(80), nullable=False, index=True)
    entity_type = Column(String(80), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True)
    before_data = Column(Text, nullable=True)
    after_data = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    user = relationship("User")
    location = relationship("Location")

    __table_args__ = (
        Index("idx_audit_action_date", "action", "created_at"),
        Index("idx_audit_entity", "entity_type", "entity_id"),
    )


class PurchaseReceipt(Base):
    """Recepción formal de compra/proveedor en una ubicación."""

    __tablename__ = "purchase_receipts"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False, index=True)
    invoice_number = Column(String(120), nullable=True, index=True)
    status = Column(String(30), default="received", nullable=False, index=True)
    total_cost = Column(Numeric(12, 2), default=0, nullable=False)
    notes = Column(Text, nullable=True)
    received_by = Column(String(100), nullable=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    supplier = relationship("Supplier")
    location = relationship("Location")
    items = relationship("PurchaseReceiptItem", back_populates="receipt", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_purchase_receipt_location_date", "location_id", "received_at"),)


class PurchaseReceiptItem(Base):
    __tablename__ = "purchase_receipt_items"

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("purchase_receipts.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Numeric(12, 2), default=0, nullable=False)
    imeis_json = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    receipt = relationship("PurchaseReceipt", back_populates="items")
    product = relationship("Product")


class PhysicalInventoryCount(Base):
    """Conteo físico de inventario por ubicación."""

    __tablename__ = "physical_inventory_counts"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False, index=True)
    status = Column(String(30), default="draft", nullable=False, index=True)
    notes = Column(Text, nullable=True)
    counted_by = Column(String(100), nullable=True)
    approved_by = Column(String(100), nullable=True)
    counted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    location = relationship("Location")
    items = relationship("PhysicalInventoryCountItem", back_populates="count", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_inventory_count_location_status", "location_id", "status"),)


class PhysicalInventoryCountItem(Base):
    __tablename__ = "physical_inventory_count_items"

    id = Column(Integer, primary_key=True, index=True)
    count_id = Column(Integer, ForeignKey("physical_inventory_counts.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    expected_quantity = Column(Integer, nullable=False)
    counted_quantity = Column(Integer, nullable=False)
    difference = Column(Integer, nullable=False)
    imeis_json = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    count = relationship("PhysicalInventoryCount", back_populates="items")
    product = relationship("Product")


class LocationDailyClose(Base):
    """Corte/cierre operativo por tienda."""

    __tablename__ = "location_daily_closes"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False, index=True)
    close_date = Column(DateTime(timezone=True), nullable=False, index=True)
    close_day = Column(Date, nullable=False, index=True)
    cash_expected = Column(Numeric(12, 2), default=0, nullable=False)
    transfer_expected = Column(Numeric(12, 2), default=0, nullable=False)
    card_expected = Column(Numeric(12, 2), default=0, nullable=False)
    financing_expected = Column(Numeric(12, 2), default=0, nullable=False)
    cash_counted = Column(Numeric(12, 2), default=0, nullable=False)
    transfer_total = Column(Numeric(12, 2), default=0, nullable=False)
    card_total = Column(Numeric(12, 2), default=0, nullable=False)
    financing_total = Column(Numeric(12, 2), default=0, nullable=False)
    difference = Column(Numeric(12, 2), default=0, nullable=False)
    status = Column(String(30), default="closed", nullable=False, index=True)
    notes = Column(Text, nullable=True)
    closed_by = Column(String(100), nullable=True)
    approved_by = Column(String(100), nullable=True)
    closed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    location = relationship("Location")

    __table_args__ = (
        Index("idx_location_daily_close_location_date", "location_id", "close_date"),
        UniqueConstraint("location_id", "close_day", name="uq_location_daily_close_location_day"),
    )


__all__ = [
    "UserLocationAccess",
    "AuditLog",
    "PurchaseReceipt",
    "PurchaseReceiptItem",
    "PhysicalInventoryCount",
    "PhysicalInventoryCountItem",
    "LocationDailyClose",
]