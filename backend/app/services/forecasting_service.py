from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Order, OrderItem, Product, Stock
from app.schemas import ForecastingSummary, SalesForecast


def _normalize_window(days_history: int) -> int:
    return max(30, min(days_history, 365))


def generate_sales_forecasts(
    db: Session,
    *,
    days_history: int = 60,
    product_ids: Optional[List[int]] = None,
    location_id: Optional[int] = None,
) -> List[SalesForecast]:
    """Compute per-product sales forecasts with optional filters."""

    window_days = _normalize_window(days_history)
    recent_window_days = min(30, window_days)
    older_window_days = max(window_days - recent_window_days, 0)

    now = datetime.now()
    recent_start = now - timedelta(days=recent_window_days)
    window_start = now - timedelta(days=window_days)

    product_query = db.query(Product).filter(Product.activo == True)
    if product_ids:
        product_query = product_query.filter(Product.id.in_(product_ids))

    products_raw: List[Product] = product_query.all()
    if not products_raw:
        return []

    resolved_products: List[Tuple[int, Product]] = []
    for product in products_raw:
        product_id_value = getattr(product, "id", None)
        if product_id_value is None:
            continue
        resolved_products.append((int(product_id_value), product))

    if not resolved_products:
        return []

    target_ids = [product_id for product_id, _ in resolved_products]

    stock_query = db.query(
        Stock.product_id,
        func.sum(Stock.cantidad_disponible).label("total_stock"),
        func.sum(Stock.cantidad_reservada).label("total_reserved"),
    ).filter(Stock.product_id.in_(target_ids))

    if location_id:
        stock_query = stock_query.filter(Stock.location_id == location_id)

    raw_stock_rows = stock_query.group_by(Stock.product_id).all()
    stock_rows: List[Tuple[int, Optional[int], Optional[int]]] = [
        (int(product_id), total, reserved) for product_id, total, reserved in raw_stock_rows
    ]

    stock_map: Dict[int, int] = {}
    for product_id, total, reserved in stock_rows:
        total_value = int(total or 0)
        reserved_value = int(reserved or 0)
        available = max(total_value - reserved_value, 0)
        stock_map[product_id] = available

    base_sales_query = db.query(
        OrderItem.product_id,
        func.sum(OrderItem.cantidad).label("qty_sum"),
    ).join(Order).filter(
        Order.estado != "cancelada",
        OrderItem.product_id.in_(target_ids),
    )

    if location_id:
        base_sales_query = base_sales_query.filter(Order.source_location_id == location_id)

    recent_sales_rows_raw = (
        base_sales_query.filter(Order.created_at >= recent_start)
        .group_by(OrderItem.product_id)
        .all()
    )
    older_sales_rows_raw = (
        base_sales_query.filter(
            Order.created_at >= window_start,
            Order.created_at < recent_start,
        )
        .group_by(OrderItem.product_id)
        .all()
    )

    recent_sales_rows: List[Tuple[int, Optional[int]]] = [
        (int(pid), qty) for pid, qty in recent_sales_rows_raw
    ]
    older_sales_rows: List[Tuple[int, Optional[int]]] = [
        (int(pid), qty) for pid, qty in older_sales_rows_raw
    ]

    recent_sales_map = {pid: int(qty or 0) for pid, qty in recent_sales_rows}
    older_sales_map = {pid: int(qty or 0) for pid, qty in older_sales_rows}

    forecasts: List[SalesForecast] = []

    for product_id, product in resolved_products:
        total_stock = stock_map.get(product_id, 0)
        recent_sales = recent_sales_map.get(product_id, 0)
        older_sales = older_sales_map.get(product_id, 0)

        recent_daily_sales = float(recent_sales) / recent_window_days if recent_window_days else 0.0
        older_daily_sales = (
            float(older_sales) / older_window_days if older_window_days else recent_daily_sales
        )

        trend = "stable"
        if older_daily_sales > 0:
            if recent_daily_sales > older_daily_sales * 1.1:
                trend = "increasing"
            elif recent_daily_sales < older_daily_sales * 0.9:
                trend = "decreasing"
        elif recent_daily_sales > 0:
            trend = "increasing"

        growth_factor = 1.0
        if older_daily_sales > 0:
            growth_factor = recent_daily_sales / older_daily_sales
            growth_factor = min(max(growth_factor, 0.5), 2.0)

        predicted_daily_sales = recent_daily_sales * growth_factor
        predicted_7 = int(round(predicted_daily_sales * 7))
        predicted_30 = int(round(predicted_daily_sales * 30))

        days_until_stockout = 999
        if predicted_daily_sales > 0:
            days_until_stockout = int(total_stock / predicted_daily_sales)

        restock_recommendation = max(0, predicted_30 - total_stock)

        confidence = 0.5
        if recent_sales > 10:
            confidence += 0.2
        if older_sales > 10:
            confidence += 0.2
        if trend == "stable":
            confidence += 0.1
        confidence = float(min(confidence, 1.0))

        forecasts.append(
            SalesForecast(
                product_id=product_id,
                product_name=f"{product.marca} {product.modelo}",
                current_stock=total_stock,
                average_daily_sales=round(recent_daily_sales, 2),
                predicted_sales_next_7_days=predicted_7,
                predicted_sales_next_30_days=predicted_30,
                days_until_stockout=days_until_stockout,
                restock_recommendation=restock_recommendation,
                confidence=round(confidence, 2),
                trend=trend,
            )
        )

    forecasts.sort(key=lambda forecast: forecast.days_until_stockout)
    return forecasts


def summarize_forecasts(db: Session, forecasts: List[SalesForecast]) -> ForecastingSummary:
    """Builds a summary object with aggregated metrics."""

    if not forecasts:
        return ForecastingSummary(
            total_products=0,
            products_needing_restock=0,
            critical_stock_alerts=0,
            estimated_revenue_7_days=0.0,
            estimated_revenue_30_days=0.0,
            top_performing_products=[],
            slow_moving_products=[],
            forecasts=[],
        )

    product_ids = [forecast.product_id for forecast in forecasts]

    price_rows = (
        db.query(Product.id, Product.precio)
        .filter(Product.id.in_(product_ids))
        .all()
    )
    price_map = {int(pid): Decimal(str(price or 0)) for pid, price in price_rows}

    estimated_revenue_7 = Decimal(0)
    estimated_revenue_30 = Decimal(0)

    products_needing_restock = 0
    critical_stock_alerts = 0
    top_performing: List[str] = []
    slow_moving: List[str] = []

    for forecast in forecasts:
        unit_price = price_map.get(forecast.product_id, Decimal(0))
        estimated_revenue_7 += unit_price * Decimal(forecast.predicted_sales_next_7_days)
        estimated_revenue_30 += unit_price * Decimal(forecast.predicted_sales_next_30_days)

        if forecast.restock_recommendation > 0:
            products_needing_restock += 1
        if forecast.days_until_stockout <= 7:
            critical_stock_alerts += 1

        if forecast.trend == "increasing" and forecast.average_daily_sales >= 0.5:
            top_performing.append(forecast.product_name)
        if forecast.average_daily_sales == 0 and forecast.current_stock > 0:
            slow_moving.append(forecast.product_name)

    return ForecastingSummary(
        total_products=len(forecasts),
        products_needing_restock=products_needing_restock,
        critical_stock_alerts=critical_stock_alerts,
        estimated_revenue_7_days=float(estimated_revenue_7),
        estimated_revenue_30_days=float(estimated_revenue_30),
        top_performing_products=top_performing[:10],
        slow_moving_products=slow_moving[:10],
        forecasts=forecasts,
    )
