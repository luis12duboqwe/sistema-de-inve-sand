from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import Optional, List
from datetime import datetime, timedelta, date
from decimal import Decimal
from app.database import get_db
from app.models import Order, Product, Stock, OrderItem, Location, User, Return, ReturnItem  # type: ignore[attr-defined]
from app.schemas import (
    DashboardStats, SalesReport, TopProduct, InventoryAlert
)
from app.auth import get_current_active_user, check_permission
from app.utils.order_queries import resolve_sales_profile_for_query
from app.utils.order_validators import validate_location_exists
from app.utils.location_access import get_accessible_location_ids, require_location_access

router = APIRouter(prefix="/api/reports", tags=["reports"])

FINAL_SALE_STATUSES = ["completada", "validada"]


def _apply_location_scope_to_orders(query, accessible_location_ids: Optional[list[int]]):
    if accessible_location_ids is not None:
        query = query.filter(Order.source_location_id.in_(accessible_location_ids))
    return query


def _apply_location_scope_to_stock(query, accessible_location_ids: Optional[list[int]]):
    if accessible_location_ids is not None:
        query = query.filter(Stock.location_id.in_(accessible_location_ids))
    return query


def _get_refunds_in_range(
    db: Session,
    start_dt: datetime,
    end_dt: datetime,
    sales_profile_id: Optional[int] = None,
    accessible_location_ids: Optional[list[int]] = None,
) -> Decimal:
    """
    Calcula el total de reembolsos (action='refund') de devoluciones creadas
    en el rango de fechas indicado.

    Solo considera items con action='refund' (no store_credit ni warranty_exchange).
    Si se indica sales_profile_id, filtra por el perfil de venta de la orden original.
    """
    query = (
        db.query(
            func.coalesce(
                func.sum(OrderItem.precio_unitario * ReturnItem.quantity),
                0,
            )
        )
        .select_from(Return)
        .join(ReturnItem, ReturnItem.return_id == Return.id)  # type: ignore[attr-defined]
        .join(Order, Order.id == Return.order_id)
        .join(
            OrderItem,
            (OrderItem.order_id == Order.id)
            & (OrderItem.product_id == ReturnItem.product_id),
        )
        .filter(
            Return.created_at >= start_dt,
            Return.created_at <= end_dt,
            ReturnItem.action == "refund",  # solo reembolsos de dinero
        )
    )
    if sales_profile_id:
        query = query.filter(Order.sales_profile_id == sales_profile_id)
    if accessible_location_ids is not None:
        query = query.filter(Order.source_location_id.in_(accessible_location_ids))

    result = query.scalar()
    return Decimal(result or 0)


