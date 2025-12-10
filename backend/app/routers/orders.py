from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, date
import math
from app.database import get_db
from app.models import Order, OrderItem, Product, Profile, Stock, SalesProfile, Location
from app.schemas import (
    OrderCreate,
    OrderResponse,
    OrderListResponse,
    ProductResponse,
    OrderStatusUpdate,
    OrderUpdate,
    OrderSearchParams,
    PaginatedResponse
)

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _serialize_product_for_order(product: Product, location_id: Optional[int] = None) -> dict:
    """Serializa un producto para incluirlo en la respuesta de una orden."""
    # V2.0: el stock está distribuido por ubicación; si se conoce la ubicación de origen,
    # se reporta el stock específico, de lo contrario se envía el total consolidado.
    stock_disponible = 0
    if hasattr(product, "stock_items") and product.stock_items:
        if location_id:
            matching_stock = next((s for s in product.stock_items if s.location_id == location_id), None)
            stock_disponible = matching_stock.cantidad_disponible if matching_stock else 0
        else:
            stock_disponible = sum(s.cantidad_disponible for s in product.stock_items)

    return {
        "id": product.id,
        "profile_id": product.profile_id,
        "sku": product.sku,
        "nombre": product.nombre,
        "categoria": product.categoria,
        "marca": product.marca,
        "modelo": product.modelo,
        "capacidad": product.capacidad,
        "condicion": product.condicion,
        "precio": product.precio,
        "moneda": product.moneda,
        "garantia_meses": product.garantia_meses,
        "activo": product.activo,
        "stock_disponible": stock_disponible
    }


def _serialize_order(order: Order) -> OrderResponse:
    """
    Helper function to serialize an Order model to OrderResponse schema.
    
    Args:
        - order: Order model instance
        
    Returns:
        OrderResponse with complete items and product details
    """
    items_response = []
    for item in order.items:
        items_response.append({
            "id": item.id,
            "product_id": item.product_id,
            "cantidad": item.cantidad,
            "precio_unitario": item.precio_unitario,
            "es_regalo_promocion": item.es_regalo_promocion,
            "product": ProductResponse(**_serialize_product_for_order(item.product, order.source_location_id)) if item.product else None
        })

    return OrderResponse(
        id=order.id,
        profile_id=order.profile_id,
        sales_profile_id=order.sales_profile_id,  # V2.0
        source_location_id=order.source_location_id,  # V2.0
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        canal=order.canal,
        metodo_pago=order.metodo_pago,
        total=order.total,
        estado=order.estado,
        notes=order.notes,
        delivery_date=order.delivery_date,
        created_at=order.created_at,
        items=items_response
    )

@router.get("", response_model=PaginatedResponse[OrderResponse])
def list_orders(
    sales_profile_slug: Optional[str] = Query(None, description="Filtrar por canal de venta (ej: 'bot-whatsapp')"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db)
):
    """
    Lista órdenes del sistema con paginación.
    
    V2.0: Filtra por sales_profile_slug (canal de venta: bot, vendedor, etc.)
    
    Args:
        - sales_profile_slug: Filtro opcional por canal de venta
        - page: Número de página (default: 1)
        - per_page: Resultados por página (default: 50, max: 100)
        
    Returns:
        Respuesta paginada con lista de órdenes ordenadas por fecha de creación (más recientes primero)
        
    Raises:
        - 404: Si el sales_profile_slug especificado no existe
    """
    query = db.query(Order)
    
    if sales_profile_slug:
        sales_profile = db.query(SalesProfile).filter(SalesProfile.slug == sales_profile_slug).first()
        if not sales_profile:
            raise HTTPException(
                status_code=404, 
                detail=f"El canal de venta con slug '{sales_profile_slug}' no fue encontrado"
            )
        query = query.filter(Order.sales_profile_id == sales_profile.id)
    
    total = query.count()
    offset = (page - 1) * per_page
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(per_page).all()
    
    # Serializar órdenes con items completos
    serialized_orders = [_serialize_order(order) for order in orders]
    
    return PaginatedResponse(
        items=serialized_orders,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0
    )


