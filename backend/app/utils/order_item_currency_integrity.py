"""Transaction-boundary currency normalization for historical order-item cost.

Every new OrderItem stores historical cost in HNL so reports never compare an HNL
sale price against a raw USD product cost. The guard protects normal API writes,
order edits and future ORM callers alike.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.utils.order_currency import product_amount_in_hnl, resolve_exchange_rate


_INSTALLED = False


def _normalize_new_order_item_cost(session: Session, item: Any) -> None:
    from app.models import Order, Product, SalesProfile

    product = getattr(item, "product", None)
    if product is None and getattr(item, "product_id", None) is not None:
        with session.no_autoflush:
            product = session.get(Product, int(item.product_id))
    if product is None:
        return

    order = getattr(item, "order", None)
    if order is None and getattr(item, "order_id", None) is not None:
        with session.no_autoflush:
            order = session.get(Order, int(item.order_id))

    sales_profile = None
    if order is not None and getattr(order, "sales_profile_id", None) is not None:
        with session.no_autoflush:
            sales_profile = session.get(SalesProfile, int(order.sales_profile_id))

    exchange_rate = resolve_exchange_rate(sales_profile)
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
