import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

from app.auth import get_current_active_user, check_permission
from app.models import User

router = APIRouter(prefix="/api/locations", tags=["locations"])
logger = logging.getLogger(__name__)


@router.get("", response_model=List[schemas.LocationResponse], dependencies=[Depends(check_permission("settings:view"))])
def get_locations(
    skip: int = 0,
    limit: int = 100,
    activo: Optional[bool] = None,
    tipo: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Obtener todas las ubicaciones (tiendas, bodegas, etc.)"""
    query = db.query(models.Location)
    
    if activo is not None:
        query = query.filter(models.Location.activo == activo)
    
    if tipo:
        query = query.filter(models.Location.tipo == tipo)
    
    locations = query.order_by(models.Location.nombre).offset(skip).limit(limit).all()
    return locations


@router.get("/{location_id}", response_model=schemas.LocationResponse, dependencies=[Depends(check_permission("settings:view"))])
def get_location(location_id: int, db: Session = Depends(get_db)):
    """Obtener una ubicación específica"""
    location = db.query(models.Location).filter(models.Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    return location


@router.post("", response_model=schemas.LocationResponse, status_code=201, dependencies=[Depends(check_permission("settings:edit"))])
def create_location(
    location: schemas.LocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("locations:manage"))
):
    """Crear una nueva ubicación"""
    # Validar que el nombre sea único (case-insensitive)
    nombre_limpio = (location.nombre or "").strip()
    if not nombre_limpio:
        raise HTTPException(
            status_code=400,
            detail="El nombre de la ubicación no puede estar vacío"
        )
    
    existing = db.query(models.Location).filter(
        func.lower(models.Location.nombre) == nombre_limpio.lower()
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"La ubicación '{nombre_limpio}' ya existe"
        )
    
    try:
        location_data = location.model_dump()
        location_data['nombre'] = nombre_limpio
        db_location = models.Location(**location_data)
        db.add(db_location)
        db.commit()
        db.refresh(db_location)
        return db_location
    except Exception:
        db.rollback()
        logger.exception("Error al crear ubicación")
        raise HTTPException(
            status_code=500,
            detail="Error interno al crear la ubicación. Intente nuevamente o contacte al administrador."
        )


@router.put("/{location_id}", response_model=schemas.LocationResponse, dependencies=[Depends(check_permission("settings:edit"))])
def update_location(
    location_id: int,
    location: schemas.LocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("locations:manage"))
):
    """Actualizar una ubicación existente"""
    db_location = db.query(models.Location).filter(models.Location.id == location_id).first()
    if not db_location:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    
    try:
        update_data = location.model_dump(exclude_unset=True)
        
        # Validar nombre único si se está actualizando (case-insensitive)
        if 'nombre' in update_data:
            nuevo_nombre = (update_data['nombre'] or "").strip()
            if not nuevo_nombre:
                raise HTTPException(
                    status_code=400,
                    detail="El nombre de la ubicación no puede estar vacío"
                )
            if nuevo_nombre.lower() != db_location.nombre.lower():
                existing = db.query(models.Location).filter(
                    func.lower(models.Location.nombre) == nuevo_nombre.lower(),
                    models.Location.id != location_id
                ).first()
                if existing:
                    raise HTTPException(
                        status_code=400,
                        detail=f"La ubicación '{nuevo_nombre}' ya existe"
                    )
            update_data['nombre'] = nuevo_nombre
        
        for field, value in update_data.items():
            setattr(db_location, field, value)
        
        db.commit()
        db.refresh(db_location)
        return db_location
    except Exception:
        db.rollback()
        logger.exception("Error al actualizar ubicación %s", location_id)
        raise HTTPException(
            status_code=500,
            detail="Error interno al actualizar la ubicación. Intente nuevamente o contacte al administrador."
        )


@router.delete("/{location_id}", status_code=204, dependencies=[Depends(check_permission("settings:edit"))])
def delete_location(
    location_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("locations:manage"))
):
    """Eliminar una ubicación"""
    db_location = db.query(models.Location).filter(models.Location.id == location_id).first()
    if not db_location:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    
    # Verificar que no tenga stock REAL (cantidad > 0)
    # Si tiene registros de stock pero todos están en 0, se pueden eliminar
    stocks = db.query(models.Stock).filter(models.Stock.location_id == location_id).all()
    
    has_stock = False
    for stock in stocks:
        total_stock = stock.cantidad_disponible + stock.cantidad_reservada + stock.cantidad_defectuosa
        if total_stock > 0:
            has_stock = True
            break
            
    if has_stock:
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede eliminar la ubicación porque tiene productos con stock positivo."
        )
        
    # Si llegamos aquí, o no hay registros de stock, o todos están en 0.
    # Eliminamos los registros de stock vacíos antes de eliminar la ubicación
    if stocks:
        for stock in stocks:
            db.delete(stock)
        db.flush()
    
    # V2.0: Verificar que no tenga órdenes asociadas
    from app.models import Order
    order_count = db.query(Order).filter(Order.source_location_id == location_id).count()
    if order_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar la ubicación porque tiene {order_count} órdenes históricas. Use 'activo=false' para desactivarla."
        )
    
    # V2.0: Verificar que no tenga transferencias asociadas
    from app.models import StockTransfer
    from sqlalchemy import or_
    transfer_count = db.query(StockTransfer).filter(
        or_(
            StockTransfer.from_location_id == location_id,
            StockTransfer.to_location_id == location_id
        )
    ).count()
    if transfer_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar la ubicación porque tiene {transfer_count} transferencias de stock. Use 'activo=false' para desactivarla."
        )
    
    try:
        db.delete(db_location)
        db.commit()
        return None
    except Exception:
        db.rollback()
        logger.exception("Error al eliminar ubicación %s", location_id)
        raise HTTPException(
            status_code=500,
            detail="Error interno al eliminar la ubicación. Intente nuevamente o contacte al administrador."
        )


@router.get("/{location_id}/stock", response_model=List[schemas.StockByLocationResponse], dependencies=[Depends(check_permission("inventory:view"))])
def get_location_stock(
    location_id: int,
    db: Session = Depends(get_db)
):
    """Obtener todo el stock de una ubicación específica"""
    location = db.query(models.Location).filter(models.Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    
    stock_items = db.query(models.Stock).filter(
        models.Stock.location_id == location_id,
        models.Stock.cantidad_disponible > 0
    ).all()
    
    return stock_items
