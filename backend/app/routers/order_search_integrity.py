"""Canonical order-search filters with literal user text and stable pagination."""

from __future__ import annotations

from datetime import datetime
import math
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import check_permission
from app.database import get_db
from app.models import Order, OrderItem, User
from app.routers.orders import _apply_order_location_access, _serialize_order
from app.schemas import OrderResponse, OrderSearchParams, PaginatedResponse
from app.utils.location_access import require_location_access
from app.utils.order_queries import resolve_sales_profile_for_query


router = APIRouter(prefix="/api/orders", tags=["orders"])


def _escape_like_pattern(value: str) -> str:
    """Treat user-provided SQL LIKE wildcard characters as literal text."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.post(
    "/search",
    response_model=PaginatedResponse[OrderResponse],
    dependencies=[Depends(check_permission("orders:view"))],
)
def search_orders_integrity(
    search_params: OrderSearchParams,
    sales_profile_slug: Optional[str] = Query(None, description="Filtrar por canal de venta"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("orders:view")),
):
    """Search orders without treating customer text as SQL syntax."""
    query = _apply_order_location_access(db.query(Order), db, current_user)

    sales_profile = resolve_sales_profile_for_query(
        db,
        sales_profile_slug,
        require_active=True,
    )
    if sales_profile:
        query = query.filter(Order.sales_profile_id == sales_profile.id)

    if search_params.location_id:
        require_location_access(db, current_user, search_params.location_id, "can_view")
        query = query.filter(Order.source_location_id == search_params.location_id)

    if search_params.date_from:
        date_from_dt = datetime.combine(search_params.date_from, datetime.min.time())
        query = query.filter(Order.created_at >= date_from_dt)

    if search_params.date_to:
        date_to_dt = datetime.combine(search_params.date_to, datetime.max.time())
        query = query.filter(Order.created_at <= date_to_dt)

    if search_params.amount_min is not None:
        query = query.filter(Order.total >= search_params.amount_min)

    if search_params.amount_max is not None:
        query = query.filter(Order.total <= search_params.amount_max)

    if search_params.customer_query:
        escaped_customer_query = _escape_like_pattern(search_params.customer_query)
        customer_pattern = f"%{escaped_customer_query}%"
        query = query.filter(
            Order.customer_name.ilike(customer_pattern, escape="\\")
            | Order.customer_phone.ilike(customer_pattern, escape="\\")
        )

    if search_params.estado:
        query = query.filter(Order.estado == search_params.estado.value)

    if search_params.product_id:
        # EXISTS keeps one logical Order row even if legacy data contains the same
        # product in multiple line items. A JOIN would inflate total/pages.
        query = query.filter(
            Order.items.any(OrderItem.product_id == search_params.product_id)
        )

    total = query.count()
    offset = (page - 1) * per_page
    orders = (
        query.order_by(Order.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return PaginatedResponse(
        items=[_serialize_order(order) for order in orders],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0,
    )


__all__ = ["router", "search_orders_integrity"]
