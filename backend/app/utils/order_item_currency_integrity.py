"""Transaction-boundary currency normalization for historical order-item cost.

Every new USD-backed OrderItem stores historical cost in HNL so reports never
compare an HNL sale price against a raw USD product cost. Missing HNL historical
costs are also filled from the product. Explicit HNL historical costs are preserved
for controlled imports/tests.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.utils.order_currency import (
    is_usd_currency,
    product_amount_in_hnl,
    resolve_exchange_rate,
)


_INSTALLED = False


def _normalize_new_order_item_cost(session: Session, item: Any) -> None:
    from app.models import Order, Product, Profile, SalesProfile

    product = getattr(item, "product", None)
    if product is None and getattr(item, "product_id", None) is not None:
        with session.no_autoflush:
            product = session.get(Product, int(item.product_id))
    if product is None:
        return

    # Historical/manual HNL imports can explicitly provide a cost different from
    # the current product cost. Preserve it. USD items, however, must always be
    # normalized because a raw USD number is not comparable with an HNL sale.
    if (
        not is_usd_currency(getattr(product, "moneda", None))
        and getattr(item, "costo_unitario", None) is not None
    ):
        return

    order = getattr(item, "order", None)
    if order is None and getattr(item, "order_id", None) is not None:
        with session.no_autoflush:
            order = session.get(Order, int(item.order_id))

    profile_like = None
    if order is not None and getattr(order, "sales_profile_id", None) is not None:
        with session.no_autoflush:
            profile_like = session.get(SalesProfile, int(order.sales_profile_id))
    elif order is not None and getattr(order, "profile_id", None) is not None:
        with session.no_autoflush:
            profile_like = session.get(Profile, int(order.profile_id))

    exchange_rate = resolve_exchange_rate(profile_like)
    item.costo_unitario = product_amount_in_hnl(
        getattr(product, "costo", 0),
        product,
        exchange_rate,
    )


def _before_flush(session: Session, flush_context: Any, instances: Any) -> None:  # noqa: ARG001
    from app.models import OrderItem

    for candidate in list(session.new):
        if isinstance(candidate, OrderItem):
            _normalize_new_order_item_cost(session, candidate)


def install_order_item_currency_guards() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    event.listen(Session, "before_flush", _before_flush)
    _INSTALLED = True


__all__ = ["install_order_item_currency_guards"]
