"""Schemas financieros: bancos, financiamiento y políticas de retoma."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


def _empty_financing_option_creates() -> List["FinancingOptionCreate"]:
    """Factory para listas tipadas de opciones de financiamiento (creación)."""
    return []


def _empty_financing_option_responses() -> List["FinancingOptionResponse"]:
    """Factory para listas tipadas de opciones de financiamiento (respuesta)."""
    return []


class FinancingOptionBase(BaseModel):
    """Configuración base para una opción de financiamiento por banco."""

    months: int = Field(..., gt=0, description="Plazo en meses")
    rate: Decimal = Field(..., ge=0, description="Tasa de recargo (ej. 0.05 para 5%)")
    active: bool = True


class FinancingOptionCreate(FinancingOptionBase):
    """Payload de creación para opciones de financiamiento."""

    pass


class FinancingOptionResponse(FinancingOptionBase):
    """Respuesta serializada con el ID y banco asociado."""

    id: int
    bank_id: int

    model_config = ConfigDict(from_attributes=True)


class BankBase(BaseModel):
    """Atributos comunes de un banco configurado."""

    name: str = Field(..., min_length=2, max_length=255)
    active: bool = True
    normal_card_rate: Decimal = Field(
        Decimal("0"),
        ge=0,
        description="Tasa estándar para tarjetas de crédito",
    )


class BankCreate(BankBase):
    """Entrada para crear bancos junto a sus opciones."""

    financing_options: List[FinancingOptionCreate] = Field(default_factory=_empty_financing_option_creates)


class BankUpdate(BaseModel):
    """Actualización parcial de un banco."""

    name: Optional[str] = Field(None, min_length=2, max_length=255)
    active: Optional[bool] = None
    normal_card_rate: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Nueva tasa estándar para tarjetas",
    )


class BankResponse(BankBase):
    """Respuesta completa de banco con las opciones cargadas."""

    id: int
    financing_options: List[FinancingOptionResponse] = Field(default_factory=_empty_financing_option_responses)

    model_config = ConfigDict(from_attributes=True)


class TradeInPolicyBase(BaseModel):
    """Definición de reglas para evaluar retomas de dispositivos."""

    rule_type: Literal[
        "model_rejection",
        "model_acceptance",
        "condition_adjustment",
        "custom_rule",
    ] = "model_rejection"
    pattern: str = Field(..., min_length=1, description="Patrón o criterio a evaluar")
    action: Literal["reject", "accept", "accept_with_conditions"] = "reject"
    reason: Optional[str] = Field(None, max_length=500)
    is_active: bool = True


class TradeInPolicyCreate(TradeInPolicyBase):
    """Payload para crear una política de retoma."""

    pass


class TradeInPolicyUpdate(BaseModel):
    """Actualización parcial para políticas de retoma."""

    rule_type: Optional[str] = None
    pattern: Optional[str] = None
    action: Optional[str] = None
    reason: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class TradeInPolicyResponse(TradeInPolicyBase):
    """Respuesta serializada de una política registrada."""

    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