@router.post("/search", response_model=PaginatedResponse[OrderResponse])
def search_orders(
    search_params: OrderSearchParams,
    sales_profile_slug: Optional[str] = Query(None, description="Filtrar por canal de venta"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db)
):
    """
    Búsqueda avanzada de órdenes con múltiples filtros y paginación.
    
    V2.0: Filtra por sales_profile_slug (canal de venta).
    
    Permite filtrar por:
    - Rango de fechas
    - Rango de montos
    - Cliente (nombre o teléfono)
    - Producto incluido en la orden
    - Estado de la orden
    
    Args:
        - search_params: Parámetros de búsqueda
        - sales_profile_slug: Filtro opcional por canal de venta
        - page: Número de página (default: 1)
        - per_page: Resultados por página (default: 50, max: 100)
        
    Returns:
        Respuesta paginada con órdenes que coinciden con los criterios
    """
    query = db.query(Order)
    
    # Filter by sales profile (V2.0)
    if sales_profile_slug:
        sales_profile = db.query(SalesProfile).filter(
            SalesProfile.slug == sales_profile_slug,
            SalesProfile.active == True  # Validar que esté activo
        ).first()
        if not sales_profile:
            raise HTTPException(
                status_code=404,
                detail=f"El canal de venta con slug '{sales_profile_slug}' no fue encontrado o está inactivo"
            )
        query = query.filter(Order.sales_profile_id == sales_profile.id)
    
    # Filter by date range
    if search_params.date_from:
        date_from_dt = datetime.combine(search_params.date_from, datetime.min.time())
        query = query.filter(Order.created_at >= date_from_dt)
    
    if search_params.date_to:
        date_to_dt = datetime.combine(search_params.date_to, datetime.max.time())
        query = query.filter(Order.created_at <= date_to_dt)
    
    # Filter by amount range
    if search_params.amount_min is not None:
        query = query.filter(Order.total >= search_params.amount_min)
    
    if search_params.amount_max is not None:
        query = query.filter(Order.total <= search_params.amount_max)
    
    # Filter by customer (name or phone)
    if search_params.customer_query:
        customer_pattern = f"%{search_params.customer_query}%"
        query = query.filter(
            (Order.customer_name.ilike(customer_pattern)) |
            (Order.customer_phone.ilike(customer_pattern))
        )
    
    # Filter by estado
    if search_params.estado:
        query = query.filter(Order.estado == search_params.estado.value)
    
    # Product filter requires special handling (join with order_items)
    if search_params.product_id:
        query = query.join(OrderItem).filter(OrderItem.product_id == search_params.product_id)
    
    total = query.count()
    offset = (page - 1) * per_page
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(per_page).all()
    
    # Serializar órdenes con items completos
    serialized_orders = [_serialize_order(order) for order in orders]
    
    return PaginatedResponse(
        items=serialized_orders,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0
    )


