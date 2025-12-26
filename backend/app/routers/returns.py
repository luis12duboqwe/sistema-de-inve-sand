from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Order, Return, ReturnItem, Stock, Product, ProductIMEI, StockHistory, IMEIHistory, OrderItem, User
from app.schemas import ReturnCreate, ReturnResponse, ReturnItemResponse, PaginatedResponse
from typing import List
from app.auth import get_current_active_user, check_permission

router = APIRouter(prefix="/api/returns", tags=["returns"])

@router.get("", response_model=PaginatedResponse[ReturnResponse])
def list_returns(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("orders:edit"))
):
    """
    Lista todas las devoluciones.
    """
    returns = db.query(Return).order_by(Return.created_at.desc()).all()
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

    # 2. Crear Objeto Return
    new_return = Return(
        order_id=return_data.order_id,
        reason=return_data.reason,
        created_by=current_user.username,
        status="completed" # Por ahora procesamos inmediatamente
    )
    db.add(new_return)
    db.flush() # Obtener ID

    return_items_response = []

    # Cargar devoluciones previas para evitar sobre-retornos
    previous_items = db.query(ReturnItem).join(Return, ReturnItem.return_id == Return.id).filter(
        Return.order_id == order.id
    ).all()
    returned_quantities = {}
    for prev in previous_items:
        returned_quantities[prev.product_id] = returned_quantities.get(prev.product_id, 0) + prev.quantity

    # 3. Procesar Items
    for item in return_data.items:
        # Validar que el producto estaba en la orden
        order_item = db.query(OrderItem).filter(
            OrderItem.order_id == order.id,
            OrderItem.product_id == item.product_id
        ).first()
        
        if not order_item:
            raise HTTPException(status_code=400, detail=f"El producto {item.product_id} no pertenece a esta orden")
        
        # Validar cantidad acumulada con devoluciones previas
        already_returned = returned_quantities.get(item.product_id, 0)
        if already_returned + item.quantity > order_item.cantidad:
            raise HTTPException(
                status_code=400,
                detail=f"Cantidad a devolver ({already_returned + item.quantity}) excede la comprada ({order_item.cantidad}) para producto {item.product_id}"
            )

        returned_quantities[item.product_id] = already_returned + item.quantity

        # Crear ReturnItem
        return_item = ReturnItem(
            return_id=new_return.id,
            product_id=item.product_id,
            quantity=item.quantity,
            condition=item.condition,
            action=item.action,
            imei=item.imei
        )
        db.add(return_item)
        
        # 4. Lógica de Inventario (Solo si la acción implica reingreso)
        if item.action in ["refund", "warranty_exchange", "store_credit"]:
            # Buscar Stock en la ubicación original de la orden
            stock = db.query(Stock).filter(
                Stock.product_id == item.product_id,
                Stock.location_id == order.source_location_id
            ).first()
            
            if not stock:
                # Si no existe stock (raro), crearlo
                stock = Stock(
                    product_id=item.product_id,
                    location_id=order.source_location_id,
                    cantidad_disponible=0,
                    cantidad_reservada=0
                )
                db.add(stock)
            
            # Aumentar Stock
            stock_anterior = stock.cantidad_disponible
            
            if item.condition == 'defectuoso':
                # V2.0: Sumar a stock defectuoso (no disponible para venta)
                stock.cantidad_defectuosa += item.quantity
            else:
                # Si está en buen estado, sumar a disponible
                stock.cantidad_disponible += item.quantity
            
            stock_nuevo = stock.cantidad_disponible
            
            # Historial Stock
            stock_history = StockHistory(
                product_id=item.product_id,
                location_id=order.source_location_id,
                tipo_cambio='devolucion',
                cantidad=item.quantity,
                stock_anterior=stock_anterior,
                stock_nuevo=stock_nuevo,
                referencia_id=new_return.id,
                referencia_tipo='return',
                notas=f"Devolución Orden #{order.id}: {item.condition}",
                usuario=current_user.username
            )
            db.add(stock_history)
            
            # 5. Lógica IMEI
            if item.imei:
                imei_obj = db.query(ProductIMEI).filter(
                    ProductIMEI.imei == item.imei
                ).first()

                if not imei_obj:
                    raise HTTPException(status_code=400, detail=f"IMEI {item.imei} no existe en inventario")

                if imei_obj.order_id != order.id:
                    raise HTTPException(status_code=400, detail=f"IMEI {item.imei} no pertenece a la orden {order.id}")

                # Evitar doble devolución del mismo IMEI
                imei_already_returned = db.query(ReturnItem).join(Return, ReturnItem.return_id == Return.id).filter(
                    Return.order_id == order.id,
                    ReturnItem.imei == item.imei
                ).first()
                if imei_already_returned or not imei_obj.vendido:
                    raise HTTPException(status_code=400, detail=f"IMEI {item.imei} ya fue devuelto o liberado previamente")

                imei_obj.vendido = False
                imei_obj.order_id = None

                imei_history = IMEIHistory(
                    imei=item.imei,
                    product_id=item.product_id,
                    location_id=order.source_location_id,
                    event_type='devolucion',
                    reference_id=new_return.id,
                    reference_type='return',
                    notes=f"Devolución por {item.condition} - Acción: {item.action}",
                    created_by=current_user.username
                )
                db.add(imei_history)

    try:
        db.commit()
        db.refresh(new_return)
        return new_return
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
