"""Transaction-boundary currency normalization for historical order-item cost.

Every new USD-backed OrderItem stores historical cost in HNL so reports never
compare an HNL sale price against a raw USD product cost. During order edits,
retained quantities can register their already-persisted historical HNL cost in
``Session.info`` so rebuilding rows does not revalue old margins at today's rate.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.utils.order_currency import (
    is_usd_currency,
    product_amount_in_hnl,
    resolve_exchange_rate,
)


_INSTALLED = False
_COST_OVERRIDE_KEY = "order_item_historical_cost_overrides"


def install_order_item_cost_overrides(
    session: Session,
    *,
    order_id: int,
    items: Sequence[dict[str, Any]],
) -> None:
    """Queue retained historical costs for the rows an edit will recreate."""

    overrides: dict[tuple[int, int], list[Any]] = {}
    for item in items:
        key = (int(order_id), int(item["product_id"]))
        overrides.setdefault(key, []).append(item.get("_historical_cost_hnl"))
    session.info[_COST_OVERRIDE_KEY] = overrides


def clear_order_item_cost_overrides(session: Session) -> None:
    session.info.pop(_COST_OVERRIDE_KEY, None)


def _consume_historical_cost_override(
    session: Session,
    *,
    order_id: int,
    product_id: int,
) -> tuple[bool, Any]:
    overrides = session.info.get(_COST_OVERRIDE_KEY)
    if not isinstance(overrides, dict):
        return False, None

    key = (int(order_id), int(product_id))
    queue = overrides.get(key)
    if not queue:
        return False, None

    value = queue.pop(0)
    if not queue:
        overrides.pop(key, None)
    return True, value


def _normalize_new_order_item_cost(session: Session, item: Any) -> None:
    from app.models import Order, Product, Profile, SalesProfile

    product = getattr(item, "product", None)
    if product is None and getattr(item, "product_id", None) is not None:
        with session.no_autoflush:
            product = session.get(Product, int(item.product_id))
    if product is None:
        return

    order_id = int(getattr(item, "order_id", 0) or 0)
    product_id = int(getattr(item, "product_id", 0) or 0)
    has_override, historical_cost = _consume_historical_cost_override(
        session,
        order_id=order_id,
        product_id=product_id,
    )
    if has_override and historical_cost is not None:
        item.costo_unitario = Decimal(str(historical_cost))
        return

    # Historical/manual HNL imports can explicitly provide a cost different from
    # the current product cost. Preserve it. USD rows without an edit-time
    # historical override must be normalized because raw USD is not comparable HNL.
    if (
        not is_usd_currency(getattr(product, "moneda", None))
        and getattr(item, "costo_unitario", None) is not None
    ):
        return

    order = getattr(item, "order", None)
    if order is None and order_id:
        with session.no_autoflush:
            order = session.get(Order, order_id)

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


__all__ = [
    "clear_order_item_cost_overrides",
    "install_order_item_cost_overrides",
    "install_order_item_currency_guards",
]
