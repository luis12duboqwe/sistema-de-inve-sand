from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from decimal import Decimal
from app.database import get_db
from app.models import Order, Profile
from app.schemas import CustomerStats, CustomerHistory, OrderListResponse
from app.routers.orders import _serialize_order

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=List[CustomerStats])
def list_customers(
    profile_slug: Optional[str] = Query(None, description="Filtrar por slug del perfil"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db)
):
    """
    Lista clientes únicos con sus estadísticas básicas.
    
    Args:
        - profile_slug: Filtro opcional por perfil
        - page: Número de página (default: 1)
        - per_page: Resultados por página (default: 50, max: 100)
        
    Returns:
        Lista de clientes con estadísticas (ordenados por total gastado, descendente)
    """
    query = db.query(Order)
    
    if profile_slug:
        profile = db.query(Profile).filter(Profile.slug == profile_slug).first()
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"El perfil con slug '{profile_slug}' no fue encontrado"
            )
        query = query.filter(Order.profile_id == profile.id)
    
    # Get all orders
    orders = query.order_by(Order.created_at.desc()).all()
    
    # Group by customer phone
    customers_data = {}
    for order in orders:
        phone = order.customer_phone
        if phone not in customers_data:
            customers_data[phone] = {
                "phone": phone,
                "name": order.customer_name,
                "orders": [],
                "total": Decimal("0.00")
            }
        customers_data[phone]["orders"].append(order)
        customers_data[phone]["total"] += order.total
    
    # Build and sort result by total spent
    result = []
    for phone, data in customers_data.items():
        orders_list = data["orders"]
        result.append(CustomerStats(
            customer_phone=phone,
            customer_name=data["name"],
            total_orders=len(orders_list),
            total_spent=data["total"],
            average_order=data["total"] / len(orders_list) if orders_list else Decimal("0.00"),
            first_order_date=min(o.created_at for o in orders_list),
            last_order_date=max(o.created_at for o in orders_list)
        ))
    
    # Sort by total spent descending
    result.sort(key=lambda x: x.total_spent, reverse=True)
    
    # Apply pagination in-memory (after aggregation)
    # NOTE: Ideally this should be done at database level with GROUP BY,
    # but SQLite/SQLAlchemy makes this complex for this use case
    offset = (page - 1) * per_page
    return result[offset:offset + per_page]


@router.get("/{customer_phone}/stats", response_model=CustomerStats)
def get_customer_stats(
    customer_phone: str,
    profile_slug: Optional[str] = Query(None, description="Filtrar por slug del perfil"),
    db: Session = Depends(get_db)
):
    """
    Obtiene estadísticas de un cliente específico por su teléfono.
    
    Args:
        - customer_phone: Teléfono del cliente
        - profile_slug: Filtro opcional por perfil
        
    Returns:
        Estadísticas del cliente
        
    Raises:
        - 404: Si el cliente no tiene órdenes
    """
    query = db.query(Order).filter(Order.customer_phone == customer_phone)
    
    if profile_slug:
        profile = db.query(Profile).filter(Profile.slug == profile_slug).first()
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"El perfil con slug '{profile_slug}' no fue encontrado"
            )
        query = query.filter(Order.profile_id == profile.id)
    
    orders = query.all()
    
    if not orders:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron órdenes para el cliente con teléfono '{customer_phone}'"
        )
    
    total_spent = sum(o.total for o in orders)
    
    return CustomerStats(
        customer_phone=customer_phone,
        customer_name=orders[0].customer_name,
        total_orders=len(orders),
        total_spent=total_spent,
        average_order=total_spent / len(orders),
        first_order_date=min(o.created_at for o in orders),
        last_order_date=max(o.created_at for o in orders)
    )


@router.get("/{customer_phone}/history", response_model=CustomerHistory)
def get_customer_history(
    customer_phone: str,
    profile_slug: Optional[str] = Query(None, description="Filtrar por slug del perfil"),
    db: Session = Depends(get_db)
):
    """
    Obtiene el historial completo de órdenes de un cliente.
    
    Args:
        - customer_phone: Teléfono del cliente
        - profile_slug: Filtro opcional por perfil
        
    Returns:
        Estadísticas del cliente con lista completa de órdenes
        
    Raises:
        - 404: Si el cliente no tiene órdenes
    """
    query = db.query(Order).filter(Order.customer_phone == customer_phone)
    
    if profile_slug:
        profile = db.query(Profile).filter(Profile.slug == profile_slug).first()
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"El perfil con slug '{profile_slug}' no fue encontrado"
            )
        query = query.filter(Order.profile_id == profile.id)
    
    orders = query.order_by(Order.created_at.desc()).all()
    
    if not orders:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron órdenes para el cliente con teléfono '{customer_phone}'"
        )
    
    total_spent = sum(o.total for o in orders)
    
    return CustomerHistory(
        customer_phone=customer_phone,
        customer_name=orders[0].customer_name,
        total_orders=len(orders),
        total_spent=total_spent,
        average_order=total_spent / len(orders),
        first_order_date=min(o.created_at for o in orders),
        last_order_date=max(o.created_at for o in orders),
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
