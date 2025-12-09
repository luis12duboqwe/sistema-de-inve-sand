from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import StockTransfer, Product, Location, Stock, StockHistory
from app.schemas import (
    StockTransferCreate, 
    StockTransferResponse, 
    StockTransferConfirm,
    StockTransferReject,
    PaginatedResponse
)

router = APIRouter(prefix="/api/stock-transfers", tags=["stock-transfers"])


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
        to_profile_name=transfer.to_profile.name if transfer.to_profile else None
    )


@router.post("", response_model=StockTransferResponse, status_code=201)
def create_transfer(
    transfer: StockTransferCreate,
    db: Session = Depends(get_db)
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
    # Validar ubicaciones
    from_location = db.query(Location).filter(
        Location.id == transfer.from_location_id,
        Location.activo == True
    ).first()
    
    if not from_location:
        raise HTTPException(
            status_code=404,
            detail=f"Ubicación de origen con ID {transfer.from_location_id} no encontrada o inactiva"
        )
    
    to_location = db.query(Location).filter(
        Location.id == transfer.to_location_id,
        Location.activo == True
    ).first()
    
    if not to_location:
        raise HTTPException(
            status_code=404,
            detail=f"Ubicación de destino con ID {transfer.to_location_id} no encontrada o inactiva"
        )
    
    if from_location.id == to_location.id:
        raise HTTPException(
            status_code=400,
            detail="No se puede transferir stock a la misma ubicación"
        )
    
    # Validar producto
    product = db.query(Product).filter(
        Product.id == transfer.product_id,
        Product.activo == True
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Producto con ID {transfer.product_id} no encontrado o inactivo"
        )
    
    # Validar stock en ubicación de origen
    source_stock = db.query(Stock).filter(
        Stock.product_id == transfer.product_id,
        Stock.location_id == transfer.from_location_id
    ).first()
    
    if not source_stock:
        raise HTTPException(
            status_code=400,
            detail=f"El producto '{product.nombre}' no tiene stock en '{from_location.nombre}'"
        )
    
    if source_stock.cantidad_disponible < transfer.cantidad:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente en '{from_location.nombre}'. Disponible: {source_stock.cantidad_disponible}, Solicitado: {transfer.cantidad}"
        )
    
    # Crear la transferencia en estado PENDIENTE
    # El stock se moverá cuando se confirme la transferencia
    db_transfer = StockTransfer(
        product_id=product.id,
        from_location_id=from_location.id,
        to_location_id=to_location.id,
        cantidad=transfer.cantidad,
        notas=transfer.notas,
        estado="pendiente",
        created_by=transfer.created_by
    )
    db.add(db_transfer)
    
    try:
        db.commit()
        db.refresh(db_transfer)
        return _serialize_transfer(db_transfer)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear la transferencia: {str(e)}"
        )


