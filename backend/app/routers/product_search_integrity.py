"""Canonical product listing with literal-text search semantics.

The legacy endpoint interpolates user keywords directly into SQL LIKE patterns, so
``%`` and ``_`` act as wildcards.  Product search is user-facing text search: those
characters (and the escape character itself) must be matched literally.
"""

from __future__ import annotations

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.auth import check_permission
from app.database import get_db
from app.models import Product, Stock, User
from app.routers.products import _serialize_product
from app.schemas import PaginatedResponse, ProductResponse
from app.utils.location_access import get_accessible_location_ids


router = APIRouter(prefix="/api/products", tags=["products"])


def _escape_like_literal(value: str) -> str:
    """Escape SQL LIKE metacharacters so product search treats input literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("", response_model=PaginatedResponse[ProductResponse])
def list_products_integrity(
    search: Optional[str] = Query(None, description="Buscar por nombre, marca o modelo"),
    location_id: Optional[int] = Query(None, description="Filtrar por ubicación con stock disponible"),
    include_inactive: bool = Query(False, description="Incluir productos inactivos y sin stock"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:view")),
):
    """List products while treating every search keyword as literal user text."""
    query = db.query(Product).options(
        joinedload(Product.stock_items).joinedload(Stock.location)
    )
    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")

    if accessible_location_ids == []:
        return PaginatedResponse(
            items=[],
            total=0,
            page=page,
            per_page=per_page,
            pages=0,
        )

    if location_id:
        if accessible_location_ids is not None and location_id not in accessible_location_ids:
            raise HTTPException(status_code=403, detail="No tiene acceso a esta ubicación")
        stock_filters = [Stock.location_id == location_id]
        if not include_inactive:
            stock_filters.append(Stock.cantidad_disponible > 0)
        query = query.join(Stock, Product.id == Stock.product_id).filter(*stock_filters).distinct()
    elif accessible_location_ids is not None:
        stock_filters = [Stock.location_id.in_(accessible_location_ids)]
        if not include_inactive:
            stock_filters.append(Stock.cantidad_disponible > 0)
        query = query.join(Stock, Product.id == Stock.product_id).filter(*stock_filters).distinct()

    if not include_inactive:
        query = query.filter(Product.activo == True)  # noqa: E712

    if search:
        keywords = search.split()
        for keyword in keywords:
            term = f"%{_escape_like_literal(keyword)}%"
            query = query.filter(
                or_(
                    Product.nombre.ilike(term, escape="\\"),
                    Product.marca.ilike(term, escape="\\"),
                    Product.modelo.ilike(term, escape="\\"),
                    Product.sku.ilike(term, escape="\\"),
                )
            )

    total = query.count()
    products = query.offset((page - 1) * per_page).limit(per_page).all()

    return PaginatedResponse(
        items=[_serialize_product(product, accessible_location_ids) for product in products],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0,
    )
