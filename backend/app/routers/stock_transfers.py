from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import List, Optional
from datetime import UTC, datetime

from app.database import get_db
from app.models import StockTransfer, Product, Location, Stock, StockHistory, IMEIHistory, User
from app.schemas import (
    StockTransferCreate,
    StockTransferResponse,
    StockTransferConfirm,
    StockTransferReject,
    PaginatedResponse
)

from app.auth import get_current_active_user, check_permission
from app.utils.stock_manager import StockManager, StockValidationError
from app.utils.order_validators import validate_product_exists, validate_location_exists

router = APIRouter(prefix="/api/stock-transfers", tags=["stock_transfers"])

def _serialize_transfer(transfer: StockTransfer) -> StockTransferResponse:
    """Serializa una transferencia de stock con información adicional de ubicaciones V2.0"""
    return StockTransferResponse(
        id=transfer.id,
        product_id=transfer.product_id,
        from_location_id=transfer.from_location_id,
        to_location_id=transfer.to_location_id,
        from_profile_id=transfer.from_profile_id,  # Legacy, puede ser None
        to_profile_id=transfer.to_profile_id,  # Legacy, puede ser None
        cantidad=transfer.cantidad,
        notas=transfer.notas,
        estado=transfer.estado,
        confirmed_at=transfer.confirmed_at,
        confirmed_by=transfer.confirmed_by,
        rejection_reason=transfer.rejection_reason,
        created_at=transfer.created_at,
        created_by=transfer.created_by,
        product_nombre=transfer.product.nombre if transfer.product else None,
        product_sku=transfer.product.sku if transfer.product else None,
        from_location_name=transfer.from_location.nombre if transfer.from_location else None,
        to_location_name=transfer.to_location.nombre if transfer.to_location else None,
        # Legacy V1
        from_profile_name=transfer.from_profile.name if transfer.from_profile else None,
        to_profile_name=transfer.to_profile.name if transfer.to_profile else None,
        imeis=[imei.imei for imei in transfer.imeis_en_transito] if transfer.imeis_en_transito else []
    )


