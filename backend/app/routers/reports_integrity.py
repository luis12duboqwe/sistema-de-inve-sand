"""Canonical financial reports based on finalization time and net refunds."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.auth import check_permission
from app.database import get_db
from app.models import Location, Order, OrderItem, Product, Return, ReturnItem, Stock, User
from app.schemas import DashboardStats, SalesReport, TopProduct
from app.utils.location_access import get_accessible_location_ids, require_location_access
from app.utils.order_integrity import effective_sale_at, effective_sale_column
from app.utils.order_queries import resolve_sales_profile_for_query
from app.utils.order_validators import validate_location_exists


router = APIRouter(prefix="/api/reports", tags=["reports"])
FINAL_SALE_STATUSES = ["completada", "validada"]


def _scope_stock(query, accessible_location_ids: Optional[list[int]]):
    if accessible_location_ids is not None:
        query = query.filter(Stock.location_id.in_(accessible_location_ids))
    return query


def _sale_item_basis_subquery(db: Session):
    """One paid financial basis row per order/product.

    A historical order may contain multiple OrderItem rows for the same product.
    Refunds only identify order + product, not a specific sale line, so joining a
    ReturnItem directly to OrderItem would multiply the refund. Consolidating the
    paid lines first lets us allocate returned units against the actual weighted
    historical revenue/cost without inventing a line-level choice.
    """
    return (
        db.query(
            OrderItem.order_id.label("order_id"),
            OrderItem.product_id.label("product_id"),
            func.sum(OrderItem.cantidad).label("sold_quantity"),
            func.sum(OrderItem.cantidad * OrderItem.precio_unitario).label("sold_revenue"),
            func.sum(
                OrderItem.cantidad * func.coalesce(OrderItem.costo_unitario, 0)
            ).label("sold_cost"),
        )
        .filter(OrderItem.es_regalo_promocion == False)  # noqa: E712
        .group_by(OrderItem.order_id, OrderItem.product_id)
        .subquery()
    )


def _refund_allocations(
    db: Session,
    start_dt: datetime | None,
    end_dt: datetime | None,
    *,
    sales_profile_id: int | None = None,
    location_ids: list[int] | None = None,
    product_id: int | None = None,
) -> list[dict[str, Any]]:
    """Return one accounting allocation per ReturnItem, never per sale line."""
    basis = _sale_item_basis_subquery(db)
    query = (
        db.query(
            ReturnItem,
            Order,
            Product,
            basis.c.sold_quantity,
            basis.c.sold_revenue,
            basis.c.sold_cost,
        )
        .join(Return, Return.id == ReturnItem.return_id)
        .join(Order, Order.id == Return.order_id)
        .join(
            basis,
            (basis.c.order_id == Order.id)
            & (basis.c.product_id == ReturnItem.product_id),
        )
        .join(Product, Product.id == ReturnItem.product_id)
        .filter(ReturnItem.action == "refund")
    )
    if start_dt is not None:
        query = query.filter(Return.created_at >= start_dt)
    if end_dt is not None:
        query = query.filter(Return.created_at <= end_dt)
    if sales_profile_id is not None:
        query = query.filter(Order.sales_profile_id == sales_profile_id)
    if location_ids is not None:
        query = query.filter(Order.source_location_id.in_(location_ids))
    if product_id is not None:
        query = query.filter(ReturnItem.product_id == product_id)

    allocations: list[dict[str, Any]] = []
    for returned, order, product, sold_quantity, sold_revenue, sold_cost in query.all():
        basis_quantity = int(sold_quantity or 0)
        returned_quantity = int(returned.quantity or 0)
        if basis_quantity <= 0 or returned_quantity <= 0:
            continue

        unit_revenue = Decimal(sold_revenue or 0) / basis_quantity
        unit_cost = Decimal(sold_cost or 0) / basis_quantity
        allocations.append(
            {
                "return_item_id": returned.id,
                "order_id": order.id,
                "product_id": returned.product_id,
                "product_name": product.nombre,
                "product_category": product.categoria,
                "location_id": order.source_location_id,
                "quantity": returned_quantity,
                "revenue": unit_revenue * returned_quantity,
                "cost": unit_cost * returned_quantity,
            }
        )
    return allocations


def _refund_totals(
    db: Session,
    start_dt: datetime,
    end_dt: datetime,
    *,
    sales_profile_id: int | None = None,
    location_ids: list[int] | None = None,
    product_id: int | None = None,
) -> tuple[Decimal, Decimal, int]:
    """Return (refunded revenue, reversed historical cost, refunded units)."""
    revenue = Decimal("0.00")
    cost = Decimal("0.00")
    units = 0
    for allocation in _refund_allocations(
        db,
        start_dt,
        end_dt,
        sales_profile_id=sales_profile_id,
        location_ids=location_ids,
        product_id=product_id,
    ):
        revenue += Decimal(allocation["revenue"])
        cost += Decimal(allocation["cost"])
        units += int(allocation["quantity"])
    return revenue, cost, units


def _scoped_sales_query(
    db: Session,
    *,
    start_dt: datetime | None = None,
    end_dt: datetime | None = None,
    location_ids: list[int] | None = None,
    sales_profile_id: int | None = None,
):
    sale_at = effective_sale_column(Order)
    query = db.query(Order).filter(Order.estado.in_(FINAL_SALE_STATUSES))
    if start_dt is not None:
        query = query.filter(sale_at >= start_dt)
    if end_dt is not None:
        query = query.filter(sale_at <= end_dt)
    if location_ids is not None:
        query = query.filter(Order.source_location_id.in_(location_ids))
    if sales_profile_id is not None:
        query = query.filter(Order.sales_profile_id == sales_profile_id)
    return query


def _resolve_report_scope(
    db: Session,
    current_user: User,
    location_id: int | None,
) -> tuple[list[int] | None, int | None]:
    accessible = get_accessible_location_ids(db, current_user, "can_view")
    if location_id is not None:
        location = validate_location_exists(db, location_id)
        require_location_access(db, current_user, location.id, "can_view")
        return [location.id], location.id
    return accessible, None


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats_integrity(
    sales_profile_slug: Optional[str] = Query(None),
    location_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view")),
):
    location_ids, _ = _resolve_report_scope(db, current_user, location_id)
    sales_profile = resolve_sales_profile_for_query(db, sales_profile_slug, require_active=True)
    sales_profile_id = sales_profile.id if sales_profile else None

    product_query = db.query(Product)
    if location_ids is not None:
        product_query = (
            product_query.join(Stock, Stock.product_id == Product.id)
            .filter(Stock.location_id.in_(location_ids))
            .distinct()
        )
    active_products = product_query.filter(Product.activo == True).count()  # noqa: E712
    total_products = product_query.count()

    stock_query = db.query(Stock).join(Product).filter(Product.activo == True)  # noqa: E712
    stock_query = _scope_stock(stock_query, location_ids)
    unit_value = func.coalesce(func.nullif(Product.costo, 0), Product.precio)
    stock_stats = stock_query.with_entities(
        func.sum(case((Stock.cantidad_disponible == 0, 1), else_=0)).label("out_of_stock"),
        func.sum(
            case(
                (((Stock.cantidad_disponible > 0) & (Stock.cantidad_disponible < 10)), 1),
                else_=0,
            )
        ).label("low_stock"),
        func.sum(Stock.cantidad_disponible * unit_value).label("inventory_value"),
    ).first()

    low_stock_count = int((stock_stats.low_stock if stock_stats else 0) or 0)
    out_of_stock_count = int((stock_stats.out_of_stock if stock_stats else 0) or 0)
    total_inventory_value = Decimal((stock_stats.inventory_value if stock_stats else 0) or 0)

    pending_query = db.query(Order).filter(Order.estado == "pendiente")
    if location_ids is not None:
        pending_query = pending_query.filter(Order.source_location_id.in_(location_ids))
    if sales_profile_id is not None:
        pending_query = pending_query.filter(Order.sales_profile_id == sales_profile_id)
    pending_orders = pending_query.count()

    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    month_start_date = today.replace(day=1)
    month_start = datetime.combine(month_start_date, datetime.min.time())

    today_orders = _scoped_sales_query(
        db,
        start_dt=today_start,
        end_dt=today_end,
        location_ids=location_ids,
        sales_profile_id=sales_profile_id,
    ).all()
    gross_today = sum((Decimal(order.total or 0) for order in today_orders), Decimal("0.00"))
    refunds_today, _, _ = _refund_totals(
        db,
        today_start,
        today_end,
        sales_profile_id=sales_profile_id,
        location_ids=location_ids,
    )
    net_today = gross_today - refunds_today

    month_orders = _scoped_sales_query(
        db,
        start_dt=month_start,
        end_dt=today_end,
        location_ids=location_ids,
        sales_profile_id=sales_profile_id,
    ).all()
    gross_month = sum((Decimal(order.total or 0) for order in month_orders), Decimal("0.00"))
    refunds_month, refund_cost_month, _ = _refund_totals(
        db,
        month_start,
        today_end,
        sales_profile_id=sales_profile_id,
        location_ids=location_ids,
    )
    net_month = gross_month - refunds_month

    historical_cost = Decimal("0.00")
    if month_orders:
        month_order_ids = [order.id for order in month_orders]
        for item in db.query(OrderItem).filter(OrderItem.order_id.in_(month_order_ids)).all():
            historical_cost += Decimal(item.costo_unitario or 0) * int(item.cantidad or 0)
    net_cost_month = max(Decimal("0.00"), historical_cost - refund_cost_month)

    if month_start_date.month == 1:
        previous_month_date = month_start_date.replace(year=month_start_date.year - 1, month=12)
    else:
        previous_month_date = month_start_date.replace(month=month_start_date.month - 1)
    previous_start = datetime.combine(previous_month_date, datetime.min.time())
    previous_end = datetime.combine(month_start_date - timedelta(days=1), datetime.max.time())
    previous_orders = _scoped_sales_query(
        db,
        start_dt=previous_start,
        end_dt=previous_end,
        location_ids=location_ids,
        sales_profile_id=sales_profile_id,
    ).all()
    gross_previous = sum((Decimal(order.total or 0) for order in previous_orders), Decimal("0.00"))
    refunds_previous, _, _ = _refund_totals(
        db,
        previous_start,
        previous_end,
        sales_profile_id=sales_profile_id,
        location_ids=location_ids,
    )
    net_previous = gross_previous - refunds_previous

    margin = Decimal("0.00")
    if net_month > 0:
        margin = ((net_month - net_cost_month) / net_month) * Decimal("100")
    average_ticket = net_month / len(month_orders) if month_orders else Decimal("0.00")

    return DashboardStats(
        active_products=active_products,
        total_products=total_products,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count,
        total_inventory_value=total_inventory_value,
        pending_orders=pending_orders,
        total_orders_today=len(today_orders),
        total_revenue_today=net_today,
        total_revenue_month=net_month,
        total_revenue_last_month=net_previous,
        gross_margin_month=round(margin, 2),
        average_ticket_month=round(average_ticket, 2),
    )


@router.get("/sales", response_model=SalesReport)
def get_sales_report_integrity(
    sales_profile_slug: Optional[str] = Query(None),
    location_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    top_limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view")),
):
    if date_to is None:
        date_to = datetime.now().date()
    if date_from is None:
        date_from = date_to - timedelta(days=30)
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    location_ids, _ = _resolve_report_scope(db, current_user, location_id)
    sales_profile = resolve_sales_profile_for_query(db, sales_profile_slug)
    sales_profile_id = sales_profile.id if sales_profile else None

    orders = _scoped_sales_query(
        db,
        start_dt=start_dt,
        end_dt=end_dt,
        location_ids=location_ids,
        sales_profile_id=sales_profile_id,
    ).all()
    gross_revenue = sum((Decimal(order.total or 0) for order in orders), Decimal("0.00"))
    refunded_revenue, _, _ = _refund_totals(
        db,
        start_dt,
        end_dt,
        sales_profile_id=sales_profile_id,
        location_ids=location_ids,
    )
    net_revenue = gross_revenue - refunded_revenue
    total_orders = len(orders)

    product_stats: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"name": "", "units": 0, "revenue": Decimal("0.00")}
    )
    if orders:
        order_ids = [order.id for order in orders]
        for item in db.query(OrderItem).filter(OrderItem.order_id.in_(order_ids)).all():
            if item.es_regalo_promocion:
                continue
            product = item.product
            entry = product_stats[item.product_id]
            entry["name"] = product.nombre if product else f"Producto #{item.product_id}"
            entry["units"] += int(item.cantidad or 0)
            entry["revenue"] += Decimal(item.precio_unitario or 0) * int(item.cantidad or 0)

    for allocation in _refund_allocations(
        db,
        start_dt,
        end_dt,
        sales_profile_id=sales_profile_id,
        location_ids=location_ids,
    ):
        entry = product_stats[int(allocation["product_id"])]
        entry["name"] = allocation["product_name"]
        entry["units"] -= int(allocation["quantity"])
        entry["revenue"] -= Decimal(allocation["revenue"])

    ranked = sorted(
        product_stats.items(),
        key=lambda pair: pair[1]["revenue"],
        reverse=True,
    )[:top_limit]
    top_products = [
        TopProduct(
            product_id=product_id,
            product_name=data["name"],
            units_sold=int(data["units"]),
            total_revenue=Decimal(data["revenue"]),
        )
        for product_id, data in ranked
    ]

    return SalesReport(
        period_start=date_from,
        period_end=date_to,
        total_orders=total_orders,
        total_revenue=net_revenue,
        average_order_value=net_revenue / total_orders if total_orders else Decimal("0.00"),
        top_products=top_products,
    )


@router.get("/sales-summary-by-location")
def get_sales_summary_by_location_integrity(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view")),
):
    accessible = get_accessible_location_ids(db, current_user, "can_view")
    start_dt = datetime.combine(start_date, datetime.min.time()) if start_date else None
    end_dt = datetime.combine(end_date, datetime.max.time()) if end_date else None
    orders = _scoped_sales_query(
        db,
        start_dt=start_dt,
        end_dt=end_dt,
        location_ids=accessible,
    ).all()

    stats: dict[int, dict[str, Any]] = {}
    for order in orders:
        location_id = int(order.source_location_id or 0)
        if not location_id:
            continue
        location = order.source_location
        entry = stats.setdefault(
            location_id,
            {
                "name": location.nombre if location else f"Ubicación #{location_id}",
                "orders": 0,
                "units": 0,
                "revenue": Decimal("0.00"),
            },
        )
        entry["orders"] += 1
        entry["revenue"] += Decimal(order.total or 0)
        entry["units"] += sum(
            int(item.cantidad or 0)
            for item in order.items
            if not item.es_regalo_promocion
        )

    for allocation in _refund_allocations(
        db,
        start_dt,
        end_dt,
        location_ids=accessible,
    ):
        location_id = int(allocation["location_id"] or 0)
        if not location_id:
            continue
        if location_id not in stats:
            location = db.query(Location).filter(Location.id == location_id).first()
            stats[location_id] = {
                "name": location.nombre if location else f"Ubicación #{location_id}",
                "orders": 0,
                "units": 0,
                "revenue": Decimal("0.00"),
            }
        stats[location_id]["units"] -= int(allocation["quantity"])
        stats[location_id]["revenue"] -= Decimal(allocation["revenue"])

    rows = []
    for location_id, data in stats.items():
        orders_count = int(data["orders"])
        revenue = Decimal(data["revenue"])
        rows.append(
            {
                "location_id": location_id,
                "location_nombre": data["name"],
                "total_ordenes": orders_count,
                "total_unidades_vendidas": int(data["units"]),
                "total_ingresos": float(revenue),
                "ticket_promedio": float(revenue / orders_count) if orders_count else 0.0,
            }
        )
    rows.sort(key=lambda row: row["total_ingresos"], reverse=True)
    return rows


@router.get("/top-products-by-location/{location_id}")
def get_top_products_by_location_integrity(
    location_id: int,
    limit: int = Query(10, ge=1, le=50),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view")),
):
    validate_location_exists(db, location_id)
    require_location_access(db, current_user, location_id, "can_view")
    start_dt = datetime.combine(start_date, datetime.min.time()) if start_date else None
    end_dt = datetime.combine(end_date, datetime.max.time()) if end_date else None
    orders = _scoped_sales_query(
        db,
        start_dt=start_dt,
        end_dt=end_dt,
        location_ids=[location_id],
    ).all()

    stats: dict[int, dict[str, Any]] = defaultdict(
        lambda: {
            "name": "",
            "category": "",
            "units": 0,
            "revenue": Decimal("0.00"),
        }
    )
    if orders:
        order_ids = [order.id for order in orders]
        for item in db.query(OrderItem).filter(OrderItem.order_id.in_(order_ids)).all():
            if item.es_regalo_promocion:
                continue
            product = item.product
            entry = stats[item.product_id]
            entry["name"] = product.nombre if product else f"Producto #{item.product_id}"
            entry["category"] = product.categoria if product else ""
            entry["units"] += int(item.cantidad or 0)
            entry["revenue"] += Decimal(item.precio_unitario or 0) * int(item.cantidad or 0)

    for allocation in _refund_allocations(
        db,
        start_dt,
        end_dt,
        location_ids=[location_id],
    ):
        product_id = int(allocation["product_id"])
        entry = stats[product_id]
        entry["name"] = allocation["product_name"]
        entry["category"] = allocation["product_category"]
        entry["units"] -= int(allocation["quantity"])
        entry["revenue"] -= Decimal(allocation["revenue"])

    ranked = sorted(
        stats.items(),
        key=lambda pair: (pair[1]["units"], pair[1]["revenue"]),
        reverse=True,
    )[:limit]
    return [
        {
            "product_id": product_id,
            "product_nombre": data["name"],
            "product_categoria": data["category"],
            "cantidad_vendida": int(data["units"]),
            "ingresos_totales": float(data["revenue"]),
        }
        for product_id, data in ranked
    ]


def _transfer_components(order: Order) -> list[dict[str, Any]]:
    if order.payment_breakdown:
        try:
            parsed = json.loads(order.payment_breakdown)
        except (TypeError, json.JSONDecodeError):
            parsed = []
        if isinstance(parsed, list):
            components = [
                item
                for item in parsed
                if isinstance(item, dict) and item.get("method") == "transferencia"
            ]
            if components:
                return components
    if order.metodo_pago == "transferencia":
        return [
            {
                "method": "transferencia",
                "amount": str(order.total or 0),
                "bank_name": order.transfer_bank_name,
                "reference": order.transfer_reference,
            }
        ]
    return []


@router.get("/bank-transfer-reconciliation")
def get_bank_transfer_reconciliation_integrity(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    location_id: Optional[int] = Query(None),
    bank_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view")),
):
    location_ids, _ = _resolve_report_scope(db, current_user, location_id)
    start_dt = datetime.combine(start_date, datetime.min.time()) if start_date else None
    end_dt = datetime.combine(end_date, datetime.max.time()) if end_date else None
    orders = _scoped_sales_query(
        db,
        start_dt=start_dt,
        end_dt=end_dt,
        location_ids=location_ids,
    ).all()

    items: list[dict[str, Any]] = []
    total = Decimal("0.00")
    wanted_bank = bank_name.strip().lower() if bank_name else None
    for order in orders:
        for component in _transfer_components(order):
            component_bank = str(
                component.get("bank_name") or order.transfer_bank_name or ""
            ).strip()
            if wanted_bank and wanted_bank not in component_bank.lower():
                continue
            amount = Decimal(str(component.get("amount") or 0))
            total += amount
            location = order.source_location
            items.append(
                {
                    "order_id": order.id,
                    # Campo histórico conservado para clientes existentes; ahora
                    # representa la fecha efectiva de la venta.
                    "created_at": effective_sale_at(order),
                    "customer_name": order.customer_name,
                    "customer_phone": order.customer_phone,
                    "location_id": order.source_location_id,
                    "location_nombre": location.nombre if location else None,
                    "bank_name": component_bank or None,
                    "reference": component.get("reference") or order.transfer_reference,
                    "total": float(amount),
                    "estado": order.estado,
                    "validated_by": order.validated_by,
                    "validada_at": order.validada_at,
                }
            )

    items.sort(key=lambda item: item["created_at"] or datetime.min, reverse=True)
    return {
        "total_amount": float(total),
        "total_orders": len({item["order_id"] for item in items}),
        "items": items,
    }
