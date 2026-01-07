from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
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

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
):
    """Obtiene KPIs para el dashboard principal"""
    today = date.today()
    first_day_month = today.replace(day=1)
    last_month_end = first_day_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    # Product stats
    total_products = db.query(Product).count()
    active_products = db.query(Product).filter(Product.activo == True).count()
    
    # Stock stats (sum of all locations)
    # This is complex because stock is in Stock table.
    # We need to aggregate stock per product first.
    
    # Simplified: Count products with total stock < 10
    # Subquery to get total stock per product
    stock_subquery = db.query(
        Stock.product_id,
        func.sum(Stock.cantidad_disponible).label("total_stock")
    ).group_by(Stock.product_id).subquery()
    
    low_stock_count = db.query(stock_subquery).filter(stock_subquery.c.total_stock < 10, stock_subquery.c.total_stock > 0).count()
    out_of_stock_count = db.query(stock_subquery).filter(stock_subquery.c.total_stock == 0).count()

    # Inventory Value
    # Cost * Total Stock
    inventory_value = db.query(
        func.sum(func.coalesce(Product.costo, Product.precio) * stock_subquery.c.total_stock)
    ).join(stock_subquery, Product.id == stock_subquery.c.product_id).scalar() or 0

    # Order stats
    pending_orders = db.query(Order).filter(Order.estado == 'pendiente').count()
    
    today_start = datetime.combine(today, datetime.min.time())
    total_orders_today = db.query(Order).filter(
        Order.created_at >= today_start,
        Order.estado != 'cancelada'
    ).count()
    
    total_revenue_today = db.query(func.sum(Order.total)).filter(
        Order.created_at >= today_start,
        Order.estado != 'cancelada'
    ).scalar() or 0

    total_revenue_month = db.query(func.sum(Order.total)).filter(
        Order.created_at >= first_day_month,
        Order.estado != 'cancelada'
    ).scalar() or 0

    total_revenue_last_month = db.query(func.sum(Order.total)).filter(
        Order.created_at >= last_month_start,
        Order.created_at <= last_month_end,
        Order.estado != 'cancelada'
    ).scalar() or 0

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

    cacheable = (
        payload.use_cache
        and not payload.force_refresh
        and not payload.product_ids
        and payload.location_id is None
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
        location_id=payload.location_id,
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
