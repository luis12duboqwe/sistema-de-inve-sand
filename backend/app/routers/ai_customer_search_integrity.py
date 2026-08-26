"""Canonical AI-customer listing with literal search semantics."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import check_permission
from app.database import get_db
from app.models import Customer, User
from app.schemas import AICustomerResponse, PaginatedResponse


router = APIRouter(prefix="/api/ai", tags=["AI Intelligence"])


def _escape_like_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get(
    "/customers",
    response_model=PaginatedResponse[AICustomerResponse],
)
def list_customers_ai_integrity(
    search: Optional[str] = Query(None, description="Texto a buscar por nombre o teléfono"),
    is_troll: Optional[bool] = Query(None, description="Filtrar por clientes marcados como troll"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=10, le=200, description="Resultados por página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("ai:manage")),
) -> PaginatedResponse[AICustomerResponse]:
    """List AI customers while treating search text as literal input."""

    query = db.query(Customer)

    if search:
        like_term = f"%{_escape_like_literal(search)}%"
        query = query.filter(
            or_(
                Customer.phone_number.ilike(like_term, escape="\\"),
                Customer.name.ilike(like_term, escape="\\"),
            )
        )

    if is_troll is not None:
        query = query.filter(Customer.is_troll == is_troll)

    total = query.count()
    offset = (page - 1) * per_page
    customers = (
        query.order_by(
            Customer.last_interaction_at.desc().nullslast(),
            Customer.created_at.desc(),
        )
        .offset(offset)
        .limit(per_page)
        .all()
    )

    records = [
        AICustomerResponse(
            id=customer.id,
            phone_number=customer.phone_number,
            name=customer.name,
            email=customer.email,
            notes=customer.notes,
            is_troll=customer.is_troll,
            is_blocked=customer.is_blocked,
            reputation_score=customer.reputation_score,
            daily_message_count=customer.daily_message_count,
            last_interaction_at=customer.last_interaction_at,
            conversation_summary=customer.conversation_summary,
            ai_memory_json=customer.ai_memory_json,
            last_referenced_product_id=customer.last_referenced_product_id,
            last_referenced_product_name=customer.last_referenced_product_name,
            last_referenced_color=customer.last_referenced_color,
            last_referenced_variant=customer.last_referenced_variant,
            memory_updated_at=customer.memory_updated_at,
            created_at=customer.created_at,
        )
        for customer in customers
    ]

    pages = max(0, (total + per_page - 1) // per_page)
    return PaginatedResponse(
        items=records,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


__all__ = ["list_customers_ai_integrity", "router"]
