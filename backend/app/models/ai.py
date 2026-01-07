from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Customer(Base):
    """Cliente enriquecido para CRM y seguridad."""

    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    is_troll = Column(Boolean, default=False, index=True)
    is_blocked = Column(Boolean, default=False, index=True)
    reputation_score = Column(Integer, default=100)
    daily_message_count = Column(Integer, default=0)
    last_interaction_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    interactions = relationship("InteractionLog", back_populates="customer", cascade="all, delete-orphan")


class AIProfileConfig(Base):
    """Configuración de cada bot de IA."""

    __tablename__ = "ai_profile_configs"

    id = Column(Integer, primary_key=True, index=True)
    sales_profile_id = Column(Integer, ForeignKey("sales_profiles.id", ondelete="CASCADE"), unique=True, nullable=False)
    model_name = Column(String, default="gpt-4o")
    temperature = Column(Numeric(3, 2), default=0.7)
    system_prompt = Column(Text, nullable=False)
    initial_greeting = Column(Text, nullable=True)
    voice_tone = Column(String, nullable=True)
    context_rules = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    business_description = Column(Text, nullable=True)
    sales_goal = Column(String, nullable=True)
    negotiation_style = Column(String, nullable=True)
    max_discount_rate = Column(Numeric(5, 4), default=0.0)
    fallback_human_trigger = Column(String, nullable=True)
    admin_notification_phone = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sales_profile = relationship("SalesProfile", backref="ai_config")


class InteractionLog(Base):
    """Historial de conversaciones entre clientes y bots."""

    __tablename__ = "interaction_logs"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    sales_profile_id = Column(Integer, ForeignKey("sales_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, default=0)
    converted_order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    customer = relationship("Customer", back_populates="interactions")
    sales_profile = relationship("SalesProfile")
    converted_order = relationship("Order")


class TrainingQueue(Base):
    """Preguntas que requieren intervención humana para entrenar la IA."""

    __tablename__ = "training_queue"

    id = Column(Integer, primary_key=True, index=True)
    sales_profile_id = Column(Integer, ForeignKey("sales_profiles.id", ondelete="SET NULL"), nullable=True)
    customer_question = Column(Text, nullable=False)
    ai_proposed_answer = Column(Text, nullable=True)
    admin_correction = Column(Text, nullable=True)
    status = Column(String, default="pending", index=True)

    sales_profile = relationship("SalesProfile")


__all__ = ["Customer", "AIProfileConfig", "InteractionLog", "TrainingQueue"]
