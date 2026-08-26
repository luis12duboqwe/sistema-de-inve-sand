"""Canonical product resolution for AI-created orders.

The legacy AI workflow accepts free-form ``product_query`` values. Those values
are user-controlled text and must not become SQL LIKE wildcards when they contain
``%``, ``_`` or ``\\``. This module keeps the existing exact-then-partial
resolution contract while treating the query text literally.
"""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Product, Stock


def _escape_like_literal(value: str) -> str:
    """Escape SQL LIKE metacharacters while preserving ordinary text."""

    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def resolve_product_for_ai_item_integrity(
    db: Session,
    *,
    source_location_id: int,
    product_id: Optional[int],
    product_query: Optional[str],
) -> Product:
    """Resolve one AI order item without interpreting user text as LIKE syntax."""

    if product_id is not None:
        product = (
            db.query(Product)
            .filter(Product.id == product_id, Product.activo == True)
            .first()
        )
        if not product:
            raise HTTPException(status_code=404, detail=f"Producto no encontrado: id={product_id}")
        return product

    normalized_query = (product_query or "").strip()
    if not normalized_query:
        raise HTTPException(status_code=400, detail="Cada item requiere product_id o product_query")

    escaped_query = _escape_like_literal(normalized_query)
    stock_filters = (
        Product.activo == True,
        Stock.location_id == source_location_id,
        (Stock.cantidad_disponible - Stock.cantidad_reservada) > 0,
    )

    exact_match = (
        db.query(Product)
        .join(Stock, Stock.product_id == Product.id)
        .filter(
            *stock_filters,
            Product.nombre.ilike(escaped_query, escape="\\"),
        )
        .first()
    )
    if exact_match:
        return exact_match

    partial_term = f"%{escaped_query}%"
    partial_match = (
        db.query(Product)
        .join(Stock, Stock.product_id == Product.id)
        .filter(
            *stock_filters,
            or_(
                Product.nombre.ilike(partial_term, escape="\\"),
                Product.marca.ilike(partial_term, escape="\\"),
                Product.modelo.ilike(partial_term, escape="\\"),
                Product.sku.ilike(partial_term, escape="\\"),
            ),
        )
        .order_by(Product.nombre.asc())
        .first()
    )
    if not partial_match:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No se encontró producto para '{normalized_query}' "
                f"con stock en la ubicación {source_location_id}"
            ),
        )
    return partial_match


__all__ = ["resolve_product_for_ai_item_integrity"]
