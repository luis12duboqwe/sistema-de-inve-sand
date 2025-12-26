from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, Query

from app.models import SalesProfile


def resolve_sales_profile_for_query(
    db: Session,
    sales_profile_slug: Optional[str],
    *,
    require_active: bool = False
) -> Optional[SalesProfile]:
    """Resuelve SalesProfile para filtros de consulta y valida su existencia.

    - require_active=True replica la validación usada en search_orders.
    """
    if not sales_profile_slug:
        return None

    query = db.query(SalesProfile).filter(SalesProfile.slug == sales_profile_slug)
    if require_active:
        query = query.filter(SalesProfile.active == True)

    sales_profile = query.first()
    if not sales_profile:
        detail = (
            f"El canal de venta con slug '{sales_profile_slug}' no fue encontrado"
            + (" o está inactivo" if require_active else "")
        )
        raise HTTPException(status_code=404, detail=detail)

    return sales_profile