@router.get("/dashboard", response_model=DashboardStats, dependencies=[Depends(check_permission("reports:view"))])
def get_dashboard_stats(
    sales_profile_slug: Optional[str] = Query(None, description="Filtrar ventas por canal de venta"),
    location_id: Optional[int] = Query(None, description="Filtrar stock por ubicación"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
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
    
    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
    scoped_location_id = None
    if location_id:
        location_obj = validate_location_exists(db, location_id)
        require_location_access(db, current_user, location_obj.id, "can_view")
        scoped_location_id = location_obj.id

    # Products stats - globales para admin, acotados por ubicación para usuarios restringidos
    product_query = db.query(Product)
    if scoped_location_id:
        product_query = product_query.join(Stock, Stock.product_id == Product.id).filter(Stock.location_id == scoped_location_id).distinct()
    elif accessible_location_ids is not None:
        product_query = product_query.join(Stock, Stock.product_id == Product.id).filter(Stock.location_id.in_(accessible_location_ids)).distinct()

    active_products = product_query.filter(Product.activo == True).count()
    total_products = product_query.count()
    
    # Stock alerts - Por ubicación si se especifica, sino global
    stock_query = db.query(Stock).join(Product).filter(Product.activo == True)
    if scoped_location_id:
        stock_query = stock_query.filter(Stock.location_id == scoped_location_id)
    else:
        stock_query = _apply_location_scope_to_stock(stock_query, accessible_location_ids)

    unit_value_expr = func.coalesce(
        func.nullif(Product.costo, 0),
        Product.precio
    )

    stock_stats = stock_query.with_entities(
        func.sum(
            case((Stock.cantidad_disponible == 0, 1), else_=0)
        ).label("out_of_stock"),
        func.sum(
            case(
                (((Stock.cantidad_disponible > 0) & (Stock.cantidad_disponible < 10)), 1),
                else_=0
            )
        ).label("low_stock"),
        func.sum(Stock.cantidad_disponible * unit_value_expr).label("inventory_value")
    ).first()

    low_stock_count = int((stock_stats.low_stock if stock_stats else 0) or 0)
    out_of_stock_count = int((stock_stats.out_of_stock if stock_stats else 0) or 0)
    total_inventory_value = Decimal((stock_stats.inventory_value if stock_stats else 0) or 0)
    
    # Orders stats - Filtrar por sales_profile si se especifica
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    orders_query = db.query(Order)
    if scoped_location_id:
        orders_query = orders_query.filter(Order.source_location_id == scoped_location_id)
    else:
        orders_query = _apply_location_scope_to_orders(orders_query, accessible_location_ids)
    sales_profile = resolve_sales_profile_for_query(db, sales_profile_slug, require_active=True)
    if sales_profile:
        orders_query = orders_query.filter(Order.sales_profile_id == sales_profile.id)
    
    pending_orders = orders_query.filter(Order.estado == "pendiente").count()
    
    # CRÍTICO: Excluir órdenes canceladas de revenue
    orders_today_stats = orders_query.filter(
        Order.created_at >= today_start,
        Order.created_at <= today_end,
        Order.estado.in_(FINAL_SALE_STATUSES)
    ).with_entities(
        func.count(Order.id),
        func.coalesce(func.sum(Order.total), 0)
    ).first()
    
    total_orders_today = int(orders_today_stats[0] or 0)
    total_revenue_today = Decimal(orders_today_stats[1] or 0)

    # Restar reembolsos del día
    refunds_today = _get_refunds_in_range(
        db, today_start, today_end,
        sales_profile_id=sales_profile.id if sales_profile else None,
        accessible_location_ids=[scoped_location_id] if scoped_location_id else accessible_location_ids,
    )
    total_revenue_today = max(Decimal("0.00"), total_revenue_today - refunds_today)

    # Month stats
    month_start = today.replace(day=1)
    month_start_dt = datetime.combine(month_start, datetime.min.time())
    
    orders_this_month_stats = orders_query.filter(
        Order.created_at >= month_start_dt,
        Order.estado.in_(FINAL_SALE_STATUSES)
    ).with_entities(
        func.count(Order.id),
        func.coalesce(func.sum(Order.total), 0)
    ).first()
    
    total_revenue_month = Decimal(orders_this_month_stats[1] or 0)

    # Restar reembolsos del mes actual
    month_end_dt = datetime.combine(today, datetime.max.time())
    refunds_month = _get_refunds_in_range(
        db, month_start_dt, month_end_dt,
        sales_profile_id=sales_profile.id if sales_profile else None,
        accessible_location_ids=[scoped_location_id] if scoped_location_id else accessible_location_ids,
    )
    total_revenue_month = max(Decimal("0.00"), total_revenue_month - refunds_month)

    # V2.1: Calcular Margen Bruto y Ticket Promedio del mes
    gross_margin_month = Decimal(0)
    average_ticket_month = Decimal(0)
    total_cost_month = Decimal(0)
    count_orders = int(orders_this_month_stats[0] or 0)

    if count_orders:
        cost_query = db.query(
            func.coalesce(
                func.sum(
                    OrderItem.cantidad
                    * func.coalesce(
                        OrderItem.costo_unitario,
                        func.coalesce(Product.costo, 0)
                    )
                ),
                0
            )
        ).join(
            Order, Order.id == OrderItem.order_id
        ).join(
            Product, Product.id == OrderItem.product_id
        ).filter(
            Order.created_at >= month_start_dt,
            Order.estado.in_(FINAL_SALE_STATUSES)
        )
        if scoped_location_id:
            cost_query = cost_query.filter(Order.source_location_id == scoped_location_id)
        else:
            cost_query = _apply_location_scope_to_orders(cost_query, accessible_location_ids)

        if sales_profile:
            cost_query = cost_query.filter(Order.sales_profile_id == sales_profile.id)

        total_cost_month = Decimal(cost_query.scalar() or 0)

        if total_revenue_month > 0:
            gross_margin_month = ((total_revenue_month - total_cost_month) / total_revenue_month) * 100
        
        average_ticket_month = total_revenue_month / count_orders

    # Last month stats
    if month_start.month == 1:
        last_month = month_start.replace(year=month_start.year - 1, month=12)
    else:
        last_month = month_start.replace(month=month_start.month - 1)
    
    last_month_start = datetime.combine(last_month, datetime.min.time())
    last_month_end = datetime.combine(month_start - timedelta(days=1), datetime.max.time())
    
    orders_last_month_stats = orders_query.filter(
        Order.created_at >= last_month_start,
        Order.created_at <= last_month_end,
        Order.estado.in_(FINAL_SALE_STATUSES)
    ).with_entities(
        func.count(Order.id),
        func.coalesce(func.sum(Order.total), 0)
    ).first()
    
    total_revenue_last_month = Decimal(orders_last_month_stats[1] or 0)

    # Restar reembolsos del mes pasado
    refunds_last_month = _get_refunds_in_range(
        db, last_month_start, last_month_end,
        sales_profile_id=sales_profile.id if sales_profile else None,
        accessible_location_ids=[scoped_location_id] if scoped_location_id else accessible_location_ids,
    )
    total_revenue_last_month = max(Decimal("0.00"), total_revenue_last_month - refunds_last_month)

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
        total_revenue_last_month=total_revenue_last_month,
        gross_margin_month=round(gross_margin_month, 2),
        average_ticket_month=round(average_ticket_month, 2)
    )


@router.get("/sales", response_model=SalesReport, dependencies=[Depends(check_permission("reports:view"))])
def get_sales_report(
    sales_profile_slug: Optional[str] = Query(None, description="Filtrar por canal de venta"),
    location_id: Optional[int] = Query(None, description="Filtrar por ubicación de origen"),
    date_from: Optional[date] = Query(None, description="Fecha inicial (default: hace 30 días)"),
    date_to: Optional[date] = Query(None, description="Fecha final (default: hoy)"),
    top_limit: int = Query(10, ge=1, le=50, description="Número de top products a retornar"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
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
        Order.estado.in_(FINAL_SALE_STATUSES)
    )
    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
    if location_id:
        location_obj = validate_location_exists(db, location_id)
        require_location_access(db, current_user, location_obj.id, "can_view")
        orders_query = orders_query.filter(Order.source_location_id == location_obj.id)
    else:
        orders_query = _apply_location_scope_to_orders(orders_query, accessible_location_ids)
    
    sales_profile = resolve_sales_profile_for_query(db, sales_profile_slug)
    if sales_profile:
        orders_query = orders_query.filter(Order.sales_profile_id == sales_profile.id)
    
    stats = orders_query.with_entities(
        func.count(Order.id),
        func.coalesce(func.sum(Order.total), 0)
    ).first()

    total_orders = stats[0] or 0
    total_revenue = Decimal(stats[1] or 0)
    average_order_value = total_revenue / total_orders if total_orders else Decimal("0.00")

    revenue_expr = func.coalesce(
        func.sum(
            case(
                (OrderItem.es_regalo_promocion == True, 0),
                else_=OrderItem.cantidad * OrderItem.precio_unitario
            )
        ),
        0
    ).label("revenue")

    product_query = db.query(
        Product.id,
        Product.nombre,
        func.coalesce(func.sum(OrderItem.cantidad), 0).label("units"),
        revenue_expr
    ).join(
        OrderItem, Product.id == OrderItem.product_id
    ).join(
        Order, Order.id == OrderItem.order_id
    ).filter(
        Order.created_at >= start_dt,
        Order.created_at <= end_dt,
        Order.estado.in_(FINAL_SALE_STATUSES)
    )
    product_query = _apply_location_scope_to_orders(product_query, accessible_location_ids)

    if sales_profile:
        product_query = product_query.filter(Order.sales_profile_id == sales_profile.id)

    top_products_rows = product_query.group_by(
        Product.id,
        Product.nombre
    ).order_by(revenue_expr.desc()).limit(top_limit).all()

    top_products = [
        TopProduct(
            product_id=row.id,
            product_name=row.nombre,
            units_sold=int(row.units or 0),
            total_revenue=Decimal(row.revenue or 0)
        )
        for row in top_products_rows
    ]
    
    return SalesReport(
        period_start=date_from,
        period_end=date_to,
        total_orders=total_orders,
        total_revenue=total_revenue,
        average_order_value=average_order_value,
        top_products=top_products
    )


@router.get("/inventory/alerts", response_model=List[InventoryAlert], dependencies=[Depends(check_permission("reports:view"))])
def get_inventory_alerts(
    location_id: Optional[int] = Query(None, description="Filtrar por ubicación"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
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
        location_obj = validate_location_exists(db, location_id)
        require_location_access(db, current_user, location_obj.id, "can_view")
        stock_query = stock_query.filter(Stock.location_id == location_obj.id)
    else:
        accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
        stock_query = _apply_location_scope_to_stock(stock_query, accessible_location_ids)
    
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

@router.get("/stock-summary-by-location", dependencies=[Depends(check_permission("reports:view"))])
def get_stock_summary_by_location(
    active_only: bool = Query(True, description="Solo ubicaciones activas"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
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
    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
    if accessible_location_ids is not None:
        query = query.filter(Location.id.in_(accessible_location_ids))
    
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


@router.get("/sales-summary-by-location", dependencies=[Depends(check_permission("reports:view"))])
def get_sales_summary_by_location(
    start_date: Optional[date] = Query(None, description="Fecha inicial (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Fecha final (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
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
        Order.estado.in_(['completada', 'validada'])  # Ventas confirmadas y validadas; excluye canceladas y pendientes
    )
    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
    if accessible_location_ids is not None:
        query = query.filter(Location.id.in_(accessible_location_ids))
    
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


@router.get("/top-products-by-location/{location_id}", dependencies=[Depends(check_permission("reports:view"))])
def get_top_products_by_location(
    location_id: int,
    limit: int = Query(10, ge=1, le=50, description="Cantidad de productos"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
):
    """
    Top N productos más vendidos de una ubicación específica.
    """
    from sqlalchemy import desc, and_
    
    # Verificar ubicación
    location = validate_location_exists(db, location_id)
    require_location_access(db, current_user, location_id, "can_view")
    
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
            Order.estado.in_(['completada', 'validada'])  # Ventas confirmadas y validadas; excluye canceladas y pendientes
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


@router.get("/bank-transfer-reconciliation", dependencies=[Depends(check_permission("reports:view"))])
def get_bank_transfer_reconciliation(
    start_date: Optional[date] = Query(None, description="Fecha inicial (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Fecha final (YYYY-MM-DD)"),
    location_id: Optional[int] = Query(None, description="Filtrar por ubicación"),
    bank_name: Optional[str] = Query(None, description="Filtrar por banco"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view")),
):
    """Detalle conciliable de órdenes pagadas por transferencia bancaria."""
    from sqlalchemy import desc

    if location_id is not None:
        validate_location_exists(db, location_id)
        require_location_access(db, current_user, location_id, "can_view")

    query = db.query(Order, Location.nombre.label("location_nombre")).outerjoin(
        Location,
        Location.id == Order.source_location_id,
    ).filter(
        Order.metodo_pago == "transferencia",
        Order.estado.in_(["completada", "validada"]),
    )

    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
    if accessible_location_ids is not None:
        query = query.filter(Order.source_location_id.in_(accessible_location_ids))
    if location_id is not None:
        query = query.filter(Order.source_location_id == location_id)
    if bank_name:
        query = query.filter(Order.transfer_bank_name.ilike(f"%{bank_name.strip()}%"))
    if start_date:
        query = query.filter(func.date(Order.created_at) >= start_date)
    if end_date:
        query = query.filter(func.date(Order.created_at) <= end_date)

    rows = query.order_by(desc(Order.created_at)).all()
    total = sum((order.total or Decimal("0")) for order, _location_nombre in rows)

    return {
        "total_amount": float(total),
        "total_orders": len(rows),
        "items": [
            {
                "order_id": order.id,
                "created_at": order.created_at,
                "customer_name": order.customer_name,
                "customer_phone": order.customer_phone,
                "location_id": order.source_location_id,
                "location_nombre": location_nombre,
                "bank_name": order.transfer_bank_name,
                "reference": order.transfer_reference,
                "total": float(order.total or 0),
                "estado": order.estado,
                "validated_by": order.validated_by,
                "validada_at": order.validada_at,
            }
            for order, location_nombre in rows
        ],
    }