@router.get("", response_model=PaginatedResponse[StockTransferResponse])
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
    total_pages = (total + per_page - 1) // per_page
    
    transfers = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return PaginatedResponse(
        items=[_serialize_transfer(t) for t in transfers],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
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


@router.post("/{transfer_id}/confirm", response_model=StockTransferResponse)
def confirm_transfer(
    transfer_id: int,
    confirm_data: StockTransferConfirm,
    db: Session = Depends(get_db)
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
    
    # Validar que el producto existe
    product = db.query(Product).filter(
        Product.id == transfer.product_id,
        Product.activo == True
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=404,
            detail="Producto no encontrado o inactivo"
        )
    
    # Validar stock en ubicación de origen
    source_stock = db.query(Stock).filter(
        Stock.product_id == transfer.product_id,
        Stock.location_id == transfer.from_location_id
    ).first()
    
    if not source_stock:
        raise HTTPException(
            status_code=400,
            detail="Stock de origen no encontrado"
        )
    
    if source_stock.cantidad_disponible < transfer.cantidad:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente para confirmar. Disponible: {source_stock.cantidad_disponible}, Necesario: {transfer.cantidad}"
        )
    
    # Buscar o crear stock en ubicación de destino
    dest_stock = db.query(Stock).filter(
        Stock.product_id == transfer.product_id,
        Stock.location_id == transfer.to_location_id
    ).first()
    
    stock_anterior_origen = source_stock.cantidad_disponible
    stock_anterior_destino = dest_stock.cantidad_disponible if dest_stock else 0
    
    if not dest_stock:
        # Crear registro de stock en ubicación de destino
        dest_stock = Stock(
            product_id=product.id,
            location_id=transfer.to_location_id,
            cantidad_disponible=0
        )
        db.add(dest_stock)
        db.flush()
    
    # Actualizar stocks atómicamente
    source_stock.cantidad_disponible -= transfer.cantidad
    dest_stock.cantidad_disponible += transfer.cantidad
    
    # Validación de seguridad post-operación
    if source_stock.cantidad_disponible < 0:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error crítico: Stock negativo detectado en ubicación de origen ({source_stock.cantidad_disponible}). Posible race condition."
        )
    
    # Registrar en historial de stock (trazabilidad)
    history_salida = StockHistory(
        product_id=product.id,
        location_id=transfer.from_location_id,
        tipo_cambio='transferencia_salida',
        cantidad=-transfer.cantidad,
        stock_anterior=stock_anterior_origen,
        stock_nuevo=source_stock.cantidad_disponible,
        referencia_id=transfer.id,
        referencia_tipo='transfer',
        notas=f"Transferencia a {transfer.to_location.nombre}: {transfer.notas or ''}",
        usuario=confirm_data.confirmed_by
    )
    db.add(history_salida)
    
    history_entrada = StockHistory(
        product_id=product.id,
        location_id=transfer.to_location_id,
        tipo_cambio='transferencia_entrada',
        cantidad=transfer.cantidad,
        stock_anterior=stock_anterior_destino,
        stock_nuevo=dest_stock.cantidad_disponible,
        referencia_id=transfer.id,
        referencia_tipo='transfer',
        notas=f"Transferencia desde {transfer.from_location.nombre}: {transfer.notas or ''}",
        usuario=confirm_data.confirmed_by
    )
    db.add(history_entrada)
    
    # V2.0: Mover IMEIs automáticamente a la nueva ubicación
    from app.models import ProductIMEI
    imeis_to_move = db.query(ProductIMEI).filter(
        ProductIMEI.product_id == transfer.product_id,
        ProductIMEI.location_id == transfer.from_location_id,
        ProductIMEI.vendido == False
    ).limit(transfer.cantidad).all()
    
    for imei in imeis_to_move:
        imei.location_id = transfer.to_location_id
    
    # Actualizar estado de la transferencia
    transfer.estado = "confirmada"
    transfer.confirmed_at = datetime.utcnow()
    transfer.confirmed_by = confirm_data.confirmed_by
    
    try:
        db.commit()
        db.refresh(transfer)
        return _serialize_transfer(transfer)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al confirmar la transferencia: {str(e)}"
        )


@router.post("/{transfer_id}/reject", response_model=StockTransferResponse)
def reject_transfer(
    transfer_id: int,
    reject_data: StockTransferReject,
    db: Session = Depends(get_db)
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
    
    # Actualizar estado de la transferencia
    transfer.estado = "rechazada"
    transfer.confirmed_at = datetime.utcnow()
    transfer.confirmed_by = reject_data.rejected_by
    transfer.rejection_reason = reject_data.rejection_reason
    
    # V2.0: Registrar rechazo en historial para trazabilidad
    from app.models import StockHistory
    history_rechazo = StockHistory(
        product_id=transfer.product_id,
        location_id=transfer.from_location_id,
        tipo_cambio='transferencia_rechazada',
        cantidad=0,  # No se mueve stock
        stock_anterior=0,
        stock_nuevo=0,
        referencia_id=transfer.id,
        referencia_tipo='transfer_rejected',
        notas=f"Transferencia rechazada por {reject_data.rejected_by}: {reject_data.rejection_reason or 'Sin motivo especificado'}",
        usuario=reject_data.rejected_by
    )
    db.add(history_rechazo)
    
    try:
        db.commit()
        db.refresh(transfer)
        return _serialize_transfer(transfer)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al rechazar la transferencia: {str(e)}"
        )


@router.delete("/{transfer_id}", status_code=204)
def cancel_transfer(
    transfer_id: int,
    db: Session = Depends(get_db)
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
    
    transfer.estado = "cancelada"
    
    # V2.0: Registrar cancelación en historial para trazabilidad
    from app.models import StockHistory
    history_cancelacion = StockHistory(
        product_id=transfer.product_id,
        location_id=transfer.from_location_id,
        tipo_cambio='transferencia_cancelada',
        cantidad=0,  # No se mueve stock
        stock_anterior=0,
        stock_nuevo=0,
        referencia_id=transfer.id,
        referencia_tipo='transfer_cancelled',
        notas=f"Transferencia cancelada: {transfer.notas or 'Sin motivo especificado'}",
        usuario=transfer.created_by or 'sistema'
    )
    db.add(history_cancelacion)
    
    try:
        db.commit()
        return None
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al cancelar la transferencia: {str(e)}"
        )
