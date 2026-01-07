from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
import math

from app.database import get_db
from app.models import Product
from app.schemas import CategoriaEnum, CondicionEnum, PaginatedResponse, PublicProductResponse

router = APIRouter(prefix="/api/public", tags=["public"])

@router.get("/catalog", response_model=PaginatedResponse[PublicProductResponse])
def get_public_catalog(
    search: Optional[str] = Query(None),
    category: Optional[CategoriaEnum] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Obtiene el catálogo público de productos.
    No requiere autenticación.
    Oculta costos y cantidades exactas.
    """
    query = db.query(Product).filter(Product.activo == True)
    
    # Eager load stock to calculate availability
    query = query.options(joinedload(Product.stock_items))
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Product.nombre.ilike(search_term),
                Product.marca.ilike(search_term),
                Product.modelo.ilike(search_term)
            )
        )
        
    if category:
        query = query.filter(Product.categoria == category)
        
    total = query.count()
    offset = (page - 1) * per_page
    products = query.offset(offset).limit(per_page).all()
    
    items = []
    for p in products:
        # Calculate total stock across all locations
        total_stock = sum(
            max((s.cantidad_disponible or 0) - (s.cantidad_reservada or 0), 0) 
            for s in p.stock_items
        )
        
        items.append(PublicProductResponse(
            id=p.id,
            nombre=p.nombre,
            marca=p.marca,
            modelo=p.modelo,
            categoria=p.categoria,
            condicion=p.condicion,
            precio=p.precio,
            moneda=p.moneda,
            capacidad=p.capacidad,
            color=p.color,
            in_stock=total_stock > 0
        ))
        
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0
    )
