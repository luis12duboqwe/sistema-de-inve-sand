from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from datetime import datetime, timedelta, date
from decimal import Decimal
from app.database import get_db
from app.models import Order, Product, Stock, Profile, OrderItem, SalesProfile, Location
from app.schemas import (
    DashboardStats, SalesReport, TopProduct, InventoryAlert
)

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(
    sales_profile_slug: Optional[str] = Query(None, description="Filtrar ventas por canal de venta"),
    location_id: Optional[int] = Query(None, description="Filtrar stock por ubicación"),
    db: Session = Depends(get_db)
):
    """
    Obtiene KPIs del dashboard.
    
    V2.0: Productos son globales (no se filtran). 
    Ventas se pueden filtrar opcionalmente por sales_profile_slug.
    Stock se puede filtrar opcionalmente por location_id.
    
    Args:
        - sales_profile_slug: Filtro opcional por canal de venta (para ventas)
        - location_id: Filtro opcional por ubicación (para stock)
        
    Returns:
        Estadísticas del dashboard
    """
    
    # Products stats - GLOBALES (sin filtro)
    active_products = db.query(Product).filter(Product.activo == True).count()
    total_products = db.query(Product).count()
    
    # Stock alerts - Por ubicación si se especifica, sino global
    stock_query = db.query(Stock).join(Product).filter(Product.activo == True)
    if location_id:
        stock_query = stock_query.filter(Stock.location_id == location_id)
    
    stocks = stock_query.all()
    low_stock_count = sum(1 for s in stocks if 0 < s.cantidad_disponible < 10)
    out_of_stock_count = sum(1 for s in stocks if s.cantidad_disponible == 0)
    
    # Inventory value - Por ubicación si se especifica
    total_inventory_value = Decimal("0.00")
    for stock in stocks:
        if stock.product:
            # V2.0: Usar costo si existe, sino precio (fallback)
            valor_unitario = stock.product.costo if stock.product.costo > 0 else stock.product.precio
            total_inventory_value += valor_unitario * stock.cantidad_disponible
    
    # Orders stats - Filtrar por sales_profile si se especifica
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    orders_query = db.query(Order)
    if sales_profile_slug:
        sales_profile = db.query(SalesProfile).filter(
            SalesProfile.slug == sales_profile_slug,
            SalesProfile.active == True  # Validar que esté activo
        ).first()
        if sales_profile:
            orders_query = orders_query.filter(Order.sales_profile_id == sales_profile.id)
    
    pending_orders = orders_query.filter(Order.estado == "pendiente").count()
    
    # CRÍTICO: Excluir órdenes canceladas de revenue
    orders_today = orders_query.filter(
        Order.created_at >= today_start,
        Order.created_at <= today_end,
        Order.estado != "cancelada"  # Excluir canceladas
    ).all()
    
    total_orders_today = len(orders_today)
    total_revenue_today = sum(o.total for o in orders_today)
    
    # Month stats
    month_start = today.replace(day=1)
    month_start_dt = datetime.combine(month_start, datetime.min.time())
    
    orders_this_month = orders_query.filter(
        Order.created_at >= month_start_dt,
        Order.estado != "cancelada"  # Excluir canceladas
    ).all()
    
    total_revenue_month = sum(o.total for o in orders_this_month)
    
    # Last month stats
    if month_start.month == 1:
        last_month = month_start.replace(year=month_start.year - 1, month=12)
    else:
        last_month = month_start.replace(month=month_start.month - 1)
    
    last_month_start = datetime.combine(last_month, datetime.min.time())
    last_month_end = datetime.combine(month_start - timedelta(days=1), datetime.max.time())
    
    orders_last_month = orders_query.filter(
        Order.created_at >= last_month_start,
        Order.created_at <= last_month_end,
        Order.estado != "cancelada"  # Excluir canceladas
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
    sales_profile_slug: Optional[str] = Query(None, description="Filtrar por canal de venta"),
    date_from: Optional[date] = Query(None, description="Fecha inicial (default: hace 30 días)"),
    date_to: Optional[date] = Query(None, description="Fecha final (default: hoy)"),
    top_limit: int = Query(10, ge=1, le=50, description="Número de top products a retornar"),
    db: Session = Depends(get_db)
):
    """
    Genera reporte de ventas para un período específico.
    
    V2.0: Opcionalmente filtra por sales_profile_slug (canal de venta).
    
    Args:
        - sales_profile_slug: Filtro opcional por canal de venta
        - date_from: Fecha inicial (default: hace 30 días)
        - date_to: Fecha final (default: hoy)
        - top_limit: Número de top products (default: 10, max: 50)
        
    Returns:
        Reporte de ventas con top products
    """
    
    # Default dates
    if not date_to:
        date_to = datetime.now().date()
    if not date_from:
        date_from = date_to - timedelta(days=30)
    
    # Convert to datetime for query
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())
    
    # Query orders - optionally filter by sales_profile
    # CRÍTICO: Excluir órdenes canceladas de los reportes de ventas
    orders_query = db.query(Order).filter(
        Order.created_at >= start_dt,
        Order.created_at <= end_dt,
        Order.estado != "cancelada"  # Excluir canceladas
    )
    
    if sales_profile_slug:
        sales_profile = db.query(SalesProfile).filter(SalesProfile.slug == sales_profile_slug).first()
        if sales_profile:
            orders_query = orders_query.filter(Order.sales_profile_id == sales_profile.id)
    
    orders = orders_query.all()
    
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


