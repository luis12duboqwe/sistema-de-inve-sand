"""Canonical rejection/cancellation paths for stock transfers."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import check_permission
from app.database import get_db
from app.models import ProductIMEI, Stock, StockTransfer, User
from app.routers.stock_transfers import _serialize_transfer
from app.schemas import StockTransferReject, StockTransferResponse
from app.utils.audit import log_audit_event
from app.utils.location_access import require_location_access
from app.utils.order_validators import validate_location_exists, validate_product_exists
from app.utils.stock_manager import StockManager, StockValidationError


router = APIRouter(prefix="/api/stock-transfers", tags=["stock-transfers"])


def _load_pending_transfer(db: Session, transfer_id: int) -> StockTransfer:
    transfer = db.query(StockTransfer).filter(StockTransfer.id == transfer_id).with_for_update().first()
    if not transfer:
        raise HTTPException(status_code=404, detail=f"Transferencia con ID {transfer_id} no encontrada")
    if transfer.estado != "pendiente":
        raise HTTPException(
            status_code=400,
            detail=f"Solo se puede operar una transferencia pendiente. Estado actual: '{transfer.estado}'",
        )
    return transfer


def _release_transfer_reservation(
    db: Session,
    transfer: StockTransfer,
    current_user: User,
    *,
    notes: str,
) -> Stock:
    product = validate_product_exists(db, transfer.product_id)
    source = validate_location_exists(db, transfer.from_location_id)
    require_location_access(db, current_user, source.id, "can_edit")

    source_stock = db.query(Stock).filter(
        Stock.product_id == product.id,
        Stock.location_id == source.id,
    ).with_for_update().first()
    if not source_stock:
        raise HTTPException(status_code=400, detail="Stock de origen no encontrado para liberar reserva")

    manager = StockManager(db)
    manager.release_reservation(
        stock=source_stock,
        quantity=transfer.cantidad,
        transfer_id=transfer.id,
        notes=notes,
        user_id=current_user.username,
        is_rejection=True,
    )
    reserved_imeis = db.query(ProductIMEI).filter(ProductIMEI.transfer_id == transfer.id).all()
    if reserved_imeis:
        manager.release_reserved_imeis(reserved_imeis)
    return source_stock


@router.post("/{transfer_id}/reject", response_model=StockTransferResponse)
def reject_transfer_integrity(
    transfer_id: int,
    reject_data: StockTransferReject,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:edit")),
):
    transfer = _load_pending_transfer(db, transfer_id)
    reason = reject_data.rejection_reason or "Sin motivo especificado"
    before = {"estado": transfer.estado, "cantidad": transfer.cantidad}
    try:
        _release_transfer_reservation(
            db,
            transfer,
            current_user,
            notes=f"Transferencia rechazada por {current_user.username}: {reason}",
        )
        transfer.estado = "rechazada"
        transfer.confirmed_at = datetime.now(UTC)
        transfer.confirmed_by = current_user.username
        transfer.rejection_reason = reject_data.rejection_reason
        log_audit_event(
            db,
            action="stock_transfer.reject",
            entity_type="stock_transfer",
            entity_id=transfer.id,
            location_id=transfer.from_location_id,
            user=current_user,
            before_data=before,
            after_data={"estado": transfer.estado, "rejection_reason": transfer.rejection_reason},
        )
        db.commit()
        db.refresh(transfer)
        return _serialize_transfer(transfer)
    except HTTPException:
        db.rollback()
        raise
    except StockValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno al rechazar la transferencia.") from exc


@router.delete("/{transfer_id}", status_code=204)
def cancel_transfer_integrity(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:edit")),
):
    transfer = _load_pending_transfer(db, transfer_id)
    before = {"estado": transfer.estado, "cantidad": transfer.cantidad}
    try:
        _release_transfer_reservation(
            db,
            transfer,
            current_user,
            notes=f"Transferencia cancelada: {transfer.notas or 'Sin motivo especificado'}",
        )
        transfer.estado = "cancelada"
        transfer.confirmed_at = datetime.now(UTC)
        transfer.confirmed_by = current_user.username
        log_audit_event(
            db,
            action="stock_transfer.cancel",
            entity_type="stock_transfer",
            entity_id=transfer.id,
            location_id=transfer.from_location_id,
            user=current_user,
            before_data=before,
            after_data={"estado": transfer.estado},
        )
        db.commit()
        return None
    except HTTPException:
        db.rollback()
        raise
    except StockValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno al cancelar la transferencia.") from exc
