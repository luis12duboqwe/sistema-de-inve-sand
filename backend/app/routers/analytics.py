from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import List, Optional
from datetime import datetime, timedelta, date
from decimal import Decimal

from app.database import get_db
from app.models import Product, Order, OrderItem, Stock
from app.schemas import ForecastingSummary, SalesForecast, SalesReport, TopProduct, DashboardStats
from app.auth import check_permission, User

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

    return DashboardStats(
        active_products=active_products,
        total_products=total_products,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count,
        total_inventory_value=Decimal(inventory_value),
        pending_orders=pending_orders,
        total_orders_today=total_orders_today,
        total_revenue_today=Decimal(total_revenue_today),
        total_revenue_month=Decimal(total_revenue_month),
        total_revenue_last_month=Decimal(total_revenue_last_month)
    )

@router.get("/forecast", response_model=ForecastingSummary)
def generate_forecast(
    days_history: int = Query(60, ge=30, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
):
    """Genera predicciones de ventas basadas en historial"""
    
    # 1. Get active products with their total stock
    products = db.query(Product).filter(Product.activo == True).all()
    
    # Pre-fetch stock for all products to avoid N+1
    stock_map = {}
    stocks = db.query(Stock.product_id, func.sum(Stock.cantidad_disponible)).group_by(Stock.product_id).all()
    for pid, qty in stocks:
        stock_map[pid] = qty or 0

    # 2. Get order items from history window
    cutoff_date = datetime.now() - timedelta(days=days_history)
    recent_cutoff = datetime.now() - timedelta(days=30)
    
    # Query to get daily sales per product
    # We need to separate recent (last 30 days) vs older (30-60 days) for trend analysis
    
    sales_data = db.query(
        OrderItem.product_id,
        Order.created_at,
        OrderItem.cantidad
    ).join(Order).filter(
        Order.created_at >= cutoff_date,
        Order.estado != 'cancelada'
    ).all()

    # Process in Python (easier than complex SQL for trend analysis without window functions)
    product_sales = {}
    
    for pid, created_at, qty in sales_data:
        if pid not in product_sales:
            product_sales[pid] = {'recent': 0, 'older': 0}
        
        if created_at >= recent_cutoff:
            product_sales[pid]['recent'] += qty
        else:
            product_sales[pid]['older'] += qty

    forecasts = []
    total_revenue_7 = Decimal(0)
    total_revenue_30 = Decimal(0)
    products_needing_restock = 0
    critical_alerts = 0
    
    top_performing = []
    slow_moving = []

    for p in products:
        sales = product_sales.get(p.id, {'recent': 0, 'older': 0})
        current_stock = stock_map.get(p.id, 0)
        
        recent_daily = sales['recent'] / 30
        older_daily = sales['older'] / (days_history - 30) if days_history > 30 else recent_daily
        
        # Trend calculation
        trend = "stable"
        growth_factor = 1.0
        
        if older_daily > 0:
            change = (recent_daily - older_daily) / older_daily
            if change > 0.1:
                trend = "increasing"
                growth_factor = 1.1 # Conservative growth
            elif change < -0.1:
                trend = "decreasing"
                growth_factor = 0.9
        elif recent_daily > 0:
            trend = "increasing"
            growth_factor = 1.1

        predicted_daily = recent_daily * growth_factor
        pred_7 = round(predicted_daily * 7)
        pred_30 = round(predicted_daily * 30)
        
        days_until_stockout = 999
        if predicted_daily > 0:
            days_until_stockout = int(current_stock / predicted_daily)
        
        restock_rec = max(0, pred_30 - current_stock)
        
        # Confidence (simple heuristic based on volume)
        confidence = 0.5
        total_sales = sales['recent'] + sales['older']
        if total_sales > 50: confidence = 0.9
        elif total_sales > 20: confidence = 0.7
        elif total_sales > 5: confidence = 0.6
        
        forecast = SalesForecast(
            product_id=p.id,
            product_name=f"{p.marca} {p.modelo}",
            current_stock=current_stock,
            average_daily_sales=round(recent_daily, 2),
            predicted_sales_next_7_days=pred_7,
            predicted_sales_next_30_days=pred_30,
            days_until_stockout=days_until_stockout,
            restock_recommendation=restock_rec,
            confidence=confidence,
            trend=trend
        )
        forecasts.append(forecast)
        
        total_revenue_7 += Decimal(pred_7) * p.precio
        total_revenue_30 += Decimal(pred_30) * p.precio
        
        if restock_rec > 0:
            products_needing_restock += 1
        
        if days_until_stockout < 7:
            critical_alerts += 1
            
        if recent_daily > 0.5: # Arbitrary threshold for "top"
            top_performing.append(f"{p.marca} {p.modelo}")
        elif recent_daily == 0 and current_stock > 0:
            slow_moving.append(f"{p.marca} {p.modelo}")

    # Sort by urgency (days until stockout)
    forecasts.sort(key=lambda x: x.days_until_stockout)

    return ForecastingSummary(
        total_products=len(products),
        products_needing_restock=products_needing_restock,
        critical_stock_alerts=critical_alerts,
        estimated_revenue_7_days=total_revenue_7,
        estimated_revenue_30_days=total_revenue_30,
        top_performing_products=top_performing[:10],
        slow_moving_products=slow_moving[:10],
        forecasts=forecasts
    )
