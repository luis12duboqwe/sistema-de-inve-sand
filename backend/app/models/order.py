from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Order(Base):
    """Órdenes de venta multi-ubicación."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    sales_profile_id = Column(Integer, ForeignKey("sales_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    source_location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False, index=True)
    canal = Column(String, nullable=False, index=True)
    metodo_pago = Column(String, nullable=False)
    payment_breakdown = Column(Text, nullable=True)
    transfer_bank_name = Column(String(120), nullable=True, index=True)
    transfer_reference = Column(String(120), nullable=True)
    transfer_reference_normalized = Column(String(120), nullable=True, index=True)
    total = Column(Numeric(10, 2), nullable=False)
    financing_details = Column(Text, nullable=True)
    estado = Column(String, default="pendiente", nullable=False, index=True)
    notes = Column(Text, nullable=True)
    delivery_date = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    # Validación de cierre de día (admin)
    validada_at = Column(DateTime(timezone=True), nullable=True, index=True)
    validated_by = Column(String(100), nullable=True)

    sales_profile = relationship("SalesProfile", back_populates="orders")
    source_location = relationship("Location", back_populates="orders")
    profile = relationship("Profile", foreign_keys=[profile_id], back_populates="orders_legacy")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    trade_ins = relationship("TradeIn", back_populates="order", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_order_sales_profile_estado", "sales_profile_id", "estado"),
        Index("idx_order_source_location", "source_location_id"),
        Index("idx_order_delivery_date", "delivery_date"),
        Index(
            "uq_orders_transfer_reference_normalized_not_null",
            "transfer_reference_normalized",
            unique=True,
            postgresql_where=transfer_reference_normalized.isnot(None),
            sqlite_where=transfer_reference_normalized.isnot(None),
        ),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    costo_unitario = Column(Numeric(10, 2), nullable=True, default=0)
    es_regalo_promocion = Column(Boolean, default=False, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class StockTransfer(Base):
    """Transferencias de stock entre ubicaciones físicas."""

    __tablename__ = "stock_transfers"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    from_location_id = Column(Integer, ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False, index=True)
    to_location_id = Column(Integer, ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False, index=True)
    from_profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="RESTRICT"), nullable=True, index=True)
    to_profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="RESTRICT"), nullable=True, index=True)
    cantidad = Column(Integer, nullable=False)
    notas = Column(Text, nullable=True)
    estado = Column(String(20), default="pendiente", nullable=False, index=True)
    received_quantity = Column(Integer, nullable=True)
    missing_quantity = Column(Integer, nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    confirmed_by = Column(String(100), nullable=True)
    incident_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    created_by = Column(String(100), nullable=True)

    product = relationship("Product", foreign_keys=[product_id])
    from_location = relationship("Location", foreign_keys=[from_location_id])
    to_location = relationship("Location", foreign_keys=[to_location_id])
    from_profile = relationship("Profile", foreign_keys=[from_profile_id])
    to_profile = relationship("Profile", foreign_keys=[to_profile_id])

    __table_args__ = (
        Index("idx_transfer_product", "product_id"),
        Index("idx_transfer_from_location", "from_location_id"),
        Index("idx_transfer_to_location", "to_location_id"),
        Index("idx_transfer_created", "created_at"),
        Index("idx_transfer_estado", "estado"),
    )


class TradeIn(Base):
    """Equipos recibidos como parte de pago (trade-in)."""

    __tablename__ = "trade_ins"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    marca = Column(String, nullable=False)
    modelo = Column(String, nullable=False)
    color = Column(String, nullable=True)
    capacidad = Column(String, nullable=True)
    imei = Column(String, nullable=True)
    condicion = Column(String, nullable=False)
    valor_estimado = Column(Numeric(10, 2), nullable=False)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order = relationship("Order", back_populates="trade_ins")


class Return(Base):
    """Registro de devoluciones y garantías (RMA)."""

    __tablename__ = "returns"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reason = Column(String, nullable=True)
    status = Column(String, default="completed", nullable=False)
    created_by = Column(String, nullable=True)

    order = relationship("Order", backref="returns")
    items = relationship("ReturnItem", back_populates="return_obj", cascade="all, delete-orphan")


class ReturnItem(Base):
    """Items dentro de una devolución."""

    __tablename__ = "return_items"

    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(Integer, ForeignKey("returns.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    condition = Column(String, nullable=False)
    action = Column(String, nullable=False)
    imei = Column(String, nullable=True)                # IMEI del equipo defectuoso que regresa (entra al inventario)
    replacement_imei = Column(String, nullable=True)    # IMEI del equipo de reemplazo que sale (garantía)

    return_obj = relationship("Return", back_populates="items")
    product = relationship("Product")


class TradeInPolicy(Base):
    """Políticas configurables para evaluar retomas."""

    __tablename__ = "trade_in_policies"

    id = Column(Integer, primary_key=True, index=True)
    rule_type = Column(String, default="model_rejection")
    pattern = Column(String, nullable=False)
    action = Column(String, default="reject")
    reason = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


__all__ = [
    "Order",
    "OrderItem",
    "StockTransfer",
    "TradeIn",
    "Return",
    "ReturnItem",
    "TradeInPolicy",
]
