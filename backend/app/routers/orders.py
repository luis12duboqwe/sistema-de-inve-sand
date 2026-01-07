from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, date
import math
import json
from app.database import get_db
from app.models import Order, OrderItem, Product, Profile, Stock, SalesProfile, Location, TradeIn, ProductIMEI, StockHistory, IMEIHistory, Bank, FinancingOption, InteractionLog, Customer, User
from app.schemas import (
    OrderCreate,
    OrderResponse,
    OrderListResponse,
    ProductResponse,
    OrderStatusUpdate,
    OrderUpdate,
    OrderItemUpdate,
    OrderSearchParams,
    PaginatedResponse,
    TradeInResponse
)
from app.auth import get_current_active_user, get_current_user_optional, check_permission
from app.services.order_service import OrderService, resolve_user_label
from app.services.stock_transaction_helper import (
    PreparedSaleItem,
    StockTransactionHelper,
)
from app.utils.order_financing import recompute_financing_from_details
from app.utils.order_queries import resolve_sales_profile_for_query
from app.utils.order_tradeins import compute_trade_in_total
from app.utils.order_validators import (
    resolve_sales_profile,
    validate_location_and_phone,
    validate_location_exists,
    normalize_customer_phone,
)
from app.utils.stock_manager import StockManager, StockValidationError

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _serialize_product_for_order(product: Product, location_id: Optional[int] = None) -> dict:
    """Serializa un producto para incluirlo en la respuesta de una orden."""
    # V2.0: el stock está distribuido por ubicación; si se conoce la ubicación de origen,
    # se reporta el stock específico, de lo contrario se envía el total consolidado.
    stock_disponible = 0
    if hasattr(product, "stock_items") and product.stock_items:
        if location_id:
            matching_stock = next((s for s in product.stock_items if s.location_id == location_id), None)
            if matching_stock:
                reservado = matching_stock.cantidad_reservada or 0
                stock_libre = (matching_stock.cantidad_disponible or 0) - reservado
                stock_disponible = max(stock_libre, 0)
            else:
                stock_disponible = 0
        else:
            total = 0
            for s in product.stock_items:
                reservado = s.cantidad_reservada or 0
                stock_libre = (s.cantidad_disponible or 0) - reservado
                total += max(stock_libre, 0)
            stock_disponible = total

    return {
        "id": product.id,
        "profile_id": product.profile_id,
        "sku": product.sku,
        "nombre": product.nombre,
        "categoria": product.categoria,
        "marca": product.marca,
        "modelo": product.modelo,
        "color": product.color,
        "capacidad": product.capacidad,
        "condicion": product.condicion,
        "precio": product.precio,
        "costo": product.costo,
        "moneda": product.moneda,
        "garantia_meses": product.garantia_meses,
        "activo": product.activo,
        "is_serialized": product.is_serialized,
        "stock_disponible": stock_disponible,
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
        # V2.0: Incluir IMEIs vendidos en este item
        imeis_list = []
        if hasattr(order, 'imeis_vendidos'):
             # Filtrar imeis_vendidos por product_id
             imeis_list = [i.imei for i in order.imeis_vendidos if i.product_id == item.product_id]

        items_response.append({
            "id": item.id,
            "product_id": item.product_id,
            "cantidad": item.cantidad,
            "precio_unitario": item.precio_unitario,
            "es_regalo_promocion": item.es_regalo_promocion,
            "product": ProductResponse(**_serialize_product_for_order(item.product, order.source_location_id)) if item.product else None,
            "imeis": imeis_list if imeis_list else None
        })

    trade_ins_response = []
    if order.trade_ins:
        for trade_in in order.trade_ins:
            trade_ins_response.append(TradeInResponse.model_validate(trade_in))

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
        financing_details=order.financing_details,  # V2.1: Incluir detalles de financiamiento
        estado=order.estado,
        notes=order.notes,
        delivery_date=order.delivery_date,
        created_at=order.created_at,
        items=items_response,
        trade_ins=trade_ins_response
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
    sales_profile = resolve_sales_profile_for_query(db, sales_profile_slug)
    if sales_profile:
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
    sales_profile = resolve_sales_profile_for_query(db, sales_profile_slug, require_active=True)
    if sales_profile:
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
def create_order(
    order: OrderCreate, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Crea una orden usando OrderService para centralizar la lógica V2.0."""
    service = OrderService(db)
    created_order = service.create_order(order, current_user=current_user)
    return _serialize_order(created_order)


@router.put("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int, 
    payload: OrderStatusUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("orders:edit"))
):
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
def update_order(
    order_id: int, 
    updates: OrderUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("orders:edit"))
):
    """
    Actualiza una orden existente con transaccionalidad garantizada (Bug #1 fix).
    
    Solo permite actualizar órdenes en estado 'pendiente' o 'por_entregar'.
    GARANTIZA: Todas las validaciones ANTES de cualquier modificación.
    """
    try:
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

        user_identifier = resolve_user_label(current_user)

        # 🔒 BUG #1 FIX: Obtener snapshot de items antiguos PRIMERO
        # StockHistory y ProductIMEI ya están importados globalmente
        current_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()

        items_total = None  # Usado para recalcular total + financiamiento

        # Determinar la ubicación de origen para los nuevos items
        # Si se actualiza la ubicación, usar la nueva; de lo contrario, usar la actual
        target_location_id = order.source_location_id
        if hasattr(updates, 'source_location_id') and updates.source_location_id:
            new_location = validate_location_exists(db, updates.source_location_id)
            target_location_id = new_location.id

        if updates.items is not None:
            # Liberar IMEIs de los items actuales antes de reemplazarlos
            # ProductIMEI ya está importado globalmente
            stock_manager = StockManager(db)
            stock_helper = StockTransactionHelper(db, stock_manager=stock_manager)
            
            for item in current_items:
                # Liberar IMEIs asociados a este item
                imeis_item = db.query(ProductIMEI).filter(
                    ProductIMEI.order_id == order_id,
                    ProductIMEI.product_id == item.product_id,
                    ProductIMEI.vendido == True
                ).all()
                
                if imeis_item:
                    stock_manager.release_imeis(
                        imeis=imeis_item,
                        notes=f"Actualización de orden #{order.id} - Items removidos",
                        user_id=user_identifier
                    )
                
                # V2.0: Devolver stock a la ubicación de origen
                if order.source_location_id:
                    stock_manager.increase_stock(
                        product_id=item.product_id,
                        location_id=order.source_location_id,
                        quantity=item.cantidad,
                        operation_type="devolucion",
                        notes=f"Actualización de orden #{order.id} - Items removidos/modificados",
                            user_id=user_identifier,
                        create_if_missing=True
                    )
                else:
                    # Legacy: Sin ubicación específica - Mantener lógica manual limitada
                    stock = db.query(Stock).filter(Stock.product_id == item.product_id).first()
                    if stock:
                        stock.cantidad_disponible += item.cantidad
                        # Registrar historial manual (legacy)
                        stock_history = StockHistory(
                            product_id=item.product_id,
                            location_id=None,
                            tipo_cambio="devolucion",
                            cantidad=item.cantidad,
                            stock_anterior=stock.cantidad_disponible - item.cantidad,
                            stock_nuevo=stock.cantidad_disponible,
                            referencia_id=order.id,
                            referencia_tipo="order_update",
                            notas=f"Actualización de orden #{order.id} (Legacy)",
                                usuario=user_identifier
                        )
                        db.add(stock_history)

            if len(updates.items) == 0:
                raise HTTPException(status_code=400, detail="La orden debe contener al menos un producto")

            if not target_location_id:
                raise HTTPException(status_code=400, detail="No se puede actualizar una orden legacy sin ubicación de origen en V2.0")

            # Borrar items existentes y recalcular con helper centralizado
            db.query(OrderItem).filter(OrderItem.order_id == order_id).delete()

            prepared_items: List[PreparedSaleItem]
            total, prepared_items = stock_helper.prepare_sale_items(
                items_payload=updates.items,
                location_id=target_location_id,
                allow_pending_imei=False
            )

            for item_data in prepared_items:
                if item_data.imeis_to_sell:
                    stock_manager.mark_imeis_as_sold(
                        imeis=item_data.imeis_to_sell,
                        order_id=order.id,
                        notes=f"Venta en actualización de orden #{order.id}",
                        user_id=user_identifier
                    )

                new_item = OrderItem(
                    order_id=order.id,
                    product_id=item_data.product.id,
                    cantidad=item_data.cantidad,
                    precio_unitario=item_data.precio_unitario,
                    es_regalo_promocion=item_data.es_regalo_promocion
                )
                db.add(new_item)

                try:
                    stock_manager.decrease_stock(
                        stock=item_data.stock,
                        quantity=item_data.cantidad,
                        operation_type="venta",
                        notes=f"Actualización de orden #{order.id} - Item añadido/modificado",
                        user_id=user_identifier,
                        order_id=order.id
                    )
                except StockValidationError as e:
                    db.rollback()
                    raise HTTPException(status_code=409, detail=str(e))

            items_total = total

        if updates.customer_name is not None:
            order.customer_name = updates.customer_name

        if updates.customer_phone is not None:
            order.customer_phone = normalize_customer_phone(updates.customer_phone)

        if updates.canal is not None:
            order.canal = updates.canal

        if updates.metodo_pago is not None:
            order.metodo_pago = updates.metodo_pago
        
        if updates.notes is not None:
            order.notes = updates.notes
        
        if updates.delivery_date is not None:
            order.delivery_date = updates.delivery_date
        
        # Actualizar source_location_id si cambió (ya validado al inicio)
        if hasattr(updates, 'source_location_id') and updates.source_location_id:
            order.source_location_id = updates.source_location_id

        # Recalcular total considerando trade-ins y financiamiento existentes
        if items_total is not None:
            trade_in_total = compute_trade_in_total(order.trade_ins)

            total_after_tradeins = items_total - trade_in_total
            if total_after_tradeins < 0:
                total_after_tradeins = Decimal("0.00")

            total_final, recomputed_financing = recompute_financing_from_details(
                financing_details=order.financing_details,
                metodo_pago=order.metodo_pago,
                total_after_tradeins=total_after_tradeins,
            )

            if recomputed_financing is not None:
                order.total = total_final
                order.financing_details = recomputed_financing
            else:
                order.total = total_after_tradeins
                order.financing_details = None if order.metodo_pago not in ['tarjeta', 'financiamiento'] else order.financing_details

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
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("orders:edit"))
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
    # V2.0 FIX: Permitimos cancelar órdenes completadas para facilitar correcciones
    # if order.estado == "completada":
    #     raise HTTPException(
    #         status_code=400,
    #         detail="No se puede cancelar una orden completada. Use el proceso de devolución o ajuste de inventario."
    #     )
    
    try:
        # StockHistory y ProductIMEI ya están importados globalmente
        
        print(f"🔄 Cancelando orden {order_id} - Estado actual: {order.estado}")
        print(f"  📋 Orden tiene {len(order.items)} items")
        
        # Inicializar StockManager
        stock_manager = StockManager(db)
        user_identifier = resolve_user_label(current_user)
        
        # Procesar cada item de la orden
        for idx, item in enumerate(order.items):
            print(f"  🔢 Item {idx + 1}/{len(order.items)}: Producto {item.product_id}, Cantidad {item.cantidad}")
            
            # 1. Devolver stock a la ubicación de origen
            if order.source_location_id:
                stock_manager.increase_stock(
                    product_id=item.product_id,
                    location_id=order.source_location_id,
                    quantity=item.cantidad,
                    operation_type="devolucion",
                    notes=f"Cancelación de orden #{order_id}: {reason or 'Sin motivo especificado'}",
                    user_id=user_identifier,
                    create_if_missing=True
                )
            
            # 2. Liberar IMEIs asociados a esta orden
            imeis_vendidos = db.query(ProductIMEI).filter(
                ProductIMEI.order_id == order_id,
                ProductIMEI.product_id == item.product_id,
                ProductIMEI.vendido == True
            ).all()
            
            if imeis_vendidos:
                stock_manager.release_imeis(
                    imeis=imeis_vendidos,
                    notes=f"Cancelación de orden #{order_id}",
                        user_id=user_identifier
                )

        # Revertir retomas ingresadas automáticamente al crear la orden
        if order.trade_ins:
            for trade_in in order.trade_ins:
                target_product = None
                stock_entry = None
                imei_record = None

                # Primero intentar localizar por IMEI
                if trade_in.imei:
                    imei_record = db.query(ProductIMEI).filter(ProductIMEI.imei == trade_in.imei).first()
                    if imei_record:
                        target_product = imei_record.product
                        stock_entry = db.query(Stock).filter(
                            Stock.product_id == imei_record.product_id,
                            Stock.location_id == order.source_location_id
                        ).with_for_update().first()

                # Fallback: buscar producto por características (retoma recién creada)
                if not target_product:
                    query_product = db.query(Product).filter(
                        Product.marca == trade_in.marca,
                        Product.modelo == trade_in.modelo,
                        Product.condicion == trade_in.condicion
                    )
                    if trade_in.color:
                        query_product = query_product.filter(Product.color == trade_in.color)
                    if trade_in.capacidad:
                        query_product = query_product.filter(Product.capacidad == trade_in.capacidad)

                    target_product = query_product.first()
                    if target_product:
                        stock_entry = db.query(Stock).filter(
                            Stock.product_id == target_product.id,
                            Stock.location_id == order.source_location_id
                        ).with_for_update().first()

                # Ajustar stock de la retoma
                if target_product and stock_entry and stock_entry.cantidad_disponible > 0:
                    try:
                        stock_manager.decrease_stock(
                            stock=stock_entry,
                            quantity=1,
                            operation_type="retoma_cancelada",
                            notes=f"Reversa de retoma para orden #{order_id}",
                            user_id=user_identifier,
                            order_id=order_id
                        )
                    except StockValidationError:
                        # Si falla por reservas u otro motivo, loguear y continuar (no bloquear cancelación)
                        print(f"⚠️ No se pudo revertir stock de retoma para producto {target_product.id}")

                # Eliminar IMEI ingresado por la retoma (si se creó)
                if imei_record:
                    imei_history_cancel = IMEIHistory(
                        imei=imei_record.imei,
                        product_id=imei_record.product_id,
                        location_id=order.source_location_id,
                        event_type='retoma_cancelada',
                        reference_id=order_id,
                        reference_type='order_cancelled',
                        notes=f"IMEI revertido por cancelación de orden #{order_id}",
                        created_by=user_identifier
                    )
                    db.add(imei_history_cancel)
                    db.delete(imei_record)

                # Desactivar producto de retoma sin stock (solo para RET-*)
                if target_product:
                    total_stock = sum((s.cantidad_disponible or 0) for s in db.query(Stock).filter(Stock.product_id == target_product.id).all())
                    if total_stock == 0 and target_product.sku and target_product.sku.startswith('RET-'):
                        target_product.activo = False
        
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

                # Crear el registro de stock si fue eliminado accidentalmente (solo cuando hay ubicación)
                if not stock:
                    if order.source_location_id:
                        stock = Stock(
                            product_id=item.product_id,
                            location_id=order.source_location_id,
                            cantidad_disponible=0,
                            cantidad_reservada=0
                        )
                        db.add(stock)
                        db.flush()
                        old_stock = 0
                    else:
                        # No hay ubicación (legacy) y tampoco registro de stock; no se puede reponer
                        old_stock = 0
                        stock = None
                else:
                    old_stock = stock.cantidad_disponible

                if stock:
                    stock.cantidad_disponible += item.cantidad
                    print(f"    📦 Producto {item.product_id}: stock {old_stock} -> {stock.cantidad_disponible}")
                
                # Liberar IMEIs asociados a esta orden
                # ProductIMEI ya está importado globalmente
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