@router.get("/inventory/alerts", response_model=List[InventoryAlert])
def get_inventory_alerts(
    location_id: Optional[int] = Query(None, description="Filtrar por ubicación"),
    db: Session = Depends(get_db)
):
    """
    Obtiene alertas de inventario para productos con stock bajo o agotado.
    
    V2.0: Opcionalmente filtra por location_id (ubicación física).
    Si no se especifica ubicación, muestra alertas de todas las ubicaciones.
    
    Args:
        - location_id: Filtro opcional por ubicación
        
    Returns:
        Lista de alertas de inventario ordenadas por severidad
    """
    
    # Query stock - optionally filter by location
    stock_query = db.query(Stock).join(Product).filter(Product.activo == True)
    
    if location_id:
        stock_query = stock_query.filter(Stock.location_id == location_id)
    
    stocks = stock_query.all()
    
    alerts = []
    
    for stock in stocks:
        if not stock.product:
            continue
        
        stock_qty = stock.cantidad_disponible
        alert_level = None
        
        if stock_qty == 0:
            alert_level = "out_of_stock"
        elif stock_qty < 5:
            alert_level = "critical"
        elif stock_qty < 10:
            alert_level = "low"
        
        if alert_level:
            alerts.append(InventoryAlert(
                product_id=stock.product.id,
                product_name=stock.product.nombre,
                sku=stock.product.sku,
                current_stock=stock_qty,
                category=stock.product.categoria,
                alert_level=alert_level
            ))
    
    # Sort by severity: out_of_stock > critical > low
    severity_order = {"out_of_stock": 0, "critical": 1, "low": 2}
    alerts.sort(key=lambda x: severity_order[x.alert_level])
    
    return alerts


# ============= REPORTES AVANZADOS POR UBICACIÓN V2.0 =============

