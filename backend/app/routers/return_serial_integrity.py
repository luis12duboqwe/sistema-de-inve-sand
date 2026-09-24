"""Serialized-device integrity hardening for returns and warranty exchanges.

This layer closes cross-flow gaps between sales, transfers and returns without
changing the public return contract. It keeps the existing mature return handler
as the transaction owner while strengthening the shared stock/IMEI boundaries.
"""

from __future__ import annotations

from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import check_permission
from app.database import get_db
from app.models import IMEIHistory, ProductIMEI, ReturnItem, Stock, StockHistory, User
from app.routers.returns import create_return as _legacy_create_return
from app.schemas import ReturnCreate, ReturnResponse
from app.services.stock_transaction_helper import StockTransactionHelper
from app.utils.location_access import require_location_access
from app.utils.stock_manager import StockManager, StockValidationError


router = APIRouter(prefix="/api/returns", tags=["returns"])

# ``acquisition_type`` is already used by the application as an operational state
# (for example ``conteo_fisico_faltante``), not only as immutable provenance.
# Keep unavailable serials out of the sellable pool until an explicit future
# rehabilitation workflow exists.
UNSELLABLE_IMEI_STATES = {"devolucion_defectuosa", "conteo_fisico_faltante"}

_return_user: ContextVar[User | None] = ContextVar("return_serial_user", default=None)

_original_validate_imeis = StockManager._validate_imeis
_original_process_return_imeis = StockManager.process_return_imeis
_original_prepare_return_items = StockTransactionHelper.prepare_return_items


def _imei_state(record: ProductIMEI) -> str:
    return str(getattr(record, "acquisition_type", "") or "").strip().lower()


def _imei_is_unsellable(db: Session, record: ProductIMEI) -> bool:
    """Return True for current or historical defective/unavailable serials.

    The history lookup protects databases upgraded from versions that predate the
    explicit ``devolucion_defectuosa`` operational marker. There is currently no
    repair/rehabilitation workflow, so any recorded defective return remains out of
    the sellable pool unless that future workflow explicitly changes the rule.
    """
    if _imei_state(record) in UNSELLABLE_IMEI_STATES:
        return True
    historical_defective_return = (
        db.query(ReturnItem.id)
        .filter(
            ReturnItem.imei == record.imei,
            ReturnItem.condition == "defectuoso",
        )
        .first()
    )
    return historical_defective_return is not None


def _validate_imeis_integrity(
    self: StockManager,
    product: Any,
    product_id: int,
    location_id: int,
    quantity: int,
    imeis_requested: list[str] | None,
    allow_pending_imei: bool,
) -> list[ProductIMEI]:
    """Reject serials reserved by another workflow or quarantined as defective."""
    if bool(getattr(product, "is_serialized", False)) and imeis_requested:
        requested = [str(value).strip() for value in imeis_requested if str(value).strip()]
        records = (
            self.db.query(ProductIMEI)
            .filter(ProductIMEI.imei.in_(requested))
            .with_for_update()
            .all()
        )
        by_imei = {record.imei: record for record in records}
        for imei in requested:
            record = by_imei.get(imei)
            if record is None:
                continue  # Preserve the mature helper's normal missing-IMEI error.
            if record.transfer_id is not None:
                raise HTTPException(
                    status_code=409,
                    detail=f"El IMEI {imei} está reservado en una transferencia pendiente",
                )
            if _imei_is_unsellable(self.db, record):
                raise HTTPException(
                    status_code=409,
                    detail=f"El IMEI {imei} no está habilitado para venta",
                )

    return _original_validate_imeis(
        self,
        product,
        product_id,
        location_id,
        quantity,
        imeis_requested,
        allow_pending_imei,
    )


def _prepare_return_items_integrity(
    self: StockTransactionHelper,
    *,
    order: Any,
    items_payload: Any,
):
    """Validate warranty serial state and the operator's replacement-store scope."""
    prepared = _original_prepare_return_items(
        self,
        order=order,
        items_payload=items_payload,
    )

    current_user = _return_user.get()
    for item in prepared:
        record = item.replacement_imei_record
        if record is None:
            continue

        if record.transfer_id is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"El IMEI de reemplazo {record.imei} está reservado en una "
                    "transferencia pendiente"
                ),
            )
        if record.order_id is not None:
            raise HTTPException(
                status_code=409,
                detail=f"El IMEI de reemplazo {record.imei} ya está reservado por otra orden",
            )
        if _imei_is_unsellable(self.db, record):
            raise HTTPException(
                status_code=409,
                detail=f"El IMEI de reemplazo {record.imei} no está habilitado para venta",
            )
        if record.location_id is None:
            raise HTTPException(
                status_code=409,
                detail=f"El IMEI de reemplazo {record.imei} no tiene una ubicación disponible",
            )
        if current_user is not None:
            require_location_access(self.db, current_user, int(record.location_id), "can_edit")

    return prepared


