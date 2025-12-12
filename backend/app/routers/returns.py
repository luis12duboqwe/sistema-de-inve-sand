from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Order, Return, ReturnItem, Stock, Product, ProductIMEI, StockHistory, IMEIHistory, OrderItem
from app.schemas import ReturnCreate, ReturnResponse, ReturnItemResponse, PaginatedResponse
from typing import List

router = APIRouter(prefix="/api/returns", tags=["returns"])

@router.get("", response_model=PaginatedResponse[ReturnResponse])
def list_returns(db: Session = Depends(get_db)):
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
def create_return(return_data: ReturnCreate, db: Session = Depends(get_db)):
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
        created_by=return_data.created_by,
        status="completed" # Por ahora procesamos inmediatamente
    )
    db.add(new_return)
    db.flush() # Obtener ID

    return_items_response = []

    # 3. Procesar Items
    for item in return_data.items:
        # Validar que el producto estaba en la orden
        order_item = db.query(OrderItem).filter(
            OrderItem.order_id == order.id,
            OrderItem.product_id == item.product_id
        ).first()
        
        if not order_item:
            raise HTTPException(status_code=400, detail=f"El producto {item.product_id} no pertenece a esta orden")
        
        # Validar cantidad (simple check, idealmente sumar devoluciones previas)
        if item.quantity > order_item.cantidad:
             raise HTTPException(status_code=400, detail=f"Cantidad a devolver mayor a la comprada para producto {item.product_id}")

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
        if item.action in ["refund", "exchange", "store_credit"]:
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
                usuario=return_data.created_by
            )
            db.add(stock_history)
            
            # 5. Lógica IMEI
            if item.imei:
                imei_obj = db.query(ProductIMEI).filter(
                    ProductIMEI.imei == item.imei
                ).first()
                
                if imei_obj:
                    imei_obj.vendido = False
                    imei_obj.order_id = None
                    # Si está defectuoso, tal vez mover a otra ubicación o marcar estado (pendiente implementar estado en IMEI)
                    
                    # Historial IMEI
                    imei_history = IMEIHistory(
                        imei=item.imei,
                        product_id=item.product_id,
                        location_id=order.source_location_id,
                        event_type='devolucion',
                        reference_id=new_return.id,
                        reference_type='return',
                        notes=f"Devolución por {item.condition} - Acción: {item.action}",
                        created_by=return_data.created_by
                    )
                    db.add(imei_history)

    try:
        db.commit()
        db.refresh(new_return)
        return new_return
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
