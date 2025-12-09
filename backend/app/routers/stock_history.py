"""
Router para gestión de historial de stock
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models import StockHistory, Product
from app.schemas import StockHistoryResponse, StockHistoryCreate

router = APIRouter(prefix="/stock-history", tags=["stock-history"])


@router.get("/product/{product_id}", response_model=List[StockHistoryResponse])
def get_product_stock_history(
    product_id: int,
    limit: int = Query(100, ge=1, le=1000),
    tipo_cambio: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Obtener historial de cambios de stock para un producto específico
    
    - **product_id**: ID del producto
    - **limit**: Número máximo de registros (default: 100)
    - **tipo_cambio**: Filtrar por tipo de cambio (opcional)
    - **date_from**: Fecha desde (opcional)
    - **date_to**: Fecha hasta (opcional)
    """
    # Verificar que el producto existe
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    # Construir query base
    query = db.query(StockHistory).filter(StockHistory.product_id == product_id)
    
    # Aplicar filtros
    if tipo_cambio:
        query = query.filter(StockHistory.tipo_cambio == tipo_cambio)
    
    if date_from:
        query = query.filter(StockHistory.created_at >= date_from)
    
    if date_to:
        query = query.filter(StockHistory.created_at <= date_to)
    
    # Ordenar por fecha descendente y limitar
    history = query.order_by(StockHistory.created_at.desc()).limit(limit).all()
    
    return history


@router.get("/location/{location_id}", response_model=List[StockHistoryResponse])
def get_location_stock_history(
    location_id: int,
    limit: int = Query(100, ge=1, le=1000),
    tipo_cambio: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Obtener historial de cambios de stock para una ubicación específica (V2.0)
    
    - **location_id**: ID de la ubicación (tienda/bodega)
    - **limit**: Número máximo de registros (default: 100)
    - **tipo_cambio**: Filtrar por tipo de cambio (opcional)
    - **days**: Número de días hacia atrás (default: 30)
    """
    # Verificar que la ubicación existe
    from app.models import Location
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    
    # Calcular fecha desde
    date_from = datetime.now() - timedelta(days=days)
    
    # Construir query por ubicación
    query = db.query(StockHistory).filter(
        StockHistory.location_id == location_id,
        StockHistory.created_at >= date_from
    )
    
    # Aplicar filtro de tipo si se proporciona
    if tipo_cambio:
        query = query.filter(StockHistory.tipo_cambio == tipo_cambio)
    
    # Ordenar y limitar
    history = query.order_by(StockHistory.created_at.desc()).limit(limit).all()
    
    return history


@router.get("/profile/{profile_id}", response_model=List[StockHistoryResponse])
def get_profile_stock_history(
    profile_id: int,
    limit: int = Query(100, ge=1, le=1000),
    tipo_cambio: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    LEGACY: Obtener historial de cambios de stock para todos los productos de un perfil V1.0
    
    DEPRECADO: Usar /location/{location_id} para V2.0
    
    - **profile_id**: ID del perfil legacy
    - **limit**: Número máximo de registros (default: 100)
    - **tipo_cambio**: Filtrar por tipo de cambio (opcional)
    - **days**: Número de días hacia atrás (default: 30)
    """
    # Calcular fecha desde
    date_from = datetime.now() - timedelta(days=days)
    
    # Construir query - Solo productos que AÚN tienen profile_id
    query = db.query(StockHistory).join(
        Product, StockHistory.product_id == Product.id
    ).filter(
        Product.profile_id == profile_id,
        StockHistory.created_at >= date_from
    )
    
    # Aplicar filtro de tipo si se proporciona
    if tipo_cambio:
        query = query.filter(StockHistory.tipo_cambio == tipo_cambio)
    
    # Ordenar y limitar
    history = query.order_by(StockHistory.created_at.desc()).limit(limit).all()
    
    return history


@router.post("/", response_model=StockHistoryResponse)
def create_stock_history_entry(
    entry: StockHistoryCreate,
    db: Session = Depends(get_db)
):
    """
    Crear un registro manual de historial de stock
    
    Útil para ajustes manuales o correcciones
    """
    # Verificar que el producto existe
    product = db.query(Product).filter(Product.id == entry.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    # Crear registro
    db_entry = StockHistory(**entry.model_dump())
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    
    return db_entry


@router.get("/stats/{product_id}")
def get_product_stock_stats(
    product_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Obtener estadísticas de movimientos de stock para un producto
    
    - **product_id**: ID del producto
    - **days**: Número de días hacia atrás (default: 30)
    """
    # Verificar que el producto existe
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    # Calcular fecha desde
    date_from = datetime.now() - timedelta(days=days)
    
    # Obtener todos los registros del período
    history = db.query(StockHistory).filter(
        StockHistory.product_id == product_id,
        StockHistory.created_at >= date_from
    ).all()
    
    # Calcular estadísticas
    stats = {
        "product_id": product_id,
        "product_name": product.nombre,
        "period_days": days,
        "total_movements": len(history),
        "movements_by_type": {},
        "total_entrada": 0,
        "total_salida": 0,
        "stock_actual": product.stock.cantidad_disponible if product.stock else 0
    }
    
    for record in history:
        # Contar por tipo
        tipo = record.tipo_cambio
        if tipo not in stats["movements_by_type"]:
            stats["movements_by_type"][tipo] = 0
        stats["movements_by_type"][tipo] += 1
        
        # Sumar entradas y salidas
        if record.cantidad > 0:
            stats["total_entrada"] += record.cantidad
        else:
            stats["total_salida"] += abs(record.cantidad)
    
    return stats