@router.post("", response_model=StockTransferResponse, status_code=201)
def create_transfer(
    transfer: StockTransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Crea una nueva transferencia de stock entre ubicaciones físicas (V2.0).
    
    La transferencia se crea en estado PENDIENTE y debe ser confirmada para mover el stock.
    
    Validaciones:
    - El producto debe existir
    - Las ubicaciones de origen y destino deben existir, estar activas y ser diferentes
    - Debe haber stock suficiente en la ubicación de origen
    
    Args:
        transfer: Datos de la transferencia (product_id, from_location_id, to_location_id, cantidad)
    
    Returns:
        Transferencia creada en estado PENDIENTE
        
    Raises:
        - 404: Si el producto o ubicaciones no existen
        - 400: Si las ubicaciones son iguales o no hay stock suficiente
    """
    # ✅ Validar cantidad > 0 (Bug #31 fix)
    if not transfer.cantidad or transfer.cantidad <= 0:
        raise HTTPException(
            status_code=400,
            detail="La cantidad a transferir debe ser mayor a 0"
        )
    
    # Validar ubicaciones
    from_location = validate_location_exists(db, transfer.from_location_id)
    to_location = validate_location_exists(db, transfer.to_location_id)
    
    if from_location.id == to_location.id:
        raise HTTPException(
            status_code=400,
            detail="No se puede transferir stock a la misma ubicación"
        )
    
    # Validar producto
    product = validate_product_exists(db, transfer.product_id)
    
    # Inicializar StockManager
    stock_manager = StockManager(db)
    
    try:
        # Validar y bloquear stock en origen
        # Nota: validate_and_lock_stock retorna (product, stock, imeis_found)
        # Si el producto es serializado, imeis_found contendrá los objetos ProductIMEI
        _, source_stock, imeis_to_reserve = stock_manager.validate_and_lock_stock(
            product_id=transfer.product_id,
            location_id=transfer.from_location_id,
            quantity=transfer.cantidad,
            imeis_requested=transfer.imeis if product.is_serialized else None,
            allow_pending_imei=False, # Transferencias requieren IMEIs físicos
            operation_type="transfer_out"
        )
    except StockValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Crear la transferencia en estado PENDIENTE
    db_transfer = StockTransfer(
        product_id=product.id,
        from_location_id=from_location.id,
        to_location_id=to_location.id,
        cantidad=transfer.cantidad,
        notas=transfer.notas,
        estado="pendiente",
        created_by=current_user.username
    )
    db.add(db_transfer)
    db.flush() # Obtener ID
    
    # Reservar Stock
    try:
        stock_manager.reserve_stock(
            stock=source_stock,
            quantity=transfer.cantidad,
            transfer_id=db_transfer.id,
            notes=f"Stock reservado para transferencia a '{to_location.nombre}': {transfer.notas or 'Sin notas'}",
            user_id=current_user.username
        )
        
        # Reservar IMEIs
        if imeis_to_reserve:
            stock_manager.reserve_imeis(imeis_to_reserve, db_transfer.id)
            
        db.commit()
        db.refresh(db_transfer)
        return _serialize_transfer(db_transfer)
    except StockValidationError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear la transferencia: {str(e)}"
        )


@router.get("", response_model=PaginatedResponse[StockTransferResponse], dependencies=[Depends(check_permission("inventory:view"))])
def list_transfers(
    location_id: Optional[int] = Query(None, description="Filtrar por ubicación (origen o destino)"),
    product_id: Optional[int] = Query(None, description="Filtrar por ID de producto"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db)
):
    """
    Lista las transferencias de stock con filtros opcionales.
    
    V2.0: Transferencias entre ubicaciones físicas (tiendas/bodegas).
    
    Parámetros:
    - location_id: Filtrar transferencias donde la ubicación sea origen o destino
    - product_id: Filtrar transferencias de un producto específico
    - page: Número de página para paginación
    - per_page: Cantidad de resultados por página
    """
    query = db.query(StockTransfer)
    
    # Filtro por ubicación (V2.0)
    if location_id:
        query = query.filter(
            or_(
                StockTransfer.from_location_id == location_id,
                StockTransfer.to_location_id == location_id
            )
        )
    
    # Filtro por producto
    if product_id:
        query = query.filter(StockTransfer.product_id == product_id)
    
    # Ordenar por más recientes primero
    query = query.order_by(desc(StockTransfer.created_at))
    
    # Paginación
    total = query.count()
    pages = (total + per_page - 1) // per_page
    
    transfers = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return PaginatedResponse(
        items=[_serialize_transfer(t) for t in transfers],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.get("/{transfer_id}", response_model=StockTransferResponse)
def get_transfer(
    transfer_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene los detalles de una transferencia específica.
    """
    transfer = db.query(StockTransfer).filter(
        StockTransfer.id == transfer_id
    ).first()
    
    if not transfer:
        raise HTTPException(
            status_code=404,
            detail=f"Transferencia con ID {transfer_id} no encontrada"
        )
    
    return _serialize_transfer(transfer)


@router.post("/{transfer_id}/confirm", response_model=StockTransferResponse, dependencies=[Depends(check_permission("inventory:edit"))])
def confirm_transfer(
    transfer_id: int,
    confirm_data: StockTransferConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Confirma una transferencia pendiente y mueve el stock entre ubicaciones (V2.0).
    
    Solo se puede confirmar si:
    - La transferencia está en estado "pendiente"
    - Hay stock suficiente en la ubicación de origen
    
    Al confirmar:
    - Reduce stock de la ubicación de origen
    - Aumenta stock de la ubicación de destino (crea registro si no existe)
    - Actualiza estado a "confirmada"
    - Registra fecha y usuario de confirmación
    - Crea entradas en StockHistory para trazabilidad
    """
    transfer = db.query(StockTransfer).filter(
        StockTransfer.id == transfer_id
    ).first()
    
    if not transfer:
        raise HTTPException(
            status_code=404,
            detail=f"Transferencia con ID {transfer_id} no encontrada"
        )
    
    if transfer.estado != "pendiente":
        raise HTTPException(
            status_code=400,
            detail=f"La transferencia ya está en estado '{transfer.estado}'. Solo se pueden confirmar transferencias pendientes."
        )
    
    # Validar entidades base
    product = validate_product_exists(db, transfer.product_id)
    from_location = validate_location_exists(db, transfer.from_location_id)
    to_location = validate_location_exists(db, transfer.to_location_id)
    
    # Validar stock en ubicación de origen
    source_stock = db.query(Stock).filter(
        Stock.product_id == transfer.product_id,
        Stock.location_id == transfer.from_location_id
    ).with_for_update().first()
    
    if not source_stock:
        raise HTTPException(
            status_code=400,
            detail="Stock de origen no encontrado"
        )
    
    # Inicializar StockManager
    stock_manager = StockManager(db)
    
    # VALIDACIÓN CRÍTICA: Verificar que el stock esté reservado
    if source_stock.cantidad_reservada < transfer.cantidad:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Stock no reservado correctamente. Reservado: {source_stock.cantidad_reservada}, "
                f"Necesario: {transfer.cantidad}. No se puede confirmar la transferencia."
            )
        )
    
    # V2.0: Validación de recepción física (IMEIs escaneados)
    from app.models import ProductIMEI
    imeis_in_transfer = db.query(ProductIMEI).filter(ProductIMEI.transfer_id == transfer.id).all()
    
    if imeis_in_transfer:
        if not confirm_data.scanned_imeis:
             # Si es serializado, EXIGIR escaneo
             raise HTTPException(
                 status_code=400, 
                 detail="Este producto es serializado. Debe escanear los IMEIs recibidos para confirmar la transferencia."
             )
        
        transfer_imeis_set = {i.imei for i in imeis_in_transfer}
        scanned_imeis_set = set(confirm_data.scanned_imeis)
        
        # Verificar que todos los IMEIs de la transferencia fueron escaneados
        missing = transfer_imeis_set - scanned_imeis_set
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Faltan IMEIs por escanear: {', '.join(missing)}. Verifique la recepción física."
            )
            
        # Verificar que no se escanearon IMEIs extraños
        extra = scanned_imeis_set - transfer_imeis_set
        if extra:
             raise HTTPException(
                status_code=400,
                detail=f"IMEIs escaneados no pertenecen a esta transferencia: {', '.join(extra)}"
            )

    try:
        # 1. Liberar la reserva en origen (sin aumentar stock libre)
        stock_manager.release_reservation(
            stock=source_stock,
            quantity=transfer.cantidad,
            transfer_id=transfer.id,
            is_rejection=False # Confirmación: solo reduce reserva
        )
        
        # 2. Reducir stock disponible en origen
        stock_manager.decrease_stock(
            stock=source_stock,
            quantity=transfer.cantidad,
            operation_type="transferencia_salida",
            notes=f"Transferencia a {to_location.nombre}: {transfer.notas or ''}",
            user_id=current_user.username
        )
        
        # 3. Aumentar stock disponible en destino
        stock_manager.increase_stock(
            product_id=product.id,
            location_id=to_location.id,
            quantity=transfer.cantidad,
            operation_type="transferencia_entrada",
            notes=f"Transferencia desde {from_location.nombre}: {transfer.notas or ''}",
            user_id=current_user.username,
            create_if_missing=True
        )
        
        # 4. Mover IMEIs
        # Buscar IMEIs asociados a esta transferencia (V2.0 con transfer_id)
        imeis_to_move = db.query(ProductIMEI).filter(
            ProductIMEI.transfer_id == transfer.id
        ).all()
        
        # Fallback legacy (si no hay transfer_id)
        if not imeis_to_move:
             has_imeis = db.query(ProductIMEI).filter(ProductIMEI.product_id == transfer.product_id).first() is not None
             if has_imeis:
                imeis_to_move = db.query(ProductIMEI).filter(
                    ProductIMEI.product_id == transfer.product_id,
                    ProductIMEI.location_id == transfer.from_location_id,
                    ProductIMEI.vendido == False,
                    ProductIMEI.transfer_id == None
                ).limit(transfer.cantidad).all()
        
        if imeis_to_move:
            stock_manager.transfer_imeis(
                imeis=imeis_to_move,
                to_location_id=transfer.to_location_id,
                transfer_id=transfer.id,
                notes=f"Transferencia confirmada de {from_location.nombre} a {to_location.nombre}",
                user_id=current_user.username
            )
            # Limpiar transfer_id (ya hecho en transfer_imeis? No, transfer_imeis solo cambia location y loguea)
            # StockManager.transfer_imeis NO limpia transfer_id, lo usa para el log.
            # Debemos limpiar transfer_id explícitamente
            stock_manager.release_reserved_imeis(imeis_to_move)

        # Actualizar estado de la transferencia
        transfer.estado = "confirmada"
        transfer.confirmed_at = datetime.now(UTC)
        transfer.confirmed_by = current_user.username
        
        db.commit()
        db.refresh(transfer)
        return _serialize_transfer(transfer)
    except StockValidationError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al confirmar la transferencia: {str(e)}"
        )


@router.post("/{transfer_id}/reject", response_model=StockTransferResponse, dependencies=[Depends(check_permission("inventory:edit"))])
def reject_transfer(
    transfer_id: int,
    reject_data: StockTransferReject,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Rechaza una transferencia pendiente.
    
    Solo se puede rechazar si la transferencia está en estado "pendiente".
    No se mueve ningún stock.
    """
    transfer = db.query(StockTransfer).filter(
        StockTransfer.id == transfer_id
    ).first()
    
    if not transfer:
        raise HTTPException(
            status_code=404,
            detail=f"Transferencia con ID {transfer_id} no encontrada"
        )
    
    if transfer.estado != "pendiente":
        raise HTTPException(
            status_code=400,
            detail=f"La transferencia ya está en estado '{transfer.estado}'. Solo se pueden rechazar transferencias pendientes."
        )
    
    # Validar entidades base
    product = validate_product_exists(db, transfer.product_id)
    from_location = validate_location_exists(db, transfer.from_location_id)

    # V2.0: LIBERAR la reserva de stock al rechazar
    source_stock = db.query(Stock).filter(
        Stock.product_id == product.id,
        Stock.location_id == from_location.id
    ).with_for_update().first()

    if not source_stock:
        raise HTTPException(
            status_code=400,
            detail="Stock de origen no encontrado para liberar reserva"
        )
    
    # Inicializar StockManager
    stock_manager = StockManager(db)
    
    try:
        # Liberar la reserva
        stock_manager.release_reservation(
            stock=source_stock,
            quantity=transfer.cantidad,
            transfer_id=transfer.id,
            notes=f"Transferencia rechazada por {current_user.username}: {reject_data.rejection_reason or 'Sin motivo especificado'}",
            user_id=current_user.username,
            is_rejection=True
        )
        
        # V2.0: Liberar IMEIs reservados
        from app.models import ProductIMEI
        imeis_reserved = db.query(ProductIMEI).filter(
            ProductIMEI.transfer_id == transfer.id
        ).all()
        
        if imeis_reserved:
            stock_manager.release_reserved_imeis(imeis_reserved)
        
        # Actualizar estado de la transferencia
        transfer.estado = "rechazada"
        transfer.confirmed_at = datetime.now(UTC)
        transfer.confirmed_by = current_user.username
        transfer.rejection_reason = reject_data.rejection_reason
        
        db.commit()
        db.refresh(transfer)
        return _serialize_transfer(transfer)
    except StockValidationError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al rechazar la transferencia: {str(e)}"
        )


@router.delete("/{transfer_id}", status_code=204, dependencies=[Depends(check_permission("inventory:edit"))])
def cancel_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Cancela una transferencia pendiente.
    
    Solo se puede cancelar si la transferencia está en estado "pendiente".
    """
    transfer = db.query(StockTransfer).filter(
        StockTransfer.id == transfer_id
    ).first()
    
    if not transfer:
        raise HTTPException(
            status_code=404,
            detail=f"Transferencia con ID {transfer_id} no encontrada"
        )
    
    if transfer.estado != "pendiente":
        raise HTTPException(
            status_code=400,
            detail=f"Solo se pueden cancelar transferencias pendientes. Estado actual: '{transfer.estado}'"
        )
    
    # Validar entidades base
    product = validate_product_exists(db, transfer.product_id)
    from_location = validate_location_exists(db, transfer.from_location_id)

    # V2.0: LIBERAR la reserva de stock al cancelar
    source_stock = db.query(Stock).filter(
        Stock.product_id == product.id,
        Stock.location_id == from_location.id
    ).with_for_update().first()

    if not source_stock:
        raise HTTPException(
            status_code=400,
            detail="Stock de origen no encontrado para liberar reserva"
        )
    
    # Inicializar StockManager
    stock_manager = StockManager(db)
    
    try:
        # Liberar la reserva
        stock_manager.release_reservation(
            stock=source_stock,
            quantity=transfer.cantidad,
            transfer_id=transfer.id,
             notes=f"Transferencia cancelada: {transfer.notas or 'Sin motivo especificado'}",
            user_id=current_user.username,
            is_rejection=True
        )
        
        # V2.0: Liberar IMEIs reservados
        from app.models import ProductIMEI
        imeis_reserved = db.query(ProductIMEI).filter(
            ProductIMEI.transfer_id == transfer.id
        ).all()
        
        if imeis_reserved:
            stock_manager.release_reserved_imeis(imeis_reserved)
        
        transfer.estado = "cancelada"
        
        db.commit()
        return None
    except StockValidationError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al cancelar la transferencia: {str(e)}"
        )
