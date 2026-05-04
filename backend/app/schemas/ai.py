"""Schemas especializados para endpoints de inteligencia artificial."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, ConfigDict


class AIContextRequest(BaseModel):
    sales_profile_slug: str
    customer_phone: str
    message_content: str
    customer_name: Optional[str] = None


class AIContextResponse(BaseModel):
    system_prompt: str
    bot_config: Dict[str, Any]
    customer_info: Dict[str, Any]
    relevant_inventory: str
    relevant_faqs: str
    financing_info: str
    previous_context: List[Dict[str, str]]


class InteractionLogCreate(BaseModel):
    sales_profile_slug: str
    customer_phone: str
    role: str
    content: str
    tokens_used: Optional[int] = 0


class TrainingSubmission(BaseModel):
    sales_profile_slug: str
    customer_question: str
    ai_proposed_answer: Optional[str] = None


class TrainingQueueItemResponse(BaseModel):
    id: int
    sales_profile_id: Optional[int] = None
    customer_question: str
    ai_proposed_answer: Optional[str] = None
    admin_correction: Optional[str] = None
    status: str
    created_at: datetime
    sales_profile_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AICustomerResponse(BaseModel):
    id: int
    phone_number: str
    name: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    is_troll: bool
    is_blocked: bool
    reputation_score: int
    daily_message_count: int
    last_interaction_at: Optional[datetime] = None
    conversation_summary: Optional[str] = None
    ai_memory_json: Optional[str] = None
    last_referenced_product_id: Optional[int] = None
    last_referenced_product_name: Optional[str] = None
    last_referenced_color: Optional[str] = None
    last_referenced_variant: Optional[str] = None
    memory_updated_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIConfigSchema(BaseModel):
    sales_profile_id: int
    model_name: str = "gpt-4o"
    temperature: float = 0.7
    system_prompt: str
    initial_greeting: Optional[str] = None
    voice_tone: Optional[str] = None
    context_rules: Optional[str] = None
    is_active: bool = True
    admin_notification_phone: Optional[str] = None
    business_description: Optional[str] = None
    sales_goal: Optional[str] = None
    negotiation_style: Optional[str] = None
    max_discount_rate: Optional[float] = 0.0
    fallback_human_trigger: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AIReplyRequest(AIContextRequest):
    conversation_override: Optional[List[Dict[str, str]]] = None


class AIReplyResponse(BaseModel):
    reply: str
    tokens_used: int
    model: str
    context: AIContextResponse


class LinkOrderRequest(BaseModel):
    customer_phone: str
    order_id: int


class AICreateOrderItemRequest(BaseModel):
    product_id: Optional[int] = None
    product_query: Optional[str] = None
    cantidad: int = 1
    precio_unitario: Optional[float] = None
    imeis: Optional[List[str]] = None


class AICreateOrderRequest(BaseModel):
    sales_profile_slug: str
    source_location_id: int
    customer_phone: str
    customer_name: Optional[str] = None
    canal: Literal["whatsapp", "facebook", "instagram", "tienda"] = "whatsapp"
    metodo_pago: Literal["efectivo", "transferencia", "tarjeta", "financiamiento"] = "efectivo"
    items: List[AICreateOrderItemRequest]
    notes: Optional[str] = None
    auto_link_interaction: bool = True


class AICreateOrderResponse(BaseModel):
    status: Literal["created"]
    order_id: int
    linked_interaction: bool


class AIHandleOrderIntent(BaseModel):
    source_location_id: int
    items: List[AICreateOrderItemRequest]
    canal: Literal["whatsapp", "facebook", "instagram", "tienda"] = "whatsapp"
    metodo_pago: Literal["efectivo", "transferencia", "tarjeta", "financiamiento"] = "efectivo"
    notes: Optional[str] = None
    auto_create: bool = True
    auto_link_interaction: bool = True


class AIHandleMessageRequest(AIReplyRequest):
    message_id: Optional[str] = None
    channel_hint: Optional[str] = None
    order_intent: Optional[AIHandleOrderIntent] = None


class AIHandleMessageResponse(BaseModel):
    reply: str
    tokens_used: int
    model: str
    context: AIContextResponse
    order: Optional[AICreateOrderResponse] = None