@router.post("", response_model=OrderResponse, status_code=201)
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    """
    Crea una nueva orden y descuenta el stock de los productos.
    
    V2.0: Soporta sales_profile_slug (perfil de venta) y source_location_id (ubicación de stock).
    V1 (Legacy): Usa profile_slug para compatibilidad con sistema antiguo.
    
    Args:
        - order: Datos de la orden con items, perfil de venta y ubicación origen
        
    Returns:
        Orden creada con trazabilidad completa
        
    Raises:
        - 404: Si el sales_profile_slug/profile_slug o source_location_id no existen
        - 400: Si no hay stock suficiente en la ubicación especificada
        - 400: Si la orden no contiene items o el teléfono está vacío
    """
    try:
        # V2.0: Determinar perfil de venta o perfil legacy
        sales_profile = None
        profile = None
        profile_id_for_order = None
        sales_profile_id_for_order = None
        
        if order.sales_profile_slug:
            # V2.0: Usar SalesProfile
            sales_profile = db.query(SalesProfile).filter(
                SalesProfile.slug == order.sales_profile_slug,
                SalesProfile.active == True
            ).first()
            if not sales_profile:
                raise HTTPException(
                    status_code=404, 
                    detail=f"El perfil de venta con slug '{order.sales_profile_slug}' no fue encontrado o está inactivo"
                )
            sales_profile_id_for_order = sales_profile.id
        elif order.profile_slug:
            # V1 Legacy: Usar Profile antiguo
            profile = db.query(Profile).filter(Profile.slug == order.profile_slug).first()
            if not profile:
                raise HTTPException(
                    status_code=404, 
                    detail=f"El perfil con slug '{order.profile_slug}' no fue encontrado"
                )
            profile_id_for_order = profile.id
        else:
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar sales_profile_slug (V2.0) o profile_slug (legacy)"
            )
        
        # V2.0: Validar ubicación de origen del stock (OBLIGATORIO)
        if not order.source_location_id or order.source_location_id <= 0:
            raise HTTPException(
                status_code=400,
                detail="source_location_id es obligatorio en V2.0 y debe ser un ID válido (mayor a 0)"
            )

        source_location = db.query(Location).filter(
            Location.id == order.source_location_id,
            Location.activo == True
        ).first()
        if not source_location:
            raise HTTPException(
                status_code=404,
                detail=f"La ubicación con ID {order.source_location_id} no fue encontrada o está inactiva. Verifique que la ubicación existe y está activa antes de crear la orden."
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
            
            stock = db.query(Stock).filter(
                Stock.product_id == item.product_id,
                Stock.location_id == order.source_location_id
            ).first()
            if not stock:
                raise HTTPException(
                    status_code=400,
                    detail=f"El producto '{product.nombre}' no tiene stock en la ubicación '{source_location.nombre}'"
                )
            
            if stock.cantidad_disponible < item.cantidad:
                location_name = source_location.nombre if source_location else "la ubicación"
                raise HTTPException(
                    status_code=400,
                    detail=f"Stock insuficiente para '{product.nombre}' (SKU: {product.sku}) en {location_name}. Disponible: {stock.cantidad_disponible}, Solicitado: {item.cantidad}. Por favor, ajuste la cantidad o seleccione otra ubicación con stock disponible."
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
        
        # Validar que la orden tenga al menos un item con valor (no solo regalos)
        if total == Decimal("0.00"):
            # Verificar si todos son regalos
            all_gifts = all(item_data["es_regalo_promocion"] for item_data in order_items_data)
            if all_gifts:
                raise HTTPException(
                    status_code=400,
                    detail="La orden debe tener al menos un producto con valor. No se pueden crear órdenes solo con regalos/promociones."
                )
        
        # Crear orden con nuevos campos V2.0
        db_order = Order(
            profile_id=profile_id_for_order,  # Legacy, puede ser None
            sales_profile_id=sales_profile_id_for_order,  # V2.0, puede ser None
            source_location_id=order.source_location_id,  # V2.0, puede ser None
            customer_name=order.customer_name,
            customer_phone=customer_phone_str,
            canal=order.canal,
            metodo_pago=order.metodo_pago,
            total=total,
            estado="pendiente",
            notes=order.notes,
            delivery_date=order.delivery_date
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
            
            # Descontar stock con validación de no negativos
            stock_anterior = item_data["stock"].cantidad_disponible
            stock_nuevo = stock_anterior - item_data["cantidad"]
            
            # CRÍTICO: Validar stock no negativo antes de commit
            if stock_nuevo < 0:
                db.rollback()
                raise HTTPException(
                    status_code=400,
                    detail=f"Error crítico: Stock quedaría negativo para '{item_data['product'].nombre}'. Esto no debería ocurrir después de las validaciones previas."
                )
            
            item_data["stock"].cantidad_disponible = stock_nuevo
            
            # V2.0: Marcar IMEIs como vendidos
            from app.models import StockHistory, ProductIMEI
            
            # Buscar IMEIs disponibles del producto en la ubicación de origen
            imeis_disponibles = db.query(ProductIMEI).filter(
                ProductIMEI.product_id == item_data["product"].id,
                ProductIMEI.location_id == order.source_location_id,
                ProductIMEI.vendido == False
            ).limit(item_data["cantidad"]).all()
            
            # Marcar IMEIs como vendidos y asociar a la orden
            for imei_obj in imeis_disponibles:
                imei_obj.vendido = True
                imei_obj.order_id = db_order.id
            
            # ✅ TRAZABILIDAD: Registrar en historial de stock
            stock_history = StockHistory(
                product_id=item_data["product"].id,
                location_id=order.source_location_id,  # V2.0: Ubicación de donde salió el stock
                tipo_cambio='venta',
                cantidad=-item_data["cantidad"],  # Negativo = salida de stock
                stock_anterior=stock_anterior,
                stock_nuevo=stock_nuevo,
                referencia_id=db_order.id,
                referencia_tipo='order',
                notas=f"Venta a {order.customer_name} - Canal: {order.canal} - IMEIs: {len(imeis_disponibles)} marcados",
                usuario=sales_profile.name if sales_profile else (profile.name if profile else 'Sistema')
            )
            db.add(stock_history)
        
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
    
    IMPORTANTE: No permite cambiar a 'cancelada' - use POST /orders/{order_id}/cancel
    para cancelar órdenes (libera stock e IMEIs correctamente).
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"La orden con ID {order_id} no fue encontrada")

    # Validar que no se intente cancelar usando este endpoint
    if payload.estado == "cancelada":
        raise HTTPException(
            status_code=400,
            detail="No se puede cancelar una orden usando este endpoint. Use POST /orders/{order_id}/cancel para cancelar correctamente (libera stock e IMEIs)."
        )
    
    # Validar que no se cambie el estado de una orden ya cancelada
    if order.estado == "cancelada":
        raise HTTPException(
            status_code=400,
            detail="No se puede cambiar el estado de una orden cancelada"
        )

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
    
    Solo permite actualizar órdenes en estado 'pendiente' o 'por_entregar'.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"La orden con ID {order_id} no fue encontrada")

    # Validar que la orden no esté cancelada o completada
    if order.estado == "cancelada":
        raise HTTPException(
            status_code=400,
            detail="No se puede modificar una orden cancelada"
        )
    
    if order.estado == "completada":
        raise HTTPException(
            status_code=400,
            detail="No se puede modificar una orden completada. Use el proceso de devolución o ajuste."
        )

    try:
        current_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()

        if updates.items is not None:
            # Liberar IMEIs de los items actuales antes de reemplazarlos
            from app.models import ProductIMEI
            for item in current_items:
                # Liberar IMEIs asociados a este item
                imeis_item = db.query(ProductIMEI).filter(
                    ProductIMEI.order_id == order_id,
                    ProductIMEI.product_id == item.product_id,
                    ProductIMEI.vendido == True
                ).all()
                
                for imei_obj in imeis_item:
                    imei_obj.vendido = False
                    imei_obj.order_id = None
                
                # V2.0: Devolver stock a la ubicación de origen
                if order.source_location_id:
                    stock = db.query(Stock).filter(
                        Stock.product_id == item.product_id,
                        Stock.location_id == order.source_location_id
                    ).first()
                else:
                    # Legacy: Sin ubicación específica
                    stock = db.query(Stock).filter(Stock.product_id == item.product_id).first()
                
                if stock:
                    stock.cantidad_disponible += item.cantidad
                    
                    # Registrar en historial de stock
                    from app.models import StockHistory
                    stock_history = StockHistory(
                        product_id=item.product_id,
                        location_id=order.source_location_id,
                        tipo_cambio="devolucion",
                        cantidad=item.cantidad,  # Positivo porque es entrada (devolución)
                        stock_anterior=stock.cantidad_disponible - item.cantidad,
                        stock_nuevo=stock.cantidad_disponible,
                        referencia_id=order.id,
                        referencia_tipo="order_update",
                        notas=f"Actualización de orden #{order.id} - Items removidos/modificados",
                        usuario="Sistema"
                    )
                    db.add(stock_history)

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

                # V2.0: Consultar stock con location_id
                if order.source_location_id:
                    stock = db.query(Stock).filter(
                        Stock.product_id == item_update.product_id,
                        Stock.location_id == order.source_location_id
                    ).first()
                else:
                    # Legacy: Sin ubicación específica
                    stock = db.query(Stock).filter(Stock.product_id == item_update.product_id).first()
                
                if not stock:
                    raise HTTPException(status_code=400, detail=f"El producto {item_update.product_id} no tiene stock registrado en la ubicación especificada")

                # VALIDACIÓN PREVIA: Verificar stock suficiente ANTES de decrementar
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

                # Decrementar stock (ya validado arriba)
                stock_anterior = stock.cantidad_disponible
                stock.cantidad_disponible -= item_update.cantidad
                
                # VALIDACIÓN POST-OPERACIÓN: Detectar race conditions
                if stock.cantidad_disponible < 0:
                    db.rollback()
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error crítico: Stock negativo detectado ({stock.cantidad_disponible}). Posible race condition."
                    )
                
                # TRAZABILIDAD: Registrar cambio de stock en historial
                from app.models import ProductIMEI, StockHistory
                stock_history = StockHistory(
                    product_id=item_update.product_id,
                    location_id=order.source_location_id,
                    tipo_cambio='venta',
                    cantidad=-item_update.cantidad,  # Negativo = salida de stock
                    stock_anterior=stock_anterior,
                    stock_nuevo=stock.cantidad_disponible,
                    referencia_id=order.id,
                    referencia_tipo='order_update',
                    notas=f"Actualización de orden #{order.id} - Item añadido/modificado",
                    usuario='sistema'
                )
                db.add(stock_history)
                
                # V2.0: Marcar IMEIs como vendidos (para la cantidad total del item actualizado)
                imeis_disponibles = db.query(ProductIMEI).filter(
                    ProductIMEI.product_id == item_update.product_id,
                    ProductIMEI.location_id == order.source_location_id,
                    ProductIMEI.vendido == False
                ).limit(item_update.cantidad).all()
                
                # VALIDACIÓN: Verificar que haya suficientes IMEIs si el producto los requiere
                if len(imeis_disponibles) < item_update.cantidad:
                    # Advertencia en logs pero no bloquear (IMEIs son opcionales)
                    print(f"ADVERTENCIA: Solo {len(imeis_disponibles)} IMEIs disponibles de {item_update.cantidad} solicitados para producto {item_update.product_id}")
                
                for imei in imeis_disponibles:
                    imei.vendido = True
                    imei.order_id = order.id

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
        
        if updates.notes is not None:
            order.notes = updates.notes
        
        if updates.delivery_date is not None:
            order.delivery_date = updates.delivery_date

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
    
    return _serialize_order(order)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Cancela una orden y libera los recursos (stock e IMEIs).
    
    V2.0: Operación crítica de negocio que:
    1. Cambia estado de la orden a 'cancelada'
    2. Devuelve el stock a la ubicación de origen
    3. Libera los IMEIs marcándolos como no vendidos
    4. Registra la cancelación en StockHistory
    
    Args:
        - order_id: ID de la orden a cancelar
        - reason: Motivo opcional de la cancelación
        
    Returns:
        Orden actualizada con estado 'cancelada'
        
    Raises:
        - 404: Si la orden no existe
        - 400: Si la orden ya está cancelada o completada
        - 500: Si ocurre un error en la transacción
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=404,
            detail=f"La orden con ID {order_id} no fue encontrada"
        )
    
    # Validar que la orden no esté ya cancelada
    if order.estado == "cancelada":
        raise HTTPException(
            status_code=400,
            detail="La orden ya está cancelada. El stock ya fue devuelto anteriormente."
        )
    
    # Validar que no se cancele una orden completada (debe usar proceso de devolución)
    if order.estado == "completada":
        raise HTTPException(
            status_code=400,
            detail="No se puede cancelar una orden completada. Use el proceso de devolución o ajuste de inventario."
        )
    
    try:
        from app.models import StockHistory, ProductIMEI
        
        print(f"🔄 Cancelando orden {order_id} - Estado actual: {order.estado}")
        print(f"  📋 Orden tiene {len(order.items)} items")
        
        # Procesar cada item de la orden
        for idx, item in enumerate(order.items):
            print(f"  🔢 Item {idx + 1}/{len(order.items)}: Producto {item.product_id}, Cantidad {item.cantidad}")
            
            # 1. Devolver stock a la ubicación de origen
            if order.source_location_id:
                stock = db.query(Stock).filter(
                    Stock.product_id == item.product_id,
                    Stock.location_id == order.source_location_id
                ).first()
                
                if stock:
                    stock_anterior = stock.cantidad_disponible
                    stock.cantidad_disponible += item.cantidad
                    
                    print(f"  📦 Producto {item.product_id}: Stock {stock_anterior} → {stock.cantidad_disponible} (+{item.cantidad})")
                    
                    # Registrar en historial
                    history = StockHistory(
                        product_id=item.product_id,
                        location_id=order.source_location_id,
                        tipo_cambio='devolucion',
                        cantidad=item.cantidad,  # Positivo = entrada
                        stock_anterior=stock_anterior,
                        stock_nuevo=stock.cantidad_disponible,
                        referencia_id=order_id,
                        referencia_tipo='order_cancelled',
                        notas=f"Cancelación de orden #{order_id}: {reason or 'Sin motivo especificado'}",
                        usuario='sistema'  # TODO: Usar usuario autenticado
                    )
                    db.add(history)
            
            # 2. Liberar IMEIs asociados a esta orden
            imeis_vendidos = db.query(ProductIMEI).filter(
                ProductIMEI.order_id == order_id,
                ProductIMEI.product_id == item.product_id,
                ProductIMEI.vendido == True
            ).all()
            
            for imei_obj in imeis_vendidos:
                imei_obj.vendido = False
                imei_obj.order_id = None
        
        # 3. Actualizar estado de la orden PRIMERO (para evitar doble procesamiento)
        old_estado = order.estado
        order.estado = "cancelada"
        if reason:
            order.notes = (order.notes or '') + f" | CANCELADA: {reason}"
        
        # Flush para que el estado se actualice inmediatamente
        db.flush()
        
        print(f"✅ Orden {order_id} cancelada: {old_estado} → cancelada")
        
        db.commit()
        db.refresh(order)
        
        return _serialize_order(order)
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al cancelar la orden: {str(e)}"
        )


