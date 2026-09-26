"""Política de precios y descuentos aplicada por el backend.

La API es la fuente de verdad: nunca se confía en ``precio_unitario`` enviado
por el cliente sin compararlo contra el precio de catálogo del producto.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional, Sequence

from fastapi import HTTPException

from app.models import User

CENT = Decimal("0.01")
AUTOMATIC_DISCOUNT = Decimal("0.02")
NO_GIFTS_DISCOUNT = Decimal("0.03")
OWNER_APPROVED_DISCOUNT = Decimal("0.04")


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def _minimum_price(base_price: Decimal, discount: Decimal) -> Decimal:
    return (base_price * (Decimal("1.00") - discount)).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


def _is_owner_approval(current_user: Optional[User]) -> bool:
    """El Super Admin representa la aprobación explícita del propietario."""

    return bool(current_user and getattr(current_user, "is_superuser", False))


def enforce_sale_price_policy(
    items: Sequence[Any],
    *,
    current_user: Optional[User],
) -> None:
    """Valida precios de venta contra la escalera comercial de Softmobile.

    Reglas:
    - precio de catálogo como techo; no se permiten recargos manuales;
    - hasta 2% de descuento es automático, incluso con regalos/promociones;
    - hasta 3% solo cuando la orden no incluye regalos/promociones;
    - hasta 4% solo sin regalos/promociones y con aprobación del propietario,
      representada por una sesión Super Admin;
    - más de 4% nunca se acepta desde el POS normal.

    Los ítems marcados como regalo/promoción no aportan al total de la orden y
    se excluyen del cálculo de descuento, aunque su presencia limita la rebaja
    de los productos cobrados al tramo automático del 2%.
    """

    has_gifts = any(bool(getattr(item, "es_regalo_promocion", False)) for item in items)
    owner_approved = _is_owner_approval(current_user)

    for item in items:
        if bool(getattr(item, "es_regalo_promocion", False)):
            continue

        product = getattr(item, "product", None)
        if product is None:
            raise HTTPException(
                status_code=400,
                detail="No se pudo validar el precio: el producto no está disponible",
            )

        base_price = _money(getattr(product, "precio", 0))
        sale_price = _money(getattr(item, "precio_unitario", 0))
        product_label = str(getattr(product, "nombre", None) or getattr(product, "sku", None) or "producto")

        if base_price < Decimal("0.00"):
            raise HTTPException(
                status_code=400,
                detail=f"Precio de catálogo inválido para {product_label}",
            )

        if sale_price > base_price:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"El precio de {product_label} no puede superar el precio de catálogo "
                    f"({base_price:.2f}) desde una orden. Actualice el precio del producto primero."
                ),
            )

        if base_price == Decimal("0.00"):
            if sale_price != Decimal("0.00"):
                raise HTTPException(
                    status_code=400,
                    detail=f"El producto {product_label} tiene precio de catálogo 0.00",
                )
            continue

        automatic_floor = _minimum_price(base_price, AUTOMATIC_DISCOUNT)
        if sale_price >= automatic_floor:
            continue

        no_gifts_floor = _minimum_price(base_price, NO_GIFTS_DISCOUNT)
        if not has_gifts and sale_price >= no_gifts_floor:
            continue

        owner_floor = _minimum_price(base_price, OWNER_APPROVED_DISCOUNT)
        if not has_gifts and owner_approved and sale_price >= owner_floor:
            continue

        if sale_price < owner_floor:
            detail = (
                f"El descuento de {product_label} supera el máximo permitido del 4%. "
                f"Precio mínimo: {owner_floor:.2f}."
            )
        elif has_gifts:
            detail = (
                f"Con regalos/promociones, {product_label} solo admite hasta 2% de descuento. "
                f"Precio mínimo: {automatic_floor:.2f}."
            )
        else:
            detail = (
                f"El descuento de {product_label} supera el 3% y requiere aprobación del propietario. "
                "La venta debe confirmarse desde una sesión Super Admin."
            )

        raise HTTPException(status_code=403, detail=detail)


__all__ = [
    "AUTOMATIC_DISCOUNT",
    "NO_GIFTS_DISCOUNT",
    "OWNER_APPROVED_DISCOUNT",
    "enforce_sale_price_policy",
]
