from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("", response_model=List[schemas.LocationResponse])
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


@router.get("/{location_id}", response_model=schemas.LocationResponse)
def get_location(location_id: int, db: Session = Depends(get_db)):
    """Obtener una ubicación específica"""
    location = db.query(models.Location).filter(models.Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    return location


@router.post("", response_model=schemas.LocationResponse, status_code=201)
def create_location(
    location: schemas.LocationCreate,
    db: Session = Depends(get_db)
):
    """Crear una nueva ubicación"""
    try:
        db_location = models.Location(**location.model_dump())
        db.add(db_location)
        db.commit()
        db.refresh(db_location)
        return db_location
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear ubicación: {str(e)}")


@router.put("/{location_id}", response_model=schemas.LocationResponse)
def update_location(
    location_id: int,
    location: schemas.LocationUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar una ubicación existente"""
    db_location = db.query(models.Location).filter(models.Location.id == location_id).first()
    if not db_location:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    
    try:
        update_data = location.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_location, field, value)
        
        db.commit()
        db.refresh(db_location)
        return db_location
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar ubicación: {str(e)}")


@router.delete("/{location_id}", status_code=204)
def delete_location(location_id: int, db: Session = Depends(get_db)):
    """Eliminar una ubicación"""
    db_location = db.query(models.Location).filter(models.Location.id == location_id).first()
    if not db_location:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    
    # Verificar que no tenga stock
    stock_count = db.query(models.Stock).filter(models.Stock.location_id == location_id).count()
    if stock_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede eliminar la ubicación porque tiene {stock_count} registros de stock"
        )
    
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
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar ubicación: {str(e)}")


@router.get("/{location_id}/stock", response_model=List[schemas.StockByLocationResponse])
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
