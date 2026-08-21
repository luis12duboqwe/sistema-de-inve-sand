"""Canonical order state transition endpoints.

The legacy orders router historically mixed sale completion with daily-close
validation. These handlers are registered before it and establish one explicit
state machine plus serialized order mutations:

pending/for-delivery -> completed -> validated by /api/daily-close/validate.
Cancellation, completion and detail edits lock the Order row before touching Stock
so all competing operations use the same Order -> Stock lock order.
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import check_permission
from app.database import get_db
from app.models import Order, Return, User
from app.routers.orders import (
    FINAL_ORDER_STATUSES,
    _finalize_order_stock,
    _serialize_order,
    cancel_order as _legacy_cancel_order,
    update_order as _legacy_update_order,
)
from app.schemas import OrderResponse, OrderStatusUpdate, OrderUpdate
from app.services.order_service import resolve_user_label
from app.utils.audit import log_audit_event
from app.utils.location_access import require_location_access


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.put("/{order_id}/status", response_model=OrderResponse)
def update_order_status_canonical(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("orders:edit")),
):
    # Status transitions may later lock Stock while finalizing a sale. Lock Order
    # first so completion, cancellation, returns and edits all use one lock order.
    order = (
        db.query(Order)
        .filter(Order.id == order_id)
        .with_for_update()
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail=f"La orden con ID {order_id} no fue encontrada")

    if order.source_location_id:
        require_location_access(db, current_user, order.source_location_id, "can_edit")

    target = payload.estado.value if hasattr(payload.estado, "value") else str(payload.estado)
    previous = str(order.estado)

    if target == "cancelada":
        raise HTTPException(
            status_code=400,
            detail="Use POST /orders/{order_id}/cancel para cancelar y reconciliar stock/IMEIs correctamente.",
        )

    if previous == "cancelada":
        raise HTTPException(status_code=400, detail="No se puede cambiar el estado de una orden cancelada")

    if target == "validada":
        raise HTTPException(
            status_code=400,
            detail="Una venta solo pasa a validada mediante el cierre de día /api/daily-close/validate.",
        )

    if target not in {"pendiente", "por_entregar", "completada"}:
        raise HTTPException(status_code=400, detail=f"Estado no permitido en este flujo: {target}")

    if previous in FINAL_ORDER_STATUSES:
        if previous == target:
            return _serialize_order(order)
        raise HTTPException(
            status_code=409,
            detail="Una venta finalizada no puede volver a un estado operativo. Use devolución o cancelación auditada.",
        )

    if previous == "por_entregar" and target == "pendiente":
        raise HTTPException(status_code=409, detail="Una orden por entregar no puede volver a pendiente")

    if previous == target:
        return _serialize_order(order)

    if target == "completada":
        _finalize_order_stock(db, order, resolve_user_label(current_user))
        if order.completed_at is None:
            order.completed_at = datetime.now(UTC)

    order.estado = target
    log_audit_event(
        db,
        action="order.status_update",
        entity_type="order",
        entity_id=order.id,
        location_id=order.source_location_id,
        user=current_user,
        before_data={"estado": previous},
        after_data={"estado": target, "completed_at": order.completed_at.isoformat() if order.completed_at else None},
    )

    try:
        db.commit()
        db.refresh(order)
        return _serialize_order(order)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Error al actualizar estado de la orden %s", order_id)
        raise HTTPException(
            status_code=500,
            detail="Error interno al actualizar el estado de la orden. Intente nuevamente o contacte al administrador.",
        ) from exc


@router.put("/{order_id}", response_model=OrderResponse)
def update_order_canonical(
    order_id: int,
    updates: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("orders:edit")),
):
    """Serialize order detail edits with cancellation/completion before stock changes."""
    # The legacy edit implementation contains the mature item/IMEI/payment logic but
    # historically read Order without a row lock and then locked Stock. Acquiring the
    # parent lock first prevents Stock->Order / Order->Stock deadlocks and stale edits
    # that resume after a concurrent cancellation.
    order = (
        db.query(Order)
        .filter(Order.id == order_id)
        .with_for_update()
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail=f"La orden con ID {order_id} no fue encontrada")

    # Reuse the existing handler on the same Session while this transaction still
    # owns the Order lock. It revalidates status/location and performs stock changes.
    return _legacy_update_order(
        order_id=order_id,
        updates=updates,
        db=db,
        current_user=current_user,
    )


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order_canonical(
    order_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("orders:edit")),
):
    """Serialize cancellation with returns using a single Order -> Stock lock order."""
    order = (
        db.query(Order)
        .filter(Order.id == order_id)
        .with_for_update()
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail=f"La orden con ID {order_id} no fue encontrada")

    if order.source_location_id:
        require_location_access(db, current_user, order.source_location_id, "can_edit")

    existing_return = db.query(Return.id).filter(Return.order_id == order_id).first()
    if existing_return is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "No se puede cancelar una venta que ya tiene devoluciones. "
                "Use el flujo de devoluciones/ajustes auditados para cualquier corrección adicional."
            ),
        )

    return _legacy_cancel_order(
        order_id=order_id,
        reason=reason,
        db=db,
        current_user=current_user,
    )
