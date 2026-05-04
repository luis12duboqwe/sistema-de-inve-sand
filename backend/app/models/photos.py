from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PhotoRequest(Base):
    """
    Solicitud de fotos: cuando el cliente pide fotos que el bot no tiene.
    
    Workflow:
    1. Cliente: "Quiero ver fotos del iPhone 15 en gris"
    2. Bot detecta → Responde: "Dame un momento, estoy tomando fotos..."
    3. Sistema crea PhotoRequest, notifica al agente
    4. Agente: ve dashboard "cliente X pide fotos iPhone 15 gris"
    5. Agente toma/carga fotos → Sistema las envía al cliente
    6. Cliente recibe fotos (cree que del bot)
    7. PhotoRequest marcada como resuelto
    """

    __tablename__ = "photo_requests"

    id = Column(Integer, primary_key=True, index=True)
    
    # Quién solicita
    customer_id = Column(String, nullable=False, index=True)  # Teléfono o ID del cliente
    sales_profile_id = Column(Integer, ForeignKey("sales_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Qué solicita
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)
    product_name = Column(String, nullable=False)  # Backup si producto se elimina
    color_requested = Column(String, nullable=True)  # "gris", "negro", "azul", etc.
    size_requested = Column(String, nullable=True)  # "128GB", "256GB", etc.
    additional_notes = Column(Text, nullable=True)  # "También quiero ver desde diferentes ángulos"
    customer_name = Column(String, nullable=True)
    origin_channel = Column(String, nullable=True, index=True)
    
    # Asignación
    assigned_to_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)
    notification_count = Column(Integer, default=0, nullable=False)
    
    # Estado
    status = Column(String, default="pending", index=True)  # pending, claimed, in_progress, awaiting_upload, completed, failed, declined
    completion_notes = Column(Text, nullable=True)  # Por qué falló, qué hizo, etc.
    
    # Fotos entregadas
    photo_urls = Column(JSON, nullable=True)  # ["https://...", "https://..."] (URLs de fotos enviadas)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    first_assigned_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    product = relationship("Product", backref="photo_requests")
    sales_profile = relationship("SalesProfile", backref="photo_requests")
    assigned_to_user = relationship("User", backref="assigned_photo_requests")

    __table_args__ = (
        Index("idx_photo_request_customer_status", "customer_id", "status"),
        Index("idx_photo_request_product_status", "product_id", "status"),
        Index("idx_photo_request_assigned_status", "assigned_to_user_id", "status"),
    )


class PhotoRequestMediaItem(Base):
    """
    Cada foto/video cargado para una solicitud.
    Permite múltiples archivos por solicitud.
    """

    __tablename__ = "photo_request_media"

    id = Column(Integer, primary_key=True, index=True)
    photo_request_id = Column(Integer, ForeignKey("photo_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Archivo
    media_url = Column(String, nullable=False)  # URL pública o S3
    media_type = Column(String, nullable=False)  # "photo", "video", "360_view"
    file_size_bytes = Column(Integer, nullable=True)
    media_metadata = Column("metadata", JSON, nullable=True)  # {width, height, camera_angle, etc}
    
    # Contexto
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Tracking
    sent_to_customer_at = Column(DateTime(timezone=True), nullable=True)
    customer_viewed = Column(Boolean, default=False, nullable=False)
    customer_viewed_at = Column(DateTime(timezone=True), nullable=True)
    
    relationships = relationship("User", foreign_keys=[uploaded_by_user_id])

    __table_args__ = (
        Index("idx_photo_request_media_request", "photo_request_id"),
        Index("idx_photo_request_media_sent", "photo_request_id", "sent_to_customer_at"),
    )


__all__ = ["PhotoRequest", "PhotoRequestMediaItem"]
