from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Order, Return, ReturnItem, ProductIMEI, IMEIHistory, User
from app.schemas import ReturnCreate, ReturnResponse, PaginatedResponse
from typing import List
from datetime import UTC, datetime
from types import SimpleNamespace
import logging

from app.auth import check_permission
from app.services.stock_transaction_helper import PreparedReturnItem, StockTransactionHelper
from app.utils.location_access import get_accessible_location_ids, require_location_access
from app.utils.order_validators import validate_location_exists
from app.utils.stock_manager import StockManager


logger = logging.getLogger(__name__)
FINAL_RETURNABLE_ORDER_STATUSES = {"completada", "validada"}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _aggregate_order_for_return_validation(order: Order) -> SimpleNamespace:
    """Build a read-only validation view with one quantity total per product.

    Historical/API orders may contain multiple OrderItem rows for the same product
    (for example, when unit prices differ). The stock helper validates returns by
    product, so feeding it only the last matching line would incorrectly cap the
    returnable quantity at that single line instead of the total quantity sold.
    """
    grouped: dict[int, SimpleNamespace] = {}
    for item in order.items or []:
        product_id = getattr(item, "product_id", None)
        if product_id is None:
            continue
        product_key = int(product_id)
        quantity = int(getattr(item, "cantidad", 0) or 0)
        existing = grouped.get(product_key)
        if existing is None:
            grouped[product_key] = SimpleNamespace(
                product_id=product_key,
                cantidad=quantity,
                product=getattr(item, "product", None),
            )
        else:
            existing.cantidad += quantity

    return SimpleNamespace(
        id=order.id,
        estado=order.estado,
        items=list(grouped.values()),
    )


def _validate_refund_paid_quantities(db: Session, order: Order, return_data: ReturnCreate) -> None:
    """Never grant a cash refund for promotional/gift quantities.

    Physical return validation still considers every sold/gift unit so stock can be
    reconciled. Monetary ``refund`` actions are separately capped to quantities that
    were actually paid for; prior refunds consume that paid allowance.

    ``create_return`` locks the parent order row before invoking this check, so two
    concurrent refund requests for the same order cannot both consume the same last
    paid allowance before either transaction commits.
    """
    paid_quantities: dict[int, int] = {}
    for item in order.items or []:
        if bool(getattr(item, "es_regalo_promocion", False)):
            continue
        product_id = getattr(item, "product_id", None)
        if product_id is None:
            continue
        key = int(product_id)
        paid_quantities[key] = paid_quantities.get(key, 0) + int(getattr(item, "cantidad", 0) or 0)

    previous_refund_quantities: dict[int, int] = {}
    previous_refunds = (
        db.query(ReturnItem)
        .join(Return, ReturnItem.return_id == Return.id)
        .filter(Return.order_id == order.id, ReturnItem.action == "refund")
        .all()
    )
    for item in previous_refunds:
        key = int(item.product_id)
        previous_refund_quantities[key] = previous_refund_quantities.get(key, 0) + int(item.quantity or 0)

    requested_refund_quantities: dict[int, int] = {}
    for item in return_data.items:
        action = item.action.value if hasattr(item.action, "value") else str(item.action)
        if action != "refund":
            continue
        key = int(item.product_id)
        requested_refund_quantities[key] = requested_refund_quantities.get(key, 0) + int(item.quantity or 0)

    for product_id, requested in requested_refund_quantities.items():
        paid = paid_quantities.get(product_id, 0)
        already_refunded = previous_refund_quantities.get(product_id, 0)
        if already_refunded + requested > paid:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"La cantidad a reembolsar del producto {product_id} excede las unidades pagadas. "
                    "Las unidades entregadas como regalo/promoción pueden devolverse físicamente, "
                    "pero no generan reembolso en efectivo."
                ),
            )


def _validate_serialized_return_quantities(order: Order, return_data: ReturnCreate) -> None:
    """Keep stock quantity and IMEI release one-to-one for serialized products."""
    products = {
        int(item.product_id): item.product
        for item in (order.items or [])
        if getattr(item, "product_id", None) is not None
    }
    for item in return_data.items:
        product = products.get(int(item.product_id))
        if product and bool(getattr(product, "is_serialized", False)) and int(item.quantity or 0) != 1:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Los productos serializados deben devolverse una unidad por ítem, "
                    "indicando el IMEI correspondiente a cada unidad."
                ),
            )


router = APIRouter(prefix="/api/returns", tags=["returns"])


@router.get("", response_model=PaginatedResponse[ReturnResponse])
def list_returns(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("orders:view"))
):
    """
    Lista todas las devoluciones.
    """
    query = db.query(Return).join(Order, Order.id == Return.order_id)
    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
    if accessible_location_ids is not None:
        query = query.filter(Order.source_location_id.in_(accessible_location_ids))
    returns = query.order_by(Return.created_at.desc()).all()
    return PaginatedResponse(
        items=returns,
        total=len(returns),
        page=1,
        per_page=len(returns) if returns else 10,
        pages=1
    )


