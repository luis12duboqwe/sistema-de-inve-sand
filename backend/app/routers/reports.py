from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timedelta, date
from decimal import Decimal
from app.database import get_db
from app.models import Order, Product, Stock, Profile, OrderItem
from app.schemas import (
    DashboardStats, SalesReport, TopProduct, InventoryAlert
)

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(
    profile_slug: str = Query(..., description="Slug del perfil"),
    db: Session = Depends(get_db)
):
    """
    Obtiene KPIs del dashboard para un perfil específico.
    
    Args:
        - profile_slug: Slug del perfil
        
    Returns:
        Estadísticas del dashboard
        
    Raises:
        - 404: Si el perfil no existe
    """
    profile = db.query(Profile).filter(Profile.slug == profile_slug).first()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"El perfil con slug '{profile_slug}' no fue encontrado"
        )
    
    # Products stats
    active_products = db.query(Product).filter(
        Product.profile_id == profile.id,
        Product.activo == True
    ).count()
    
    total_products = db.query(Product).filter(
        Product.profile_id == profile.id
    ).count()
    
    # Stock alerts
    products_with_stock = db.query(Product).join(Stock).filter(
        Product.profile_id == profile.id,
        Product.activo == True
    ).all()
    
    low_stock_count = sum(1 for p in products_with_stock if p.stock and p.stock.cantidad_disponible < 10 and p.stock.cantidad_disponible > 0)
    out_of_stock_count = sum(1 for p in products_with_stock if p.stock and p.stock.cantidad_disponible == 0)
    
    # Inventory value
    total_inventory_value = Decimal("0.00")
    for product in products_with_stock:
        if product.stock:
            total_inventory_value += product.precio * product.stock.cantidad_disponible
    
    # Orders stats
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    pending_orders = db.query(Order).filter(
        Order.profile_id == profile.id,
        Order.estado == "pendiente"
    ).count()
    
    orders_today = db.query(Order).filter(
        Order.profile_id == profile.id,
        Order.created_at >= today_start,
        Order.created_at <= today_end
    ).all()
    
    total_orders_today = len(orders_today)
    total_revenue_today = sum(o.total for o in orders_today)
    
    # Month stats
    month_start = today.replace(day=1)
    month_start_dt = datetime.combine(month_start, datetime.min.time())
    
    orders_this_month = db.query(Order).filter(
        Order.profile_id == profile.id,
        Order.created_at >= month_start_dt
    ).all()
    
    total_revenue_month = sum(o.total for o in orders_this_month)
    
    # Last month stats
    if month_start.month == 1:
        last_month = month_start.replace(year=month_start.year - 1, month=12)
    else:
        last_month = month_start.replace(month=month_start.month - 1)
    
    last_month_start = datetime.combine(last_month, datetime.min.time())
    last_month_end = datetime.combine(month_start - timedelta(days=1), datetime.max.time())
    
    orders_last_month = db.query(Order).filter(
        Order.profile_id == profile.id,
        Order.created_at >= last_month_start,
        Order.created_at <= last_month_end
    ).all()
    
    total_revenue_last_month = sum(o.total for o in orders_last_month)
    
    return DashboardStats(
        active_products=active_products,
        total_products=total_products,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count,
        total_inventory_value=total_inventory_value,
        pending_orders=pending_orders,
        total_orders_today=total_orders_today,
        total_revenue_today=total_revenue_today,
        total_revenue_month=total_revenue_month,
        total_revenue_last_month=total_revenue_last_month
    )


@router.get("/sales", response_model=SalesReport)
def get_sales_report(
    profile_slug: str = Query(..., description="Slug del perfil"),
    date_from: Optional[date] = Query(None, description="Fecha inicial (default: hace 30 días)"),
    date_to: Optional[date] = Query(None, description="Fecha final (default: hoy)"),
    top_limit: int = Query(10, ge=1, le=50, description="Número de top products a retornar"),
    db: Session = Depends(get_db)
):
    """
    Genera reporte de ventas para un período específico.
    
    Args:
        - profile_slug: Slug del perfil
        - date_from: Fecha inicial (default: hace 30 días)
        - date_to: Fecha final (default: hoy)
        - top_limit: Número de top products (default: 10, max: 50)
        
    Returns:
        Reporte de ventas con top products
        
    Raises:
        - 404: Si el perfil no existe
    """
    profile = db.query(Profile).filter(Profile.slug == profile_slug).first()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"El perfil con slug '{profile_slug}' no fue encontrado"
        )
    
    # Default dates
    if not date_to:
        date_to = datetime.now().date()
    if not date_from:
        date_from = date_to - timedelta(days=30)
    
    # Convert to datetime for query
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())
    
    # Get orders in period
    orders = db.query(Order).filter(
        Order.profile_id == profile.id,
        Order.created_at >= start_dt,
        Order.created_at <= end_dt
    ).all()
    
    total_orders = len(orders)
    total_revenue = sum(o.total for o in orders)
    average_order_value = total_revenue / total_orders if total_orders > 0 else Decimal("0.00")
    
    # Calculate top products
    product_sales = {}
    
    for order in orders:
        for item in order.items:
            if item.product_id not in product_sales:
                product_sales[item.product_id] = {
                    "product": item.product,
                    "units": 0,
                    "revenue": Decimal("0.00")
                }
            product_sales[item.product_id]["units"] += item.cantidad
            if not item.es_regalo_promocion:
                product_sales[item.product_id]["revenue"] += item.precio_unitario * item.cantidad
    
    # Sort by revenue and get top N
    top_products_data = sorted(
        product_sales.values(),
        key=lambda x: x["revenue"],
        reverse=True
    )[:top_limit]
    
    top_products = [
        TopProduct(
            product_id=data["product"].id,
            product_name=data["product"].nombre,
            units_sold=data["units"],
            total_revenue=data["revenue"]
        )
        for data in top_products_data
    ]
    
    return SalesReport(
        period_start=date_from,
        period_end=date_to,
        total_orders=total_orders,
        total_revenue=total_revenue,
        average_order_value=average_order_value,
        top_products=top_products
    )


@router.get("/inventory/alerts", response_model=list[InventoryAlert])
def get_inventory_alerts(
    profile_slug: str = Query(..., description="Slug del perfil"),
    db: Session = Depends(get_db)
):
    """
    Obtiene alertas de inventario para productos con stock bajo o agotado.
    
    Args:
        - profile_slug: Slug del perfil
        
    Returns:
        Lista de alertas de inventario ordenadas por severidad
        
    Raises:
        - 404: Si el perfil no existe
    """
    profile = db.query(Profile).filter(Profile.slug == profile_slug).first()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"El perfil con slug '{profile_slug}' no fue encontrado"
        )
    
    products = db.query(Product).join(Stock).filter(
        Product.profile_id == profile.id,
        Product.activo == True
    ).all()
    
    alerts = []
    
    for product in products:
        if not product.stock:
            continue
        
        stock_qty = product.stock.cantidad_disponible
        alert_level = None
        
        if stock_qty == 0:
            alert_level = "out_of_stock"
        elif stock_qty < 5:
            alert_level = "critical"
        elif stock_qty < 10:
            alert_level = "low"
        
        if alert_level:
            alerts.append(InventoryAlert(
                product_id=product.id,
                product_name=product.nombre,
                sku=product.sku,
                current_stock=stock_qty,
                category=product.categoria,
                alert_level=alert_level
            ))
    
    # Sort by severity: out_of_stock > critical > low
    severity_order = {"out_of_stock": 0, "critical": 1, "low": 2}
    alerts.sort(key=lambda x: severity_order[x.alert_level])
    
    return alerts
