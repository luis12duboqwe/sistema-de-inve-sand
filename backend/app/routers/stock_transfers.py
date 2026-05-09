from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import List, Optional
from datetime import UTC, datetime
import logging

from app.database import get_db
from app.models import StockTransfer, Product, Location, Stock, StockHistory, IMEIHistory, User
from app.schemas import (
    StockTransferCreate,
    StockTransferResponse,
    StockTransferConfirm,
    StockTransferReject,
    PaginatedResponse
)

from app.auth import check_permission, get_current_active_user
from app.utils.stock_manager import StockManager, StockValidationError
from app.utils.order_validators import validate_product_exists, validate_location_exists
from app.utils.daily_close_code import get_daily_close_code_hash, verify_daily_close_code
from app.utils.location_access import get_accessible_location_ids, require_location_access
from app.utils.audit import log_audit_event

router = APIRouter(prefix="/api/stock-transfers", tags=["stock_transfers"])
logger = logging.getLogger(__name__)

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
        received_quantity=transfer.received_quantity,
        missing_quantity=transfer.missing_quantity,
        confirmed_at=transfer.confirmed_at,
        confirmed_by=transfer.confirmed_by,
        incident_notes=transfer.incident_notes,
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


@router.post("", response_model=StockTransferResponse, status_code=201, dependencies=[Depends(check_permission("inventory:edit"))])
def create_transfer(
    transfer: StockTransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:edit"))
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
    require_location_access(db, current_user, from_location.id, "can_edit")
    require_location_access(db, current_user, to_location.id, "can_edit")
    
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

        log_audit_event(
            db,
            action="stock_transfer.create",
            entity_type="stock_transfer",
            entity_id=db_transfer.id,
            location_id=from_location.id,
            user=current_user,
            after_data=transfer.model_dump(),
        )
            
        db.commit()
        db.refresh(db_transfer)
        return _serialize_transfer(db_transfer)
    except StockValidationError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.exception("Error al crear transferencia")
        raise HTTPException(
            status_code=500,
            detail="Error interno al crear la transferencia. Intente nuevamente o contacte al administrador."
        )


@router.get("", response_model=PaginatedResponse[StockTransferResponse], dependencies=[Depends(check_permission("inventory:view"))])
def list_transfers(
    location_id: Optional[int] = Query(None, description="Filtrar por ubicación (origen o destino)"),
    from_location_id: Optional[int] = Query(None, description="Filtrar por ubicación origen"),
    to_location_id: Optional[int] = Query(None, description="Filtrar por ubicación destino"),
    product_id: Optional[int] = Query(None, description="Filtrar por ID de producto"),
    estado: Optional[str] = Query(None, description="Filtrar por estado de transferencia"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
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
    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
    
    # Filtro por ubicación (V2.0)
    if location_id:
        if accessible_location_ids is not None and location_id not in accessible_location_ids:
            raise HTTPException(status_code=403, detail="No tiene acceso a esta ubicación")
        query = query.filter(
            or_(
                StockTransfer.from_location_id == location_id,
                StockTransfer.to_location_id == location_id
            )
        )
    else:
        if from_location_id:
            if accessible_location_ids is not None and from_location_id not in accessible_location_ids:
                raise HTTPException(status_code=403, detail="No tiene acceso a la ubicación origen")
            query = query.filter(StockTransfer.from_location_id == from_location_id)

        if to_location_id:
            if accessible_location_ids is not None and to_location_id not in accessible_location_ids:
                raise HTTPException(status_code=403, detail="No tiene acceso a la ubicación destino")
            query = query.filter(StockTransfer.to_location_id == to_location_id)

    if not location_id and accessible_location_ids is not None:
        scoped_conditions = []
        if from_location_id:
            scoped_conditions.append(StockTransfer.from_location_id == from_location_id)
        if to_location_id:
            scoped_conditions.append(StockTransfer.to_location_id == to_location_id)

        if not scoped_conditions:
            query = query.filter(
                or_(
                    StockTransfer.from_location_id.in_(accessible_location_ids),
                    StockTransfer.to_location_id.in_(accessible_location_ids),
                )
            )
    elif accessible_location_ids is not None:
        query = query.filter(
            or_(
                StockTransfer.from_location_id.in_(accessible_location_ids),
                StockTransfer.to_location_id.in_(accessible_location_ids),
            )
        )
    
    # Filtro por producto
    if product_id:
        query = query.filter(StockTransfer.product_id == product_id)

    if estado:
        allowed_states = {"pendiente", "confirmada", "rechazada", "cancelada"}
        if estado not in allowed_states:
            raise HTTPException(status_code=400, detail="Estado de transferencia inválido")
        query = query.filter(StockTransfer.estado == estado)
    
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


@router.get("/{transfer_id}", response_model=StockTransferResponse, dependencies=[Depends(check_permission("inventory:view"))])
def get_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
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
    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
    if (
        accessible_location_ids is not None
        and transfer.from_location_id not in accessible_location_ids
        and transfer.to_location_id not in accessible_location_ids
    ):
        raise HTTPException(status_code=403, detail="No tiene acceso a esta transferencia")
    
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

    require_location_access(db, current_user, transfer.to_location_id, "can_edit")

    configured_code_hash = get_daily_close_code_hash(db)
    if configured_code_hash:
        if not confirm_data.validation_code:
            raise HTTPException(
                status_code=400,
                detail="Debe ingresar el código de validación para confirmar la transferencia.",
            )
        if not verify_daily_close_code(configured_code_hash, confirm_data.validation_code):
            logger.warning(
                "Intento fallido de confirmar transferencia %s por usuario %s: código inválido",
                transfer_id,
                current_user.username,
            )
            raise HTTPException(status_code=403, detail="Código de validación incorrecto.")
    
    # Validar entidades base
    product = validate_product_exists(db, transfer.product_id)
    from_location = validate_location_exists(db, transfer.from_location_id)
    require_location_access(db, current_user, from_location.id, "can_edit")
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

    received_quantity = confirm_data.received_quantity
    if received_quantity is None:
        received_quantity = transfer.cantidad
    if received_quantity < 0 or received_quantity > transfer.cantidad:
        raise HTTPException(
            status_code=400,
            detail="La cantidad recibida debe estar entre 0 y la cantidad transferida"
        )

    missing_quantity = transfer.cantidad - received_quantity
    if missing_quantity > 0 and not confirm_data.incident_notes:
        raise HTTPException(
            status_code=400,
            detail="Debe indicar notas de incidencia cuando la recepción es parcial"
        )
    
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
    scanned_imeis_set = set(confirm_data.scanned_imeis or [])
    
    if imeis_in_transfer:
        if received_quantity == 0:
            scanned_imeis_set = set()
        elif not confirm_data.scanned_imeis:
             # Si es serializado, EXIGIR escaneo
             raise HTTPException(
                 status_code=400, 
                 detail="Este producto es serializado. Debe escanear los IMEIs recibidos para confirmar la transferencia."
             )

        transfer_imeis_set = {i.imei for i in imeis_in_transfer}

        if len(scanned_imeis_set) != received_quantity:
            raise HTTPException(
                status_code=400,
                detail=f"La cantidad de IMEIs escaneados ({len(scanned_imeis_set)}) debe coincidir con la cantidad recibida ({received_quantity})"
            )
        
        # Verificar que no se escanearon IMEIs extraños
        extra = scanned_imeis_set - transfer_imeis_set
        if extra:
             raise HTTPException(
                status_code=400,
                detail=f"IMEIs escaneados no pertenecen a esta transferencia: {', '.join(extra)}"
            )

    try:
        # 1. Liberar toda la reserva en origen. Si hay faltante, queda libre en origen
        # hasta que se haga un ajuste explícito por merma/daño.
        stock_manager.release_reservation(
            stock=source_stock,
            quantity=transfer.cantidad,
            transfer_id=transfer.id,
            is_rejection=False # Confirmación: solo reduce reserva
        )
        
        if received_quantity > 0:
            # 2. Reducir stock disponible en origen solo por lo recibido
            stock_manager.decrease_stock(
                stock=source_stock,
                quantity=received_quantity,
                operation_type="transferencia_salida",
                notes=f"Transferencia a {to_location.nombre}: {transfer.notas or ''}",
                user_id=current_user.username
            )

            # 3. Aumentar stock disponible en destino por lo recibido
            stock_manager.increase_stock(
                product_id=product.id,
                location_id=to_location.id,
                quantity=received_quantity,
                operation_type="transferencia_entrada",
                notes=f"Transferencia desde {from_location.nombre}: {transfer.notas or ''}",
                user_id=current_user.username,
                create_if_missing=True
            )

        if missing_quantity > 0:
            stock_libre = source_stock.cantidad_disponible - source_stock.cantidad_reservada
            db.add(StockHistory(
                product_id=transfer.product_id,
                location_id=transfer.from_location_id,
                tipo_cambio="transferencia_recepcion_parcial",
                cantidad=missing_quantity,
                stock_anterior=stock_libre,
                stock_nuevo=stock_libre,
                referencia_id=transfer.id,
                referencia_tipo="transfer_partial",
                notas=confirm_data.incident_notes or f"Recepción parcial en {to_location.nombre}",
                usuario=current_user.username,
            ))
        
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
                ).limit(received_quantity).all()
        
        if imeis_to_move:
            if scanned_imeis_set:
                imeis_to_move = [imei for imei in imeis_to_move if imei.imei in scanned_imeis_set]
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

        if missing_quantity > 0:
            missing_imeis = [imei for imei in imeis_in_transfer if imei.imei not in scanned_imeis_set]
            if missing_imeis:
                stock_manager.release_reserved_imeis(missing_imeis)

        # Actualizar estado de la transferencia
        transfer.estado = "confirmada"
        transfer.received_quantity = received_quantity
        transfer.missing_quantity = missing_quantity
        transfer.incident_notes = confirm_data.incident_notes
        transfer.confirmed_at = datetime.now(UTC)
        transfer.confirmed_by = current_user.username
        log_audit_event(
            db,
            action="stock_transfer.confirm",
            entity_type="stock_transfer",
            entity_id=transfer.id,
            location_id=transfer.to_location_id,
            user=current_user,
            after_data={"estado": "confirmada", "scanned_imeis": confirm_data.scanned_imeis},
        )
        
        db.commit()
        db.refresh(transfer)
        return _serialize_transfer(transfer)
    except StockValidationError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.exception("Error al confirmar transferencia")
        raise HTTPException(
            status_code=500,
            detail="Error interno al confirmar la transferencia. Intente nuevamente o contacte al administrador."
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
    require_location_access(db, current_user, from_location.id, "can_edit")

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
        logger.exception("Error al rechazar transferencia")
        raise HTTPException(
            status_code=500,
            detail="Error interno al rechazar la transferencia. Intente nuevamente o contacte al administrador."
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
        logger.exception("Error al cancelar transferencia")
        raise HTTPException(
            status_code=500,
            detail="Error interno al cancelar la transferencia. Intente nuevamente o contacte al administrador."
        )
