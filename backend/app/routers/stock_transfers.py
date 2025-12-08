from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import StockTransfer, Product, Profile, Stock
from app.schemas import (
    StockTransferCreate, 
    StockTransferResponse, 
    StockTransferConfirm,
    StockTransferReject,
    PaginatedResponse
)

router = APIRouter(prefix="/api/stock-transfers", tags=["stock-transfers"])


def _serialize_transfer(transfer: StockTransfer) -> StockTransferResponse:
    """Serializa una transferencia de stock con información adicional"""
    return StockTransferResponse(
        id=transfer.id,
        product_id=transfer.product_id,
        from_profile_id=transfer.from_profile_id,
        to_profile_id=transfer.to_profile_id,
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
        from_profile_name=transfer.from_profile.name if transfer.from_profile else None,
        to_profile_name=transfer.to_profile.name if transfer.to_profile else None
    )


@router.post("", response_model=StockTransferResponse, status_code=201)
def create_transfer(
    transfer: StockTransferCreate,
    db: Session = Depends(get_db)
):
    """
    Crea una nueva transferencia de stock entre perfiles.
    
    Validaciones:
    - El producto debe existir
    - Los perfiles de origen y destino deben existir y ser diferentes
    - Debe haber stock suficiente en el perfil de origen
    - El producto debe pertenecer al perfil de origen
    
    La transferencia:
    - Reduce el stock del perfil de origen
    - Aumenta el stock del perfil de destino (creando el producto si no existe)
    - Registra la transferencia para trazabilidad
    """
    # Validar perfiles
    from_profile = db.query(Profile).filter(
        Profile.slug == transfer.from_profile_slug
    ).first()
    
    if not from_profile:
        raise HTTPException(
            status_code=404,
            detail=f"Perfil de origen '{transfer.from_profile_slug}' no encontrado"
        )
    
    to_profile = db.query(Profile).filter(
        Profile.slug == transfer.to_profile_slug
    ).first()
    
    if not to_profile:
        raise HTTPException(
            status_code=404,
            detail=f"Perfil de destino '{transfer.to_profile_slug}' no encontrado"
        )
    
    if from_profile.id == to_profile.id:
        raise HTTPException(
            status_code=400,
            detail="No se puede transferir stock al mismo perfil"
        )
    
    # Validar producto
    source_product = db.query(Product).filter(
        Product.id == transfer.product_id,
        Product.profile_id == from_profile.id
    ).first()
    
    if not source_product:
        raise HTTPException(
            status_code=404,
            detail=f"Producto con ID {transfer.product_id} no encontrado en el perfil '{from_profile.name}'"
        )
    
    # Validar stock disponible
    if not source_product.stock:
        raise HTTPException(
            status_code=400,
            detail=f"El producto '{source_product.nombre}' no tiene registro de stock"
        )
    
    if source_product.stock.cantidad_disponible < transfer.cantidad:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente. Disponible: {source_product.stock.cantidad_disponible}, Solicitado: {transfer.cantidad}"
        )
    
    # IMPORTANTE: NO mover el stock aún, solo crear la transferencia pendiente
    # El stock se moverá cuando se confirme la transferencia
    
    # Registrar la transferencia en estado PENDIENTE
    db_transfer = StockTransfer(
        product_id=source_product.id,
        from_profile_id=from_profile.id,
        to_profile_id=to_profile.id,
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
    profile_slug: Optional[str] = Query(None, description="Filtrar por perfil (origen o destino)"),
    product_id: Optional[int] = Query(None, description="Filtrar por ID de producto"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db)
):
    """
    Lista las transferencias de stock con filtros opcionales.
    
    Parámetros:
    - profile_slug: Filtrar transferencias donde el perfil sea origen o destino
    - product_id: Filtrar transferencias de un producto específico
    - page: Número de página para paginación
    - per_page: Cantidad de resultados por página
    """
    query = db.query(StockTransfer)
    
    # Filtro por perfil
    if profile_slug:
        profile = db.query(Profile).filter(Profile.slug == profile_slug).first()
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"Perfil '{profile_slug}' no encontrado"
            )
        query = query.filter(
            or_(
                StockTransfer.from_profile_id == profile.id,
                StockTransfer.to_profile_id == profile.id
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
    Confirma una transferencia pendiente y mueve el stock.
    
    Solo se puede confirmar si:
    - La transferencia está en estado "pendiente"
    - Hay stock suficiente en el perfil de origen
    
    Al confirmar:
    - Reduce stock del perfil de origen
    - Aumenta stock del perfil de destino (crea producto si no existe)
    - Actualiza estado a "confirmada"
    - Registra fecha y usuario de confirmación
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
    
    # Validar que aún hay stock suficiente
    source_product = db.query(Product).filter(
        Product.id == transfer.product_id
    ).first()
    
    if not source_product or not source_product.stock:
        raise HTTPException(
            status_code=404,
            detail="Producto de origen no encontrado o sin stock"
        )
    
    if source_product.stock.cantidad_disponible < transfer.cantidad:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente para confirmar. Disponible: {source_product.stock.cantidad_disponible}, Necesario: {transfer.cantidad}"
        )
    
    # Buscar o crear producto en el perfil de destino
    dest_product = db.query(Product).filter(
        Product.sku == source_product.sku,
        Product.profile_id == transfer.to_profile_id
    ).first()
    
    if not dest_product:
        # Crear producto en el perfil de destino
        dest_product = Product(
            profile_id=transfer.to_profile_id,
            supplier_id=source_product.supplier_id,
            sku=source_product.sku,
            nombre=source_product.nombre,
            categoria=source_product.categoria,
            marca=source_product.marca,
            modelo=source_product.modelo,
            capacidad=source_product.capacidad,
            condicion=source_product.condicion,
            precio=source_product.precio,
            moneda=source_product.moneda,
            garantia_meses=source_product.garantia_meses,
            activo=source_product.activo
        )
        db.add(dest_product)
        db.flush()
        
        # Crear stock para el nuevo producto
        dest_stock = Stock(
            product_id=dest_product.id,
            cantidad_disponible=0
        )
        db.add(dest_stock)
        db.flush()
    
    # Actualizar stocks
    source_product.stock.cantidad_disponible -= transfer.cantidad
    
    if not dest_product.stock:
        dest_stock = Stock(
            product_id=dest_product.id,
            cantidad_disponible=transfer.cantidad
        )
        db.add(dest_stock)
    else:
        dest_product.stock.cantidad_disponible += transfer.cantidad
    
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
    
    try:
        db.commit()
        return None
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al cancelar la transferencia: {str(e)}"
        )
