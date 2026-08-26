"""Canonical candidate-product lookup for AI conversation context.

AI messages are free-form user text. Search keywords derived from those messages
must remain literal when they are passed to SQL LIKE expressions; otherwise `%`,
`_` and `\\` can broaden candidate selection and contaminate recommendations,
customer memory, or photo-request product selection.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models import Customer, Product, Stock
from app.routers.ai_intelligence import _extract_search_keywords


def _escape_like_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def find_candidate_products_integrity(
    db: Session,
    message: str,
    customer: Optional[Customer] = None,
    limit: int = 5,
) -> List[Product]:
    """Preserve legacy candidate ranking while treating keywords literally."""

    search_text = message
    if customer and customer.last_referenced_product_name:
        lowered = message.lower()
        if any(
            token in lowered
            for token in [
                "gris",
                "negro",
                "blanco",
                "ese",
                "esa",
                "este",
                "fotos",
                "foto",
                "imagen",
            ]
        ):
            search_text = f"{message} {customer.last_referenced_product_name}"

    keywords = _extract_search_keywords(search_text)
    if not keywords and customer and customer.last_referenced_product_name:
        keywords = _extract_search_keywords(customer.last_referenced_product_name)

    if not keywords:
        return []

    escaped_terms = [f"%{_escape_like_literal(keyword)}%" for keyword in keywords[:6]]

    and_conditions = []
    for term in escaped_terms:
        and_conditions.append(
            or_(
                Product.nombre.ilike(term, escape="\\"),
                Product.marca.ilike(term, escape="\\"),
                Product.modelo.ilike(term, escape="\\"),
                Product.sku.ilike(term, escape="\\"),
                Product.categoria.ilike(term, escape="\\"),
            )
        )

    candidates = (
        db.query(Product)
        .options(joinedload(Product.stock_items).joinedload(Stock.location))
        .filter(Product.activo == True, *and_conditions)
        .limit(limit)
        .all()
    )

    if candidates:
        return candidates

    or_conditions = []
    for term in escaped_terms:
        or_conditions.extend(
            [
                Product.nombre.ilike(term, escape="\\"),
                Product.marca.ilike(term, escape="\\"),
                Product.modelo.ilike(term, escape="\\"),
                Product.sku.ilike(term, escape="\\"),
            ]
        )

    return (
        db.query(Product)
        .options(joinedload(Product.stock_items).joinedload(Stock.location))
        .filter(Product.activo == True, or_(*or_conditions))
        .limit(limit)
        .all()
    )


__all__ = ["find_candidate_products_integrity"]
