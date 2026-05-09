from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Order, Return, ReturnItem, ProductIMEI, IMEIHistory, User
from app.schemas import ReturnCreate, ReturnResponse, PaginatedResponse
from typing import List
from datetime import UTC, datetime

from app.auth import check_permission
from app.services.stock_transaction_helper import PreparedReturnItem, StockTransactionHelper
from app.utils.location_access import get_accessible_location_ids, require_location_access
from app.utils.order_validators import validate_location_exists
from app.utils.stock_manager import StockManager


def _utcnow() -> datetime:
    return datetime.now(UTC)

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
    Crea una devolución parcial o total de una orden.
    Maneja el reingreso al stock y la actualización de IMEIs.
    """
    # 1. Validar Orden
    order = db.query(Order).filter(Order.id == return_data.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    if order.estado == "cancelada":
        raise HTTPException(status_code=400, detail="No se pueden hacer devoluciones de órdenes canceladas")

    # 2. Validar ubicación de origen de la orden (activa)
    source_location = validate_location_exists(db, order.source_location_id)
    require_location_access(db, current_user, source_location.id, "can_edit")

    user_name = getattr(current_user, "username", "sistema") if current_user else "sistema"

    new_return = Return(
        order_id=return_data.order_id,
        reason=return_data.reason,
        created_by=user_name,
        status="completed" # Por ahora procesamos inmediatamente
    )
    db.add(new_return)
    db.flush() # Obtener ID

    stock_helper = StockTransactionHelper(db)
    stock_manager = stock_helper.stock_manager

    prepared_items: List[PreparedReturnItem] = stock_helper.prepare_return_items(
        order=order,
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
            # Para warranty_exchange registra como 'garantia_entrada' en lugar de 'devolucion'
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
            # Actualizar el event_type al más específico para garantías
            if effective_event == "garantia_entrada":
                for imei_rec in prepared.imeis_to_release:
                    # La entrada más reciente de historial es la que se acaba de crear
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

        # Procesar equipo de reemplazo en cambios por garantía
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
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
