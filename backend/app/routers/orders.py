import logging
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
from app.auth import check_permission, get_current_active_user
from app.services.order_service import OrderService, resolve_user_label
from app.services.order_service import normalize_transfer_reference, ensure_unique_transfer_reference
from app.services.stock_transaction_helper import (
    PreparedSaleItem,
    StockTransactionHelper,
)
# from app.services.notification_service import NotificationService
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


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _serialize_product_for_order(product: Product, location_id: Optional[int] = None) -> dict:
    """Serializa un producto para incluirlo en la respuesta de una orden."""
    from app.routers.products import _serialize_product
    response = _serialize_product(product)
    
    # Adapt to structure expected without crashing
    payload = response.model_dump()
    return payload


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
            "costo_unitario": getattr(item, "costo_unitario", None),
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
        transfer_bank_name=order.transfer_bank_name,
        transfer_reference=order.transfer_reference,
        total=order.total,
        financing_details=order.financing_details,  # V2.1: Incluir detalles de financiamiento
        estado=order.estado,
        notes=order.notes,
        delivery_date=order.delivery_date,
        created_at=order.created_at,
        items=items_response,
        trade_ins=trade_ins_response
    )


def _emit_trade_in_alert_notification(
    db: Session,
    *,
    order_id: int,
    alerts: List[str],
    location_id: Optional[int],
    trade_in_ids: List[int],
) -> None:
    """Registra una notificación del sistema si hay incidencias con retomas."""
    if not alerts:
        return

    # notification_service = NotificationService(db)
#     metadata = {
#         "order_id": order_id,
#         "location_id": location_id,
#         "alerts": alerts,
#         "trade_in_ids": trade_in_ids,
#     }
# 
#     try:
#         notification_service.create(
#             type="trade_in_issue",
#             title="Incidencias al revertir retomas",
#             message=(
#                 f"Se detectaron problemas al revertir las retomas de la orden #{order_id}. "
#                 "Revisa el historial de notas para más detalles."
#             ),
#             severity="warning",
#             source="orders",
#             metadata=metadata,
#         )
#         db.commit()
#     except Exception:
        db.rollback()
        logger.exception(
            "No se pudo registrar la notificación de retomas para la orden %s",
            order_id,
        )

@router.get("", response_model=PaginatedResponse[OrderResponse], dependencies=[Depends(check_permission("orders:view"))])
def list_orders(
    sales_profile_slug: Optional[str] = Query(None, description="Filtrar por canal de venta (ej: 'bot-whatsapp')"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("orders:view")),
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


@router.post("/search", response_model=PaginatedResponse[OrderResponse], dependencies=[Depends(check_permission("orders:view"))])
def search_orders(
    search_params: OrderSearchParams,
    sales_profile_slug: Optional[str] = Query(None, description="Filtrar por canal de venta"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("orders:view")),
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


@router.post("", response_model=OrderResponse, status_code=201, dependencies=[Depends(check_permission("orders:create"))])
def create_order(
    order: OrderCreate, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(check_permission("orders:create"))
):
    """Crea una orden usando OrderService para centralizar la lógica V2.0."""
    service = OrderService(db)
    created_order = service.create_order(order, current_user=current_user)
    return _serialize_order(created_order)


@router.put("/{order_id}/status", response_model=OrderResponse, dependencies=[Depends(check_permission("orders:edit"))])
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
    except Exception as exc:
        db.rollback()
        logger.exception("Error al actualizar estado de la orden %s", order_id)
        raise HTTPException(
            status_code=500,
            detail="Error interno al actualizar el estado de la orden. Intente nuevamente o contacte al administrador."
        )


@router.put("/{order_id}", response_model=OrderResponse, dependencies=[Depends(check_permission("orders:edit"))])
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
                    costo_unitario=getattr(item_data.product, 'costo', Decimal('0.00')) or Decimal('0.00'),
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

        if hasattr(updates, 'transfer_bank_name') and updates.transfer_bank_name is not None:
            order.transfer_bank_name = updates.transfer_bank_name.strip() or None

        if hasattr(updates, 'transfer_reference') and updates.transfer_reference is not None:
            order.transfer_reference = updates.transfer_reference.strip() or None

        # Validación anti-fraude para transferencias
        if order.metodo_pago == "transferencia":
            if not order.transfer_bank_name:
                raise HTTPException(
                    status_code=400,
                    detail="Debe indicar el banco cuando el método de pago es transferencia"
                )
            if not order.transfer_reference:
                raise HTTPException(
                    status_code=400,
                    detail="Debe indicar el número de referencia cuando el método de pago es transferencia"
                )

            normalized_reference = normalize_transfer_reference(order.transfer_reference)
            if not normalized_reference:
                raise HTTPException(
                    status_code=400,
                    detail="El número de referencia de transferencia no es válido"
                )

            ensure_unique_transfer_reference(
                db,
                normalized_reference,
                exclude_order_id=order.id,
            )
            order.transfer_reference_normalized = normalized_reference
        else:
            order.transfer_bank_name = None
            order.transfer_reference = None
            order.transfer_reference_normalized = None
        
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
    except Exception as exc:
        db.rollback()
        logger.exception("Error al actualizar la orden %s", order_id)
        raise HTTPException(
            status_code=500,
            detail="Error interno al actualizar la orden. Intente nuevamente o contacte al administrador."
        )

@router.get("/{order_id}", response_model=OrderResponse, dependencies=[Depends(check_permission("orders:view"))])
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("orders:view"))
):
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


