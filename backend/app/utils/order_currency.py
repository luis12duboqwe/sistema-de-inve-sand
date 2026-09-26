"""Normalización monetaria para órdenes.

Las órdenes y pagos se contabilizan en HNL. Los productos pueden estar catalogados
en USD, por lo que precio de catálogo y costo deben convertirse a HNL antes de
comparar descuentos, calcular totales o persistir márgenes históricos.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import json
from typing import Any, Optional

CENT = Decimal("0.01")
DEFAULT_HNL_PER_USD = Decimal("25.00")


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def resolve_exchange_rate(sales_profile: Optional[Any]) -> Decimal:
    """Devuelve HNL por USD desde la configuración del perfil de venta.

    Mantiene el fallback histórico de 25 HNL/USD usado por el modo local y el
    contexto de IA. Una configuración inválida nunca produce tasa cero/negativa.
    """

    if sales_profile is None:
        return DEFAULT_HNL_PER_USD

    raw_config = getattr(sales_profile, "configuracion", None)
    if not raw_config:
        return DEFAULT_HNL_PER_USD

    try:
        config = raw_config if isinstance(raw_config, dict) else json.loads(str(raw_config))
        rate = Decimal(str(config.get("exchange_rate", DEFAULT_HNL_PER_USD)))
        if not rate.is_finite() or rate <= Decimal("0"):
            return DEFAULT_HNL_PER_USD
        return rate.quantize(CENT, rounding=ROUND_HALF_UP)
    except (TypeError, ValueError, json.JSONDecodeError, ArithmeticError):
        return DEFAULT_HNL_PER_USD


def is_usd_currency(currency: Any) -> bool:
    value = str(currency or "").strip().upper()
    return value in {"USD", "US$", "$"}


def product_amount_in_hnl(amount: Any, product: Any, exchange_rate: Decimal) -> Decimal:
    normalized = _money(amount)
    if is_usd_currency(getattr(product, "moneda", None)):
        return (normalized * exchange_rate).quantize(CENT, rounding=ROUND_HALF_UP)
    return normalized


__all__ = [
    "DEFAULT_HNL_PER_USD",
    "is_usd_currency",
    "product_amount_in_hnl",
    "resolve_exchange_rate",
]
