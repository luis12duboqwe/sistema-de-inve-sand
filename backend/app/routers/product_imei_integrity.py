"""Canonical sellable-IMEI boundary for product inventory views.

Returned defective serials remain auditable in ProductIMEI/IMEIHistory but must
never reappear in selectors or product responses as sellable stock.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import exists, or_
from sqlalchemy.orm import Session

from app.auth import check_permission, get_current_active_user
from app.database import get_db
from app.models import ProductIMEI, ReturnItem, User
from app.routers import products
from app.utils.location_access import get_accessible_location_ids, require_location_access


router = APIRouter(prefix="/api/products", tags=["products"])
UNSELLABLE_IMEI_STATES = {"devolucion_defectuosa", "conteo_fisico_faltante"}

_original_serialize_product = products._serialize_product


def _record_is_currently_sellable(record: ProductIMEI) -> bool:
    state = str(getattr(record, "acquisition_type", "") or "").strip().lower()
    return (
        not bool(record.vendido)
        and record.transfer_id is None
        and record.order_id is None
        and state not in UNSELLABLE_IMEI_STATES
    )


def _serialize_product_integrity(product, accessible_location_ids=None):
    """Keep ProductResponse.imeis aligned with the sellable current-state pool."""
    payload = _original_serialize_product(product, accessible_location_ids)
    if hasattr(product, "imeis") and product.imeis:
        visible = [
            record.imei
            for record in product.imeis
            if _record_is_currently_sellable(record)
            and (
                accessible_location_ids is None
                or record.location_id in accessible_location_ids
            )
        ]
        payload.imei = visible[0] if visible else None
        payload.imeis = visible or None
    return payload


# Product/list routes resolve this module-global serializer at request time, so a
# single rebind keeps every product response consistent without duplicating those
# mature handlers.
products._serialize_product = _serialize_product_integrity


@router.get(
    "/{product_id}/imeis",
    response_model=List[str],
    dependencies=[Depends(check_permission("inventory:view"))],
)
def get_product_imeis_integrity(
    product_id: int,
    location_id: Optional[int] = Query(None, description="Filtrar por ubicación"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return only IMEIs that are genuinely eligible for a new sale.

    Besides current quarantine markers, the historical ReturnItem lookup protects
    upgraded databases created before defective returns received an explicit
    acquisition_type marker.
    """
    historical_defective = exists().where(
        ReturnItem.imei == ProductIMEI.imei,
        ReturnItem.condition == "defectuoso",
    )

    query = db.query(ProductIMEI.imei).filter(
        ProductIMEI.product_id == product_id,
        ProductIMEI.vendido == False,
        ProductIMEI.transfer_id == None,
        ProductIMEI.order_id == None,
        or_(
            ProductIMEI.acquisition_type == None,
            ~ProductIMEI.acquisition_type.in_(UNSELLABLE_IMEI_STATES),
        ),
        ~historical_defective,
    )

    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
    if location_id is not None:
        require_location_access(db, current_user, location_id, "can_view")
        query = query.filter(ProductIMEI.location_id == location_id)
    elif accessible_location_ids is not None:
        query = query.filter(ProductIMEI.location_id.in_(accessible_location_ids))

    return [row.imei for row in query.order_by(ProductIMEI.id.asc()).all()]