@router.delete("/{order_id}", status_code=204)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    """
    Elimina una orden del sistema y repone el stock de los productos.
    
    Esta operación:
    1. Encuentra la orden y sus items
    2. Repone el stock de cada producto
    3. Elimina la orden (los items se eliminan en cascada)
    
    Args:
        - order_id: ID de la orden a eliminar
        
    Returns:
        No content (204)
        
    Raises:
        - 404: Si la orden no existe
        - 500: Si ocurre un error al eliminar
    """
    print(f"🗑️ [DELETE ORDER] Iniciando eliminación de orden {order_id}")
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        print(f"❌ [DELETE ORDER] Orden {order_id} no encontrada")
        raise HTTPException(
            status_code=404,
            detail=f"La orden con ID {order_id} no fue encontrada"
        )
    
    # Advertir si se intenta eliminar orden completada (mejor usar cancelación)
    if order.estado == "completada":
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar una orden completada. Use POST /orders/{order_id}/cancel para cancelar o desactive la orden."
        )
    
    print(f"✅ [DELETE ORDER] Orden {order_id} encontrada, tiene {len(order.items)} items")
    print(f"  📊 Estado de la orden: {order.estado}")
    
    try:
        # Solo devolver stock si la orden NO está cancelada (las canceladas ya devolvieron el stock)
        if order.estado != "cancelada":
            print(f"  ♻️ Devolviendo stock (orden en estado '{order.estado}')")
            # Reponer stock antes de eliminar
            for item in order.items:
                # V2.0: Devolver stock a la ubicación de origen
                if order.source_location_id:
                    stock = db.query(Stock).filter(
                        Stock.product_id == item.product_id,
                        Stock.location_id == order.source_location_id
                    ).first()
                else:
                    # Legacy: Sin ubicación específica
                    stock = db.query(Stock).filter(Stock.product_id == item.product_id).first()
                
                if stock:
                    old_stock = stock.cantidad_disponible
                    stock.cantidad_disponible += item.cantidad
                    print(f"    📦 Producto {item.product_id}: stock {old_stock} -> {stock.cantidad_disponible}")
                
                # Liberar IMEIs asociados a esta orden
                from app.models import ProductIMEI
                imeis_vendidos = db.query(ProductIMEI).filter(
                    ProductIMEI.order_id == order.id,
                    ProductIMEI.product_id == item.product_id,
                    ProductIMEI.vendido == True
                ).all()
                
                for imei_obj in imeis_vendidos:
                    imei_obj.vendido = False
                    imei_obj.order_id = None
                    print(f"    🔓 IMEI {imei_obj.imei} liberado")
        else:
            print(f"  ⏭️  Orden ya cancelada - stock ya fue devuelto, no se vuelve a devolver")
        
        # Eliminar orden (items se eliminan en cascada)
        print(f"🗑️ [DELETE ORDER] Eliminando orden {order_id} de la base de datos...")
        db.delete(order)
        db.commit()
        print(f"✅ [DELETE ORDER] Orden {order_id} eliminada exitosamente")
        return None
    except Exception as e:
        print(f"❌ [DELETE ORDER] Error al eliminar orden {order_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar orden: {str(e)}")
