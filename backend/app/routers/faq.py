from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
import math
import logging
from app.database import get_db
from app.models import FAQEntry, User
from app.schemas import FAQEntryCreate, FAQEntryResponse, FAQEntryUpdate, PaginatedResponse
from app.auth import check_permission

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=PaginatedResponse[FAQEntryResponse], dependencies=[Depends(check_permission("settings:view"))])
def list_faq_entries(
    activa: bool = Query(True, description="Filtrar por entradas activas"),
    categoria: str = Query(None, description="Filtrar por categoría"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db)
):
    """
    Lista entradas FAQ con paginación.
    
    Args:
        - activa: Filtrar por estado activo (default: True)
        - categoria: Filtro opcional por categoría
        - page: Número de página (default: 1)
        - per_page: Resultados por página (default: 50, max: 100)
        
    Returns:
        Respuesta paginada con lista de entradas FAQ
    """
    query = db.query(FAQEntry)
    
    if activa is not None:
        query = query.filter(FAQEntry.activa == activa)
    
    if categoria:
        query = query.filter(FAQEntry.categoria == categoria)
    
    total = query.count()
    offset = (page - 1) * per_page
    entries = query.order_by(FAQEntry.veces_usada.desc(), FAQEntry.created_at.desc()).offset(offset).limit(per_page).all()
    
    return PaginatedResponse(
        items=entries,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0
    )


@router.get("/search", response_model=List[FAQEntryResponse], dependencies=[Depends(check_permission("settings:view"))])
def search_faq_entries(
    query: str = Query(..., description="Texto de la pregunta del cliente"),
    limit: int = Query(3, description="Número máximo de resultados"),
    db: Session = Depends(get_db)
):
    """
    Busca entradas FAQ por coincidencia de texto.
    
    Args:
        - query: Texto de búsqueda
        - limit: Número máximo de resultados (default: 3)
        
    Returns:
        Lista de entradas FAQ que coinciden con la búsqueda
        
    Raises:
        - 400: Si el parámetro query está vacío
        - 500: Si ocurre un error al buscar
    """
    if not query.strip():
        raise HTTPException(status_code=400, detail="El parámetro 'query' no puede estar vacío")

    try:
        # V2.1: Búsqueda inteligente de FAQs
        # 1. Filtrar stop words
        stop_words = {'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'y', 'o', 'pero', 'si', 'no', 'en', 'a', 'de', 'del', 'al', 'con', 'por', 'para', 'es', 'son', 'que', 'como', 'cuando', 'donde', 'quien', 'cual', 'cuanto', 'cuantos', 'tengo', 'tienes', 'tiene', 'hay', 'hacer', 'puedo', 'puedes', 'puede', 'soy', 'eres', 'esta', 'estan', 'estamos', 'ser', 'estar', 'haber', 'tener', 'hola', 'buenos', 'dias', 'tardes', 'noches'}
        
        keywords = [w.lower() for w in query.split() if len(w) > 2 and w.lower() not in stop_words]
        
        if not keywords:
            # Fallback si todo eran stop words
            keywords = [query.strip().lower()]

        # 2. Construir condiciones OR (basta que coincida una palabra clave importante)
        conditions = []
        for k in keywords:
            term = f"%{k}%"
            conditions.append(func.lower(FAQEntry.pregunta_clave).like(term))
            conditions.append(func.lower(FAQEntry.ejemplo_pregunta_cliente).like(term))
            # Opcional: buscar en respuesta también, pero puede dar falsos positivos
            # conditions.append(func.lower(FAQEntry.respuesta).like(term))

        results = db.query(FAQEntry).filter(
            FAQEntry.activa == True,
            or_(*conditions)
        ).order_by(FAQEntry.veces_usada.desc(), FAQEntry.created_at.desc()).limit(limit).all()

        for faq in results:
            faq.veces_usada += 1
        if results:
            db.commit()

        return results
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error al buscar entradas FAQ")
        raise HTTPException(status_code=500, detail="Error interno al buscar entradas FAQ. Intente nuevamente o contacte al administrador.")


@router.post("", response_model=FAQEntryResponse, status_code=201, dependencies=[Depends(check_permission("settings:edit"))])
def create_faq_entry(
    faq_entry: FAQEntryCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("settings:edit"))
):
    """
    Crea una nueva entrada FAQ.
    
    Args:
        - faq_entry: Datos de la entrada FAQ a crear
        
    Returns:
        Entrada FAQ creada
        
    Raises:
        - 400: Si la pregunta clave o respuesta están vacías
        - 500: Si ocurre un error al crear la entrada
    """
    if not faq_entry.pregunta_clave.strip():
        raise HTTPException(status_code=400, detail="La pregunta clave no puede estar vacía")
    if not faq_entry.respuesta.strip():
        raise HTTPException(status_code=400, detail="La respuesta no puede estar vacía")

    try:
        db_faq = FAQEntry(**faq_entry.model_dump())
        db.add(db_faq)
        db.commit()
        db.refresh(db_faq)
        return db_faq
    except Exception as e:
        db.rollback()
        logger.exception("Error al crear entrada FAQ")
        raise HTTPException(status_code=500, detail="Error interno al crear entrada FAQ. Intente nuevamente o contacte al administrador.")