@router.get("/stock-summary-by-location")
def get_stock_summary_by_location(
    active_only: bool = Query(True, description="Solo ubicaciones activas"),
    db: Session = Depends(get_db)
):
    """
    Resumen de stock agregado por ubicación.
    
    Retorna para cada ubicación:
    - Total de productos diferentes
    - Total de unidades disponibles
    - Valor total del inventario
    """
    from sqlalchemy import desc
    
    query = db.query(
        Location.id,
        Location.nombre,
        Location.tipo,
        func.count(func.distinct(Stock.product_id)).label('total_productos'),
        func.sum(Stock.cantidad_disponible).label('total_unidades'),
        func.sum(Stock.cantidad_disponible * Product.precio).label('valor_inventario')
    ).join(
        Stock, Location.id == Stock.location_id
    ).join(
        Product, Stock.product_id == Product.id
    ).filter(
        Product.activo == True
    )
    
    if active_only:
        query = query.filter(Location.activo == True)
    
    query = query.group_by(
        Location.id,
        Location.nombre,
        Location.tipo
    ).order_by(desc('total_unidades'))
    
    results = query.all()
    
    return [
        {
            "location_id": r.id,
            "location_nombre": r.nombre,
            "location_tipo": r.tipo,
            "total_productos": r.total_productos or 0,
            "total_unidades": r.total_unidades or 0,
            "valor_inventario": float(r.valor_inventario or 0)
        }
        for r in results
    ]


@router.get("/sales-summary-by-location")
def get_sales_summary_by_location(
    start_date: Optional[date] = Query(None, description="Fecha inicial (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Fecha final (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Resumen de ventas por ubicación en un período.
    
    V2.0: Usa source_location_id para identificar de dónde salió el stock.
    """
    from sqlalchemy import desc
    
    query = db.query(
        Location.id,
        Location.nombre,
        func.count(func.distinct(Order.id)).label('total_ordenes'),
        func.sum(OrderItem.cantidad).label('total_unidades'),
        func.sum(OrderItem.cantidad * OrderItem.precio_unitario).label('total_ingresos')
    ).join(
        Order, Location.id == Order.source_location_id
    ).join(
        OrderItem, Order.id == OrderItem.order_id
    ).filter(
        Order.estado == 'completada'  # Solo órdenes completadas (ventas confirmadas), excluye canceladas y pendientes
    )
    
    if start_date:
        query = query.filter(func.date(Order.created_at) >= start_date)
    if end_date:
        query = query.filter(func.date(Order.created_at) <= end_date)
    
    query = query.group_by(
        Location.id,
        Location.nombre
    ).order_by(desc('total_ingresos'))
    
    results = query.all()
    
    return [
        {
            "location_id": r.id,
            "location_nombre": r.nombre,
            "total_ordenes": r.total_ordenes or 0,
            "total_unidades_vendidas": r.total_unidades or 0,
            "total_ingresos": float(r.total_ingresos or 0),
            "ticket_promedio": float((r.total_ingresos / r.total_ordenes) if r.total_ordenes > 0 else 0)
        }
        for r in results
    ]


@router.get("/top-products-by-location/{location_id}")
def get_top_products_by_location(
    location_id: int,
    limit: int = Query(10, ge=1, le=50, description="Cantidad de productos"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Top N productos más vendidos de una ubicación específica.
    """
    from sqlalchemy import desc, and_
    
    # Verificar ubicación
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    
    query = db.query(
        Product.id,
        Product.nombre,
        Product.categoria,
        func.sum(OrderItem.cantidad).label('cantidad_vendida'),
        func.sum(OrderItem.cantidad * OrderItem.precio_unitario).label('ingresos')
    ).join(
        OrderItem, Product.id == OrderItem.product_id
    ).join(
        Order, OrderItem.order_id == Order.id
    ).filter(
        and_(
            Order.source_location_id == location_id,
            Order.estado == 'completada'  # Solo ventas completadas (confirmadas), excluye canceladas y pendientes
        )
    )
    
    if start_date:
        query = query.filter(func.date(Order.created_at) >= start_date)
    if end_date:
        query = query.filter(func.date(Order.created_at) <= end_date)
    
    query = query.group_by(
        Product.id,
        Product.nombre,
        Product.categoria
    ).order_by(desc('cantidad_vendida')).limit(limit)
    
    results = query.all()
    
    return [
        {
            "product_id": r.id,
            "product_nombre": r.nombre,
            "product_categoria": r.categoria,
            "cantidad_vendida": r.cantidad_vendida or 0,
            "ingresos_totales": float(r.ingresos or 0)
        }
        for r in results
    ]
