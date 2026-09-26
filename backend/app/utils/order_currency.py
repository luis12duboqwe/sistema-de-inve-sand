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


def resolve_exchange_rate(profile_like: Optional[Any]) -> Decimal:
    """Devuelve HNL por USD desde un perfil V2 o legacy.

    V2 guarda ``exchange_rate`` en ``SalesProfile.configuracion``. El perfil
    legacy usaba ``Profile.settings.exchangeRate``. Ambos formatos son aceptados
    para que una orden antigua no cambie de tasa al pasar por el backend canónico.
    Una configuración inválida nunca produce tasa cero/negativa.
    """

    if profile_like is None:
        return DEFAULT_HNL_PER_USD

    raw_config = getattr(profile_like, "configuracion", None)
    if not raw_config:
        raw_config = getattr(profile_like, "settings", None)
    if not raw_config:
        return DEFAULT_HNL_PER_USD

    try:
        config = raw_config if isinstance(raw_config, dict) else json.loads(str(raw_config))
        raw_rate = config.get("exchange_rate", config.get("exchangeRate", DEFAULT_HNL_PER_USD))
        rate = Decimal(str(raw_rate))
        if not rate.is_finite() or rate <= Decimal("0"):
            return DEFAULT_HNL_PER_USD
        return rate.quantize(CENT, rounding=ROUND_HALF_UP)
    except (TypeError, ValueError, json.JSONDecodeError, ArithmeticError, AttributeError):
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