@router.get("/{faq_id}", response_model=FAQEntryResponse, dependencies=[Depends(check_permission("settings:view"))])
def get_faq_entry(faq_id: int, db: Session = Depends(get_db)):
    """
    Obtiene una entrada FAQ por su ID.
    
    Args:
        - faq_id: ID de la entrada FAQ
        
    Returns:
        Entrada FAQ solicitada
        
    Raises:
        - 404: Si la entrada FAQ no existe
    """
    faq_entry = db.query(FAQEntry).filter(FAQEntry.id == faq_id).first()
    if not faq_entry:
        raise HTTPException(status_code=404, detail=f"La entrada FAQ con ID {faq_id} no fue encontrada")

    return faq_entry


@router.patch("/{faq_id}", response_model=FAQEntryResponse, dependencies=[Depends(check_permission("settings:edit"))])
def update_faq_entry(
    faq_id: int, 
    updates: FAQEntryUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("settings:edit"))
):
    """
    Actualiza una entrada FAQ existente.
    
    Args:
        - faq_id: ID de la entrada FAQ a actualizar
        - updates: Campos a modificar
        
    Returns:
        Entrada FAQ actualizada
        
    Raises:
        - 404: Si la entrada FAQ no existe
        - 400: Si se intenta establecer pregunta_clave o respuesta vacías
        - 500: Si ocurre un error al actualizar
    """
    faq_entry = db.query(FAQEntry).filter(FAQEntry.id == faq_id).first()
    if not faq_entry:
        raise HTTPException(status_code=404, detail=f"La entrada FAQ con ID {faq_id} no fue encontrada")

    if updates.pregunta_clave is not None:
        if not updates.pregunta_clave.strip():
            raise HTTPException(status_code=400, detail="La pregunta clave no puede estar vacía")
        faq_entry.pregunta_clave = updates.pregunta_clave
    if updates.ejemplo_pregunta_cliente is not None:
        faq_entry.ejemplo_pregunta_cliente = updates.ejemplo_pregunta_cliente
    if updates.respuesta is not None:
        if not updates.respuesta.strip():
            raise HTTPException(status_code=400, detail="La respuesta no puede estar vacía")
        faq_entry.respuesta = updates.respuesta
    if updates.categoria is not None:
        faq_entry.categoria = updates.categoria
    if updates.nivel_seriedad is not None:
        faq_entry.nivel_seriedad = updates.nivel_seriedad
    if updates.activa is not None:
        faq_entry.activa = updates.activa

    try:
        db.commit()
        db.refresh(faq_entry)
        return faq_entry
    except Exception as e:
        db.rollback()
        logger.exception("Error al actualizar entrada FAQ")
        raise HTTPException(status_code=500, detail="Error interno al actualizar entrada FAQ. Intente nuevamente o contacte al administrador.")


@router.delete("/{faq_id}", status_code=204, dependencies=[Depends(check_permission("settings:edit"))])
def delete_faq_entry(
    faq_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("settings:edit"))
):
    """
    Elimina una entrada FAQ del sistema.
    
    Args:
        - faq_id: ID de la entrada FAQ a eliminar
        
    Returns:
        No content (204)
        
    Raises:
        - 404: Si la entrada FAQ no existe
        - 500: Si ocurre un error al eliminar
    """
    faq_entry = db.query(FAQEntry).filter(FAQEntry.id == faq_id).first()
    if not faq_entry:
        raise HTTPException(
            status_code=404,
            detail=f"La entrada FAQ con ID {faq_id} no fue encontrada"
        )
    
    try:
        db.delete(faq_entry)
        db.commit()
        return None
    except Exception as e:
        db.rollback()
        logger.exception("Error al eliminar entrada FAQ")
        raise HTTPException(status_code=500, detail="Error interno al eliminar entrada FAQ. Intente nuevamente o contacte al administrador.")
