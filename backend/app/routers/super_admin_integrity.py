"""Additional integrity constraints for Super Admin correction tools."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, Product, ProductIMEI, Stock, StockHistory, User
from app.routers import super_admin as legacy_super_admin
from app.routers.order_state_integrity import cancel_order_canonical
from app.routers.super_admin import ReasonPayload, StockAdjustmentRequest, get_current_superuser_audited
from app.utils.audit import log_audit_event


router = APIRouter(prefix="/api/super-admin", tags=["super_admin"])


def _serialized_imei_count(db: Session, product_id: int, location_id: int) -> int:
    return int(
        db.query(func.count(ProductIMEI.id)).filter(
            ProductIMEI.product_id == product_id,
            ProductIMEI.location_id == location_id,
            ProductIMEI.vendido == False,
            ProductIMEI.transfer_id.is_(None),
            ProductIMEI.order_id.is_(None),
        ).scalar()
        or 0
    )


def _assert_serialized_stock_target(
    db: Session,
    product: Product,
    location_id: int,
    *,
    available: int,
    reserved: int,
    defective: int,
) -> None:
    if not product.is_serialized:
        return
    physical_target = int(available) + int(defective) - int(reserved)
    imeis_available = _serialized_imei_count(db, product.id, location_id)
    if physical_target != imeis_available:
        raise HTTPException(
            status_code=409,
            detail=(
                "Corrección rechazada: en un producto serializado, "
                f"disponible + defectuoso - reservado ({physical_target}) debe coincidir "
                f"con los IMEIs físicos disponibles ({imeis_available}). "
                "Use conteo físico/IMEI para reconciliar la diferencia."
            ),
        )


@router.post("/stock/adjust")
def adjust_stock_integrity(
    payload: StockAdjustmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_audited),
):
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    stock = db.query(Stock).filter(
        Stock.product_id == payload.product_id,
        Stock.location_id == payload.location_id,
    ).with_for_update().first()

    _assert_serialized_stock_target(
        db,
        product,
        payload.location_id,
        available=payload.cantidad_disponible,
        reserved=payload.cantidad_reservada,
        defective=payload.cantidad_defectuosa,
    )

    before = legacy_super_admin._serialize_stock(stock)
    if not stock:
        stock = Stock(product_id=payload.product_id, location_id=payload.location_id)
        db.add(stock)
        db.flush()

    previous_available = int(stock.cantidad_disponible or 0)
    stock.cantidad_disponible = payload.cantidad_disponible
    stock.cantidad_reservada = payload.cantidad_reservada
    stock.cantidad_defectuosa = payload.cantidad_defectuosa

    db.add(
        StockHistory(
            product_id=payload.product_id,
            location_id=payload.location_id,
            tipo_cambio="super_admin_adjustment",
            cantidad=payload.cantidad_disponible - previous_available,
            stock_anterior=previous_available,
            stock_nuevo=payload.cantidad_disponible,
            referencia_tipo="super_admin_panel",
            notas=payload.reason,
            usuario=current_user.username,
        )
    )
    log_audit_event(
        db,
        action="super_admin.stock.adjust",
        entity_type="stock",
        entity_id=stock.id,
        location_id=payload.location_id,
        user=current_user,
        before_data=before,
        after_data=legacy_super_admin._serialize_stock(stock),
        metadata={"reason": payload.reason},
    )
    db.commit()
    db.refresh(stock)
    return legacy_super_admin._serialize_stock(stock)


@router.post("/orders/{order_id}/cancel")
def super_admin_cancel_order_integrity(
    order_id: int,
    payload: ReasonPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_audited),
):
    """Use the same locked, return-aware cancellation path as ordinary operators."""
    return cancel_order_canonical(
        order_id=order_id,
        reason=f"SUPER ADMIN: {payload.reason}",
        db=db,
        current_user=current_user,
    )


def _loads_json_object(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


@router.post("/audit-logs/{audit_id}/revert")
def revert_audit_change_integrity(
    audit_id: int,
    payload: ReasonPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_audited),
):
    audit = db.query(AuditLog).filter(AuditLog.id == audit_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")

    if audit.action == "super_admin.stock.adjust":
        before = _loads_json_object(audit.before_data)
        stock = db.query(Stock).filter(Stock.id == audit.entity_id).first()
        if before is None or stock is None:
            raise HTTPException(status_code=400, detail="La corrección previa no puede revertirse de forma segura")
        product = db.query(Product).filter(Product.id == stock.product_id).first()
        if product:
            _assert_serialized_stock_target(
                db,
                product,
                stock.location_id,
                available=int(before.get("cantidad_disponible", 0)),
                reserved=int(before.get("cantidad_reservada", 0)),
                defective=int(before.get("cantidad_defectuosa", 0)),
            )

    # La implementación legacy ya audita la reversa. Los guards transaccionales de
    # órdenes validan además pagos/referencias si la reversa afecta una orden.
    return legacy_super_admin.revert_audit_change(
        audit_id=audit_id,
        payload=payload,
        db=db,
        current_user=current_user,
    )