def _process_return_imeis_integrity(
    self: StockManager,
    imeis: list[ProductIMEI],
    *,
    return_id: int,
    condition: str,
    action: str,
    user_id: str | None = None,
) -> list[IMEIHistory]:
    """Quarantine a physically returned defective serial at the IMEI level."""
    histories = _original_process_return_imeis(
        self,
        imeis,
        return_id=return_id,
        condition=condition,
        action=action,
        user_id=user_id,
    )
    if str(condition).strip().lower() == "defectuoso":
        for record in imeis:
            record.acquisition_type = "devolucion_defectuosa"
            record.received_notes = (
                f"IMEI en cuarentena por devolución defectuosa #{return_id}; "
                "no disponible para venta"
            )
    return histories


def _process_warranty_replacement_imei_integrity(
    self: StockManager,
    *,
    replacement_imei_record: ProductIMEI,
    original_order_id: int,
    return_id: int,
    user_id: str | None = None,
) -> IMEIHistory:
    """Consume exactly one free, saleable serial for a warranty replacement."""
    if replacement_imei_record.vendido:
        raise HTTPException(
            status_code=400,
            detail=f"El IMEI de reemplazo {replacement_imei_record.imei} ya está marcado como vendido",
        )
    if replacement_imei_record.transfer_id is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"El IMEI de reemplazo {replacement_imei_record.imei} está reservado "
                "en una transferencia pendiente"
            ),
        )
    if replacement_imei_record.order_id is not None:
        raise HTTPException(
            status_code=409,
            detail=f"El IMEI de reemplazo {replacement_imei_record.imei} está reservado por otra orden",
        )
    if _imei_is_unsellable(self.db, replacement_imei_record):
        raise HTTPException(
            status_code=409,
            detail=f"El IMEI de reemplazo {replacement_imei_record.imei} no está habilitado para venta",
        )

    location_id = replacement_imei_record.location_id
    if location_id is None:
        raise HTTPException(
            status_code=409,
            detail=f"El IMEI de reemplazo {replacement_imei_record.imei} no tiene ubicación disponible",
        )

    stock = (
        self.db.query(Stock)
        .filter(
            Stock.product_id == replacement_imei_record.product_id,
            Stock.location_id == location_id,
        )
        .with_for_update()
        .first()
    )
    if stock is None:
        raise StockValidationError(
            f"No existe stock para el IMEI de reemplazo {replacement_imei_record.imei}"
        )

    self._assert_stock_invariants(stock, context="warranty_replacement:before")
    free_stock = int(stock.cantidad_disponible or 0) - int(stock.cantidad_reservada or 0)
    if free_stock < 1:
        raise StockValidationError(
            f"No hay stock libre para entregar el IMEI de reemplazo {replacement_imei_record.imei}"
        )

    previous_stock = int(stock.cantidad_disponible or 0)
    stock.cantidad_disponible = previous_stock - 1
    self._assert_stock_invariants(stock, context="warranty_replacement:after")

    now = datetime.now(UTC)
    self.db.add(
        StockHistory(
            product_id=replacement_imei_record.product_id,
            location_id=location_id,
            tipo_cambio="garantia_salida",
            cantidad=-1,
            stock_anterior=previous_stock,
            stock_nuevo=stock.cantidad_disponible,
            referencia_id=return_id,
            referencia_tipo="return",
            notas=f"Equipo de reemplazo por garantía - Devolución #{return_id}",
            usuario=user_id,
            created_at=now,
        )
    )

    replacement_imei_record.vendido = True
    replacement_imei_record.sold_at = now
    replacement_imei_record.order_id = original_order_id

    history = IMEIHistory(
        imei=replacement_imei_record.imei,
        product_id=replacement_imei_record.product_id,
        location_id=location_id,
        event_type="garantia_salida",
        reference_id=return_id,
        reference_type="return",
        notes=(
            f"Equipo de reemplazo entregado al cliente - Devolución #{return_id} "
            f"(Orden #{original_order_id})"
        ),
        created_by=user_id,
        created_at=now,
    )
    self.db.add(history)
    return history


# Patch shared transaction boundaries once. Sales, transfers, returns and direct
# service callers all instantiate these classes dynamically, so the protections are
# not limited to the HTTP wrapper below.
StockManager._validate_imeis = _validate_imeis_integrity  # type: ignore[method-assign]
StockManager.process_return_imeis = _process_return_imeis_integrity  # type: ignore[method-assign]
StockManager.process_warranty_replacement_imei = _process_warranty_replacement_imei_integrity  # type: ignore[method-assign]
StockTransactionHelper.prepare_return_items = _prepare_return_items_integrity  # type: ignore[method-assign]


@router.post("", response_model=ReturnResponse, status_code=201)
def create_return_serial_integrity(
    return_data: ReturnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("orders:edit")),
):
    """Delegate to the canonical return transaction with serial-scope context."""
    token = _return_user.set(current_user)
    try:
        return _legacy_create_return(
            return_data=return_data,
            db=db,
            current_user=current_user,
        )
    finally:
        _return_user.reset(token)
