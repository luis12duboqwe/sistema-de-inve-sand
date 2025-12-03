from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from app.database import get_db
from app.models import Order, OrderItem, Product, Profile, Stock
from app.schemas import (
    OrderCreate,
    OrderResponse,
    OrderListResponse,
    ProductResponse,
    OrderStatusUpdate,
    OrderUpdate
)

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _serialize_order(order: Order) -> OrderResponse:
    items_response = []
    for item in order.items:
        product = item.product
        items_response.append({
            "id": item.id,
            "product_id": item.product_id,
            "cantidad": item.cantidad,
            "precio_unitario": item.precio_unitario,
            "es_regalo_promocion": item.es_regalo_promocion,
            "product": ProductResponse(
                id=product.id,
                nombre=product.nombre,
                categoria=product.categoria,
                marca=product.marca,
                modelo=product.modelo,
                capacidad=product.capacidad,
                condicion=product.condicion,
                precio=product.precio,
                moneda=product.moneda,
                garantia_meses=product.garantia_meses,
                stock_disponible=product.stock.cantidad_disponible if product.stock else 0
            ) if product else None
        })

    return OrderResponse(
        id=order.id,
        profile_id=order.profile_id,
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        canal=order.canal,
        metodo_pago=order.metodo_pago,
        total=order.total,
        estado=order.estado,
        created_at=order.created_at,
        items=items_response
    )

@router.get("", response_model=List[OrderListResponse])
def list_orders(
    profile_slug: Optional[str] = Query(None, description="Filtrar por slug del perfil (ej: 'softmobile')"),
    db: Session = Depends(get_db)
):
    """
    Lista todas las órdenes del sistema.
    
    Args:
        - profile_slug: Filtro opcional por perfil
        
    Returns:
        Lista de órdenes ordenadas por fecha de creación (más recientes primero)
        
    Raises:
        - 404: Si el profile_slug especificado no existe
    """
    query = db.query(Order)
    
    if profile_slug:
        profile = db.query(Profile).filter(Profile.slug == profile_slug).first()
        if not profile:
            raise HTTPException(
                status_code=404, 
                detail=f"El perfil con slug '{profile_slug}' no fue encontrado"
            )
        query = query.filter(Order.profile_id == profile.id)
    
    orders = query.order_by(Order.created_at.desc()).all()
    return orders

@router.post("", response_model=OrderResponse, status_code=201)
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    """
    Crea una nueva orden y descuenta el stock de los productos.
    
    La creación de la orden y el descuento de stock se realizan en una sola transacción
    para garantizar consistencia de datos. Si falla cualquier paso, se revierte toda la operación.
    
    Args:
        - order: Datos de la orden a crear con items y cantidades
        
    Returns:
        Orden creada con todos sus items y detalles
        
    Raises:
        - 404: Si el profile_slug no existe o algún product_id no se encuentra
        - 400: Si no hay stock suficiente para algún producto (indica cuál)
        - 400: Si la orden no contiene items
        - 400: Si el número de teléfono está vacío
    """
    try:
        profile = db.query(Profile).filter(Profile.slug == order.profile_slug).first()
        if not profile:
            raise HTTPException(
                status_code=404, 
                detail=f"El perfil con slug '{order.profile_slug}' no fue encontrado"
            )
        
        if not order.items:
            raise HTTPException(
                status_code=400, 
                detail="La orden debe contener al menos un producto"
            )
        
        customer_phone_str = str(order.customer_phone).strip()
        if not customer_phone_str:
            raise HTTPException(
                status_code=400,
                detail="El número de teléfono del cliente es requerido"
            )
        
        total = Decimal("0.00")
        order_items_data = []
        
        for item in order.items:
            product = db.query(Product).filter(
                Product.id == item.product_id,
                Product.activo == True
            ).first()
            
            if not product:
                raise HTTPException(
                    status_code=404, 
                    detail=f"El producto con ID {item.product_id} no fue encontrado o está inactivo"
                )
            
            stock = db.query(Stock).filter(Stock.product_id == item.product_id).first()
            if not stock:
                raise HTTPException(
                    status_code=400,
                    detail=f"El producto '{product.nombre}' (ID: {product.id}) no tiene stock registrado"
                )
            
            if stock.cantidad_disponible < item.cantidad:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stock insuficiente para '{product.nombre}' (ID: {product.id}). Disponible: {stock.cantidad_disponible}, Solicitado: {item.cantidad}"
                )
            
            precio_unitario = Decimal(str(product.precio))
            subtotal = precio_unitario * item.cantidad
            
            if not item.es_regalo_promocion:
                total += subtotal
            
            order_items_data.append({
                "product": product,
                "stock": stock,
                "cantidad": item.cantidad,
                "precio_unitario": precio_unitario,
                "es_regalo_promocion": item.es_regalo_promocion
            })
        
        db_order = Order(
            profile_id=profile.id,
            customer_name=order.customer_name,
            customer_phone=customer_phone_str,
            canal=order.canal,
            metodo_pago=order.metodo_pago,
            total=total,
            estado="pendiente"
        )
        db.add(db_order)
        db.flush()
        
        db_order_items = []
        for item_data in order_items_data:
            db_order_item = OrderItem(
                order_id=db_order.id,
                product_id=item_data["product"].id,
                cantidad=item_data["cantidad"],
                precio_unitario=item_data["precio_unitario"],
                es_regalo_promocion=item_data["es_regalo_promocion"]
            )
            db.add(db_order_item)
            db_order_items.append(db_order_item)
            
            item_data["stock"].cantidad_disponible -= item_data["cantidad"]
        
        db.commit()
        db.refresh(db_order)
        
        for item in db_order_items:
            db.refresh(item)
        
        return _serialize_order(db_order)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear la orden: {str(e)}"
        )