@router.post("", response_model=ReturnResponse, status_code=201)
def create_return(
    return_data: ReturnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("orders:edit"))
):
    """
    Crea una devolución parcial o total de una venta ya finalizada.

    Una orden pendiente o por entregar todavía puede cambiar/cancelarse y, por tanto,
    nunca debe reingresar stock por el flujo de devoluciones. Solo las ventas que ya
    alcanzaron un estado final son elegibles.
    """
    # The order is the shared allowance row for every return on a sale. Lock it before
    # reading previous returns so two concurrent requests cannot both validate against
    # the same pre-refund state and then restore/refund the same paid unit twice.
    order = (
        db.query(Order)
        .filter(Order.id == return_data.order_id)
        .with_for_update()
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    if order.estado not in FINAL_RETURNABLE_ORDER_STATUSES:
        if order.estado == "cancelada":
            detail = "No se pueden hacer devoluciones de órdenes canceladas"
        else:
            detail = (
                "La devolución solo puede procesarse después de completar la venta. "
                "Para una orden pendiente o por entregar, edítela o cancélela en lugar de devolverla."
            )
        raise HTTPException(status_code=400, detail=detail)

    source_location = validate_location_exists(db, order.source_location_id)
    require_location_access(db, current_user, source_location.id, "can_edit")
    _validate_refund_paid_quantities(db, order, return_data)
    _validate_serialized_return_quantities(order, return_data)

    user_name = getattr(current_user, "username", "sistema") if current_user else "sistema"

    new_return = Return(
        order_id=return_data.order_id,
        reason=return_data.reason,
        created_by=user_name,
        status="completed"
    )
    db.add(new_return)
    db.flush()

    stock_helper = StockTransactionHelper(db)
    stock_manager = stock_helper.stock_manager

    validation_order = _aggregate_order_for_return_validation(order)
    prepared_items: List[PreparedReturnItem] = stock_helper.prepare_return_items(
        order=validation_order,  # type: ignore[arg-type] - intentionally read-only validation view
        items_payload=return_data.items,
    )

    restock_actions = {"refund", "warranty_exchange", "store_credit"}

    for prepared in prepared_items:
        return_item = ReturnItem(
            return_id=new_return.id,
            product_id=prepared.product.id,
            quantity=prepared.quantity,
            condition=prepared.condition,
            action=prepared.action,
            imei=prepared.imei_value,
            replacement_imei=prepared.replacement_imei_value,
        )
        db.add(return_item)

        if prepared.action in restock_actions:
            stock_manager.process_return_stock(
                product_id=prepared.product.id,
                location_id=source_location.id,
                quantity=prepared.quantity,
                defective=prepared.condition == "defectuoso",
                reference_id=new_return.id,
                notes=f"Devolución Orden #{order.id}: {prepared.condition}",
                user_id=user_name,
            )

        if prepared.imeis_to_release:
            effective_event = (
                "garantia_entrada" if prepared.action == "warranty_exchange" else "devolucion"
            )
            stock_manager.process_return_imeis(
                prepared.imeis_to_release,
                return_id=new_return.id,
                condition=prepared.condition,
                action=prepared.action,
                user_id=user_name,
            )
            if effective_event == "garantia_entrada":
                for imei_rec in prepared.imeis_to_release:
                    last_history = (
                        db.query(IMEIHistory)
                        .filter(
                            IMEIHistory.imei == imei_rec.imei,
                            IMEIHistory.reference_id == new_return.id,
                            IMEIHistory.reference_type == "return",
                        )
                        .order_by(IMEIHistory.id.desc())
                        .first()
                    )
                    if last_history:
                        last_history.event_type = "garantia_entrada"
                        last_history.notes = (
                            f"Equipo defectuoso recibido del cliente - Devolución #{new_return.id} "
                            f"(Orden #{order.id}) - Condición: {prepared.condition}"
                        )

        if prepared.action == "warranty_exchange" and prepared.replacement_imei_record:
            stock_manager.process_warranty_replacement_imei(
                replacement_imei_record=prepared.replacement_imei_record,
                original_order_id=order.id,
                return_id=new_return.id,
                user_id=user_name,
            )

    try:
        db.commit()
        db.refresh(new_return)
        return new_return
    except Exception:
        db.rollback()
        logger.exception("Error al procesar devolución de la orden %s", return_data.order_id)
        raise HTTPException(
            status_code=500,
            detail="Error interno al procesar la devolución. Intente nuevamente o contacte al administrador."
        )