@router.post("/{order_id}/cancel", response_model=OrderResponse, dependencies=[Depends(check_permission("orders:edit"))])
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
    
    # V2.0 FIX: Permitimos cancelar órdenes completadas para facilitar correcciones
    
    try:
        # StockHistory y ProductIMEI ya están importados globalmente
        
        logger.info("Cancelando orden %s - estado actual: %s", order_id, order.estado)
        logger.debug("Orden %s tiene %s items", order_id, len(order.items))
        
        # Inicializar StockManager
        stock_manager = StockManager(db)
        user_identifier = resolve_user_label(current_user)
        
        # Procesar cada item de la orden
        for idx, item in enumerate(order.items):
            logger.debug(
                "Procesando item %s/%s de la orden %s (producto %s, cantidad %s)",
                idx + 1,
                len(order.items),
                order_id,
                item.product_id,
                item.cantidad
            )
            
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

        trade_in_alerts: List[str] = []

        # Revertir retomas ingresadas automáticamente al crear la orden
        if order.trade_ins:
            def _register_trade_in_alert(
                message: str,
                trade_in_obj: TradeIn,
                product_id: Optional[int] = None,
                stock_entry: Optional[Stock] = None,
            ) -> None:
                logger.warning(message)
                trade_in_alerts.append(message)
                if trade_in_obj:
                    prefix = " | " if trade_in_obj.notas else ""
                    trade_in_obj.notas = f"{trade_in_obj.notas or ''}{prefix}{message}"

                if product_id:
                    stock_before = int(stock_entry.cantidad_disponible) if stock_entry else 0
                    stock_history = StockHistory(
                        product_id=product_id,
                        location_id=order.source_location_id,
                        tipo_cambio="retoma_alerta",
                        cantidad=0,
                        stock_anterior=stock_before,
                        stock_nuevo=stock_before,
                        referencia_id=order_id,
                        referencia_tipo="order_cancellation",
                        notas=message,
                        usuario=user_identifier,
                    )
                    db.add(stock_history)

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

                can_adjust_stock = True
                if not target_product:
                    _register_trade_in_alert(
                        message=(
                            f"No se encontró producto coincidente para la retoma #{trade_in.id} "
                            f"al cancelar la orden {order_id}."
                        ),
                        trade_in_obj=trade_in,
                    )
                    can_adjust_stock = False
                elif not stock_entry or stock_entry.cantidad_disponible <= 0:
                    _register_trade_in_alert(
                        message=(
                            f"Sin stock disponible para revertir la retoma #{trade_in.id} del producto {target_product.id} "
                            f"al cancelar la orden {order_id}."
                        ),
                        trade_in_obj=trade_in,
                        product_id=target_product.id,
                        stock_entry=stock_entry,
                    )
                    can_adjust_stock = False

                # Ajustar stock de la retoma
                if can_adjust_stock:
                    try:
                        stock_manager.decrease_stock(
                            stock=stock_entry,
                            quantity=1,
                            operation_type="retoma_cancelada",
                            notes=f"Reversa de retoma para orden #{order_id}",
                            user_id=user_identifier,
                            order_id=order_id
                        )
                    except StockValidationError as exc:
                        logger.error(f"ERROR CRÍTICO EN RETOMA: Falló reversión de stock para orden #{order_id}. Exception: {exc}")
                        warning_msg = (
                            f"No se pudo revertir stock de retoma para producto {target_product.id}"
                            f" al cancelar la orden {order_id}: {exc}"
                        )
                        _register_trade_in_alert(
                            message=warning_msg,
                            trade_in_obj=trade_in,
                            product_id=target_product.id,
                            stock_entry=stock_entry,
                        )

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
        
        if trade_in_alerts:
            alert_text = " || ".join(trade_in_alerts)
            note_prefix = "ADVERTENCIA RETOMA: "
            order.notes = (order.notes + " | " if order.notes else "") + note_prefix + alert_text

        # 3. Actualizar estado de la orden PRIMERO (para evitar doble procesamiento)
        old_estado = order.estado
        order.estado = "cancelada"
        if reason:
            order.notes = (order.notes or '') + f" | CANCELADA: {reason}"
        
        # Flush para que el estado se actualice inmediatamente
        db.flush()
        
        logger.info("Orden %s cancelada: %s -> cancelada", order_id, old_estado)
        
        db.commit()
        db.refresh(order)

        if trade_in_alerts:
            trade_in_ids = [
                trade_in.id
                for trade_in in (order.trade_ins or [])
                if getattr(trade_in, "id", None)
            ]
            _emit_trade_in_alert_notification(
                db,
                order_id=order.id,
                alerts=trade_in_alerts.copy(),
                location_id=order.source_location_id,
                trade_in_ids=trade_in_ids,
            )
        
        return _serialize_order(order)
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Error al cancelar la orden %s", order_id)
        raise HTTPException(
            status_code=500,
            detail="Error interno al cancelar la orden. Intente nuevamente o contacte al administrador."
        )