@router.put("/{order_id}/status", response_model=OrderResponse)
def update_order_status(order_id: int, payload: OrderStatusUpdate, db: Session = Depends(get_db)):
    """
    Actualiza el estado de una orden.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"La orden con ID {order_id} no fue encontrada")

    order.estado = payload.estado

    try:
        db.commit()
        db.refresh(order)
        return _serialize_order(order)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar estado: {str(e)}")


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, updates: OrderUpdate, db: Session = Depends(get_db)):
    """
    Actualiza una orden existente, incluyendo sus items y totales.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"La orden con ID {order_id} no fue encontrada")

    try:
        current_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()

        if updates.items is not None:
            for item in current_items:
                stock = db.query(Stock).filter(Stock.product_id == item.product_id).first()
                if stock:
                    stock.cantidad_disponible += item.cantidad

            if len(updates.items) == 0:
                raise HTTPException(status_code=400, detail="La orden debe contener al menos un producto")

            total = Decimal("0.00")
            db.query(OrderItem).filter(OrderItem.order_id == order_id).delete()

            for item_update in updates.items:
                product = db.query(Product).filter(
                    Product.id == item_update.product_id,
                    Product.activo == True
                ).first()

                if not product:
                    raise HTTPException(status_code=404, detail=f"Producto {item_update.product_id} no encontrado o inactivo")

                stock = db.query(Stock).filter(Stock.product_id == item_update.product_id).first()
                if not stock:
                    raise HTTPException(status_code=400, detail=f"El producto {item_update.product_id} no tiene stock registrado")

                if stock.cantidad_disponible < item_update.cantidad:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Stock insuficiente para '{product.nombre}'. Disponible: {stock.cantidad_disponible}, Solicitado: {item_update.cantidad}"
                    )

                price = Decimal(str(product.precio))
                if not item_update.es_regalo_promocion:
                    total += price * item_update.cantidad

                new_item = OrderItem(
                    order_id=order.id,
                    product_id=item_update.product_id,
                    cantidad=item_update.cantidad,
                    precio_unitario=price,
                    es_regalo_promocion=item_update.es_regalo_promocion
                )
                db.add(new_item)

                stock.cantidad_disponible -= item_update.cantidad

            order.total = total

        if updates.customer_name is not None:
            order.customer_name = updates.customer_name

        if updates.customer_phone is not None:
            phone = str(updates.customer_phone).strip()
            if not phone:
                raise HTTPException(status_code=400, detail="El número de teléfono del cliente es requerido")
            order.customer_phone = phone

        if updates.canal is not None:
            order.canal = updates.canal

        if updates.metodo_pago is not None:
            order.metodo_pago = updates.metodo_pago

        db.commit()
        db.refresh(order)
        return _serialize_order(order)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar la orden: {str(e)}")

@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    """
    Obtiene una orden por su ID con todos sus items y detalles de productos.
    
    Args:
        - order_id: ID de la orden
        
    Returns:
        Orden con items completos y stock actualizado de los productos
        
    Raises:
        - 404: Si la orden no existe
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=404, 
            detail=f"La orden con ID {order_id} no fue encontrada"
        )
    
    items_response = []
    for item in order.items:
        product = item.product
        items_response.append({
            "id": item.id,
            "product_id": item.product_id,
            "cantidad": item.cantidad,
            "precio_unitario": item.precio_unitario,
            "es_regalo_promocion": item.es_regalo_promocion,
            "product": ProductResponse(
                id=product.id,
                nombre=product.nombre,
                categoria=product.categoria,
                marca=product.marca,
                modelo=product.modelo,
                capacidad=product.capacidad,
                condicion=product.condicion,
                precio=product.precio,
                moneda=product.moneda,
                garantia_meses=product.garantia_meses,
                stock_disponible=product.stock.cantidad_disponible if product.stock else 0
            )
        })
    
    return OrderResponse(
        id=order.id,
        profile_id=order.profile_id,
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        canal=order.canal,
        metodo_pago=order.metodo_pago,
        total=order.total,
        estado=order.estado,
        created_at=order.created_at,
        items=items_response
    )
