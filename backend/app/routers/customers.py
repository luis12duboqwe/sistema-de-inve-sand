from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, desc, distinct
from typing import List, Optional
from decimal import Decimal
from app.database import get_db
from app.models import Order, Profile, SalesProfile, Customer, User
from app.schemas import CustomerStats, CustomerHistory, OrderListResponse
from app.routers.orders import _serialize_order
from app.auth import get_current_active_user, check_permission

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=List[CustomerStats])
def list_customers(
    sales_profile_slug: Optional[str] = Query(None, description="Filtrar por canal de venta"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
):
    """
    Lista clientes únicos con sus estadísticas básicas.
    
    V2.0: Filtra por sales_profile_slug (canal de venta).
    Optimizado para usar agregación SQL en lugar de procesamiento en memoria.
    
    Args:
        - sales_profile_slug: Filtro opcional por canal de venta
        - page: Número de página (default: 1)
        - per_page: Resultados por página (default: 50, max: 100)
        
    Returns:
        Lista de clientes con estadísticas (ordenados por total gastado, descendente)
    """
    # Base query for filtering
    filter_conditions = []
    if sales_profile_slug:
        sales_profile = db.query(SalesProfile).filter(
            SalesProfile.slug == sales_profile_slug,
            SalesProfile.active == True
        ).first()
        if not sales_profile:
            raise HTTPException(
                status_code=404,
                detail=f"El canal de venta con slug '{sales_profile_slug}' no fue encontrado o está inactivo"
            )
        filter_conditions.append(Order.sales_profile_id == sales_profile.id)

    # Aggregation query
    query = db.query(
        Order.customer_phone,
        func.max(Order.customer_name).label('customer_name'),
        func.count(Order.id).label('total_orders'),
        func.sum(case((Order.estado != 'cancelada', Order.total), else_=0)).label('total_spent'),
        func.sum(case((Order.estado != 'cancelada', 1), else_=0)).label('completed_orders_count'),
        func.min(Order.created_at).label('first_order_date'),
        func.max(Order.created_at).label('last_order_date')
    )

    if filter_conditions:
        query = query.filter(*filter_conditions)

    query = query.group_by(Order.customer_phone).order_by(desc('total_spent'))
    
    # Pagination
    offset = (page - 1) * per_page
    results = query.offset(offset).limit(per_page).all()
    
    # Fetch AI Customer data
    phones = [row.customer_phone for row in results]
    ai_customers = {}
    if phones:
        customers_db = db.query(Customer).filter(Customer.phone_number.in_(phones)).all()
        ai_customers = {c.phone_number: c for c in customers_db}
    
    # Transform results to schema
    response = []
    for row in results:
        # row is a KeyedTuple
        total_spent = row.total_spent or Decimal("0.00")
        completed_count = row.completed_orders_count or 0
        
        ai_data = ai_customers.get(row.customer_phone)
        
        response.append(CustomerStats(
            customer_phone=row.customer_phone,
            customer_name=row.customer_name,
            total_orders=row.total_orders,
            total_spent=total_spent,
            average_order=total_spent / completed_count if completed_count > 0 else Decimal("0.00"),
            first_order_date=row.first_order_date,
            last_order_date=row.last_order_date,
            # AI Fields
            id=ai_data.id if ai_data else None,
            is_troll=ai_data.is_troll if ai_data else False,
            is_blocked=ai_data.is_blocked if ai_data else False,
            reputation_score=ai_data.reputation_score if ai_data else 100,
            daily_message_count=ai_data.daily_message_count if ai_data else 0
        ))
    
    return response


@router.get("/{customer_phone}/stats", response_model=CustomerStats)
def get_customer_stats(
    customer_phone: str,
    sales_profile_slug: Optional[str] = Query(None, description="Filtrar por canal de venta"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
):
    """
    Obtiene estadísticas de un cliente específico por su teléfono.
    
    V2.0: Filtra por sales_profile_slug (canal de venta).
    
    Args:
        - customer_phone: Teléfono del cliente
        - sales_profile_slug: Filtro opcional por canal de venta
        
    Returns:
        Estadísticas del cliente
        
    Raises:
        - 404: Si el cliente no tiene órdenes
    """
    query = db.query(Order).filter(Order.customer_phone == customer_phone)
    
    if sales_profile_slug:
        sales_profile = db.query(SalesProfile).filter(
            SalesProfile.slug == sales_profile_slug,
            SalesProfile.active == True  # Validar que esté activo
        ).first()
        if not sales_profile:
            raise HTTPException(
                status_code=404,
                detail=f"El canal de venta con slug '{sales_profile_slug}' no fue encontrado o está inactivo"
            )
        query = query.filter(Order.sales_profile_id == sales_profile.id)
    
    orders = query.all()
    
    if not orders:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron órdenes para el cliente con teléfono '{customer_phone}'"
        )
    
    # Solo contar órdenes completadas para total gastado (no canceladas)
    completed_orders = [o for o in orders if o.estado != 'cancelada']
    total_spent = sum(o.total for o in completed_orders)
    
    # Fetch AI Customer data
    ai_data = db.query(Customer).filter(Customer.phone_number == customer_phone).first()
    
    return CustomerStats(
        customer_phone=customer_phone,
        customer_name=orders[0].customer_name,
        total_orders=len(orders),
        total_spent=total_spent,
        average_order=total_spent / len(completed_orders) if completed_orders else Decimal("0.00"),
        first_order_date=min(o.created_at for o in orders),
        last_order_date=max(o.created_at for o in orders),
        # AI Fields
        id=ai_data.id if ai_data else None,
        is_troll=ai_data.is_troll if ai_data else False,
        is_blocked=ai_data.is_blocked if ai_data else False,
        reputation_score=ai_data.reputation_score if ai_data else 100,
        daily_message_count=ai_data.daily_message_count if ai_data else 0
    )


@router.get("/{customer_phone}/history", response_model=CustomerHistory)
def get_customer_history(
    customer_phone: str,
    sales_profile_slug: Optional[str] = Query(None, description="Filtrar por canal de venta"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
):
    """
    Obtiene el historial completo de órdenes de un cliente.
    
    V2.0: Filtra por sales_profile_slug (canal de venta).
    
    Args:
        - customer_phone: Teléfono del cliente
        - sales_profile_slug: Filtro opcional por canal de venta
        
    Returns:
        Estadísticas del cliente con lista completa de órdenes
        
    Raises:
        - 404: Si el cliente no tiene órdenes
    """
    query = db.query(Order).filter(Order.customer_phone == customer_phone)
    
    if sales_profile_slug:
        sales_profile = db.query(SalesProfile).filter(
            SalesProfile.slug == sales_profile_slug,
            SalesProfile.active == True  # Validar que esté activo
        ).first()
        if not sales_profile:
            raise HTTPException(
                status_code=404,
                detail=f"El canal de venta con slug '{sales_profile_slug}' no fue encontrado o está inactivo"
            )
        query = query.filter(Order.sales_profile_id == sales_profile.id)
    
    orders = query.order_by(Order.created_at.desc()).all()
    
    if not orders:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron órdenes para el cliente con teléfono '{customer_phone}'"
        )
    
    # Solo contar órdenes no canceladas en el total
    completed_orders = [o for o in orders if o.estado != 'cancelada']
    total_spent = sum(o.total for o in completed_orders)
    
    # Fetch AI Customer data
    ai_data = db.query(Customer).filter(Customer.phone_number == customer_phone).first()
    
    return CustomerHistory(
        customer_phone=customer_phone,
        customer_name=orders[0].customer_name,
        total_orders=len(orders),
        total_spent=total_spent,
        average_order=total_spent / len(completed_orders) if completed_orders else Decimal("0.00"),
        first_order_date=min(o.created_at for o in orders),
        last_order_date=max(o.created_at for o in orders),
        # AI Fields
        id=ai_data.id if ai_data else None,
        is_troll=ai_data.is_troll if ai_data else False,
        is_blocked=ai_data.is_blocked if ai_data else False,
        reputation_score=ai_data.reputation_score if ai_data else 100,
        daily_message_count=ai_data.daily_message_count if ai_data else 0,
        orders=[OrderListResponse(
            id=o.id,
            profile_id=o.profile_id,
            customer_name=o.customer_name,
            customer_phone=o.customer_phone,
            canal=o.canal,
            metodo_pago=o.metodo_pago,
            total=o.total,
            estado=o.estado,
            created_at=o.created_at
        ) for o in orders]
    )