@router.delete("/{order_id}", status_code=204, dependencies=[Depends(check_permission("orders:delete"))])
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("orders:edit"))
):
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
    logger.info("Iniciando eliminación de la orden %s", order_id)
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        logger.error("Orden %s no encontrada al intentar eliminarla", order_id)
        raise HTTPException(
            status_code=404,
            detail=f"La orden con ID {order_id} no fue encontrada"
        )
    
    # En V2.0 la eliminación directa está prohibida salvo que ya esté cancelada
    if order.estado != "cancelada":
        raise HTTPException(
            status_code=400,
            detail="Elimina solo órdenes ya canceladas. Usa POST /orders/{order_id}/cancel para cancelar y liberar stock/IMEIs."
        )
    
    logger.info(
        "Orden %s encontrada para eliminación; contiene %s items",
        order_id,
        len(order.items)
    )
    logger.debug("Estado actual de la orden %s: %s", order_id, order.estado)
    
    try:
        # Eliminar orden (items se eliminan en cascada). No se toca stock/IMEIs porque la
        # cancelación previa ya devolvió todo mediante StockManager.
        logger.info("Eliminando orden %s de la base de datos (ya cancelada)", order_id)
        db.delete(order)
        db.commit()
        logger.info("Orden %s eliminada exitosamente", order_id)
        return None
    except Exception as exc:
        logger.exception("Error al eliminar la orden %s", order_id)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Error interno al eliminar la orden. Intente nuevamente o contacte al administrador."
        )
