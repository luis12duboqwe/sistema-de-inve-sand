from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import case, func
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.database import get_db
from app.models import Product, Order, Stock
from app.schemas import (
    ForecastAnalyticsRequest,
    ForecastingSummary,
    DashboardStats,
)
from app.auth import check_permission, User
from app.services.forecasting_service import generate_sales_forecasts, summarize_forecasts
from app.utils.location_access import get_accessible_location_ids, require_location_access
from app.utils.order_validators import validate_location_exists

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

FINAL_SALE_STATUSES = ["completada", "validada"]


def _scope_orders(query, accessible_location_ids: list[int] | None):
    if accessible_location_ids is not None:
        return query.filter(Order.source_location_id.in_(accessible_location_ids))
    return query


def _scope_stock(query, accessible_location_ids: list[int] | None):
    if accessible_location_ids is not None:
        return query.filter(Stock.location_id.in_(accessible_location_ids))
    return query

@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(
    location_id: int | None = Query(None, description="Filtrar dashboard por ubicación"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
):
    """Obtiene KPIs para el dashboard principal"""
    today = date.today()
    first_day_month = today.replace(day=1)
    last_month_end = first_day_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
    scoped_location_ids = accessible_location_ids
    if location_id is not None:
        location_obj = validate_location_exists(db, location_id)
        require_location_access(db, current_user, location_obj.id, "can_view")
        scoped_location_ids = [location_obj.id]

    # Product stats
    product_query = db.query(Product)
    if scoped_location_ids is not None:
        product_query = product_query.join(Stock, Stock.product_id == Product.id).filter(
            Stock.location_id.in_(scoped_location_ids)
        ).distinct()

    total_products = product_query.count()
    active_products = product_query.filter(Product.activo == True).count()
    
    # Stock stats (sum of all locations)
    # This is complex because stock is in Stock table.
    # We need to aggregate stock per product first.
    
    # Simplified: Count products with total stock < 10
    # Subquery to get total stock per product
    stock_free_expr = Stock.cantidad_disponible - func.coalesce(Stock.cantidad_reservada, 0)
    stock_subquery = db.query(
        Stock.product_id,
        func.sum(case((stock_free_expr > 0, stock_free_expr), else_=0)).label("total_stock")
    )
    stock_subquery = _scope_stock(stock_subquery, scoped_location_ids)
    stock_subquery = stock_subquery.group_by(Stock.product_id).subquery()
    
    low_stock_count = db.query(stock_subquery).filter(stock_subquery.c.total_stock < 10, stock_subquery.c.total_stock > 0).count()
    out_of_stock_count = db.query(stock_subquery).filter(stock_subquery.c.total_stock == 0).count()

    # Inventory Value
    # Cost * Total Stock
    inventory_value = db.query(
        func.sum(func.coalesce(Product.costo, Product.precio) * stock_subquery.c.total_stock)
    ).join(stock_subquery, Product.id == stock_subquery.c.product_id).scalar() or 0

    # Order stats
    pending_orders_query = db.query(Order).filter(Order.estado == 'pendiente')
    pending_orders = _scope_orders(pending_orders_query, scoped_location_ids).count()
    
    today_start = datetime.combine(today, datetime.min.time())
    orders_today_query = db.query(Order).filter(
        Order.created_at >= today_start,
        Order.estado.in_(FINAL_SALE_STATUSES)
    )
    total_orders_today = _scope_orders(orders_today_query, scoped_location_ids).count()
    
    revenue_today_query = db.query(func.sum(Order.total)).filter(
        Order.created_at >= today_start,
        Order.estado.in_(FINAL_SALE_STATUSES)
    )
    total_revenue_today = _scope_orders(revenue_today_query, scoped_location_ids).scalar() or 0

    revenue_month_query = db.query(func.sum(Order.total)).filter(
        Order.created_at >= first_day_month,
        Order.estado.in_(FINAL_SALE_STATUSES)
    )
    total_revenue_month = _scope_orders(revenue_month_query, scoped_location_ids).scalar() or 0

    revenue_last_month_query = db.query(func.sum(Order.total)).filter(
        Order.created_at >= last_month_start,
        Order.created_at <= last_month_end,
        Order.estado.in_(FINAL_SALE_STATUSES)
    )
    total_revenue_last_month = _scope_orders(revenue_last_month_query, scoped_location_ids).scalar() or 0

    def _to_float(value) -> float:
        return float(value or 0)

    return DashboardStats(
        active_products=active_products,
        total_products=total_products,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count,
        total_inventory_value=_to_float(inventory_value),
        pending_orders=pending_orders,
        total_orders_today=total_orders_today,
        total_revenue_today=_to_float(total_revenue_today),
        total_revenue_month=_to_float(total_revenue_month),
        total_revenue_last_month=_to_float(total_revenue_last_month)
    )

@router.post("/forecast", response_model=ForecastingSummary)
def generate_forecast(
    payload: ForecastAnalyticsRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
):
    """Genera predicciones avanzadas con filtros y cache opcional."""

    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
    scoped_location_ids = accessible_location_ids
    if payload.location_id is not None:
        location_obj = validate_location_exists(db, payload.location_id)
        require_location_access(db, current_user, location_obj.id, "can_view")
        scoped_location_ids = [location_obj.id]

    cacheable = (
        payload.use_cache
        and not payload.force_refresh
        and not payload.product_ids
        and payload.location_id is None
        and scoped_location_ids is None
        and payload.min_confidence == 0.0
        and payload.trend in (None, "any")
    )

    if cacheable:
        cache = getattr(request.app.state, "forecast_cache", None)
        if cache and cache.get("summary"):
            return cache["summary"]

    forecasts = generate_sales_forecasts(
        db,
        days_history=payload.days_history,
        product_ids=payload.product_ids,
        location_ids=scoped_location_ids,
    )

    if payload.min_confidence:
        forecasts = [f for f in forecasts if f.confidence >= payload.min_confidence]

    if payload.trend and payload.trend != "any":
        forecasts = [f for f in forecasts if f.trend == payload.trend]

    forecasts = forecasts[: payload.limit]
    summary = summarize_forecasts(db, forecasts)

    if cacheable:
        request.app.state.forecast_cache = {
            "generated_at": datetime.now(UTC),
            "summary": summary,
        }

    return summary
