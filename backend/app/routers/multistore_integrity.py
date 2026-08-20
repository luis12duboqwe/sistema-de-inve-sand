"""Integrity override for location cash closes."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import check_permission
from app.database import get_db
from app.models import Location, LocationDailyClose, Order, User
from app.schemas import LocationDailyCloseCreate, LocationDailyCloseResponse
from app.utils.audit import log_audit_event
from app.utils.location_access import require_location_access
from app.utils.order_integrity import effective_sale_column


router = APIRouter(prefix="/api/multistore-control", tags=["multistore-control"])


def _expected_payment(
    db: Session,
    location_id: int,
    payment_method: str,
    day_start: datetime,
    day_end: datetime,
) -> Decimal:
    sale_at = effective_sale_column(Order)
    orders = db.query(Order).filter(
        Order.source_location_id == location_id,
        Order.estado.in_(["completada", "validada"]),
        sale_at >= day_start,
        sale_at <= day_end,
    ).all()

    total = Decimal("0.00")
    for order in orders:
        if order.payment_breakdown:
            try:
                breakdown = json.loads(order.payment_breakdown)
            except (TypeError, json.JSONDecodeError):
                breakdown = []
            if isinstance(breakdown, list):
                for item in breakdown:
                    if isinstance(item, dict) and item.get("method") == payment_method:
                        total += Decimal(str(item.get("amount") or 0))
                continue
        if order.metodo_pago == payment_method:
            total += Decimal(order.total or 0)
    return total.quantize(Decimal("0.01"))


@router.post("/location-daily-closes", response_model=LocationDailyCloseResponse)
def create_location_daily_close_integrity(
    payload: LocationDailyCloseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("cash_closes:manage")),
):
    require_location_access(db, current_user, payload.location_id, "can_close_cash")
    if not db.query(Location).filter(Location.id == payload.location_id).first():
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")

    close_day = payload.close_date.date()
    day_start = payload.close_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = payload.close_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    existing = db.query(LocationDailyClose).filter(
        LocationDailyClose.location_id == payload.location_id,
        LocationDailyClose.close_day == close_day,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe un cierre de caja para esta ubicación en esa fecha")

    cash_expected = _expected_payment(db, payload.location_id, "efectivo", day_start, day_end)
    transfer_expected = _expected_payment(db, payload.location_id, "transferencia", day_start, day_end)
    card_expected = _expected_payment(db, payload.location_id, "tarjeta", day_start, day_end)
    financing_expected = _expected_payment(db, payload.location_id, "financiamiento", day_start, day_end)
    expected_total = cash_expected + transfer_expected + card_expected + financing_expected
    counted_total = payload.cash_counted + payload.transfer_total + payload.card_total + payload.financing_total

    close = LocationDailyClose(
        location_id=payload.location_id,
        close_date=payload.close_date,
        close_day=close_day,
        cash_expected=cash_expected,
        transfer_expected=transfer_expected,
        card_expected=card_expected,
        financing_expected=financing_expected,
        cash_counted=payload.cash_counted,
        transfer_total=payload.transfer_total,
        card_total=payload.card_total,
        financing_total=payload.financing_total,
        difference=counted_total - expected_total,
        notes=payload.notes,
        closed_by=current_user.username,
    )
    try:
        db.add(close)
        db.flush()
        log_audit_event(
            db,
            action="location_daily_close.create",
            entity_type="location_daily_close",
            entity_id=close.id,
            location_id=payload.location_id,
            user=current_user,
            after_data={
                **payload.model_dump(),
                "cash_expected": str(cash_expected),
                "transfer_expected": str(transfer_expected),
                "card_expected": str(card_expected),
                "financing_expected": str(financing_expected),
            },
        )
        db.commit()
        db.refresh(close)
        return LocationDailyCloseResponse.model_validate(close)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Error interno al crear el cierre de caja.",
        ) from exc
