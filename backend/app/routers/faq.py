from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.database import get_db
from app.models import FAQEntry
from app.schemas import FAQEntryCreate, FAQEntryResponse, FAQEntryUpdate

router = APIRouter()


@router.post("", response_model=FAQEntryResponse, status_code=201)
def create_faq_entry(faq_entry: FAQEntryCreate, db: Session = Depends(get_db)):
    if not faq_entry.pregunta_clave.strip():
        raise HTTPException(status_code=400, detail="La pregunta clave no puede estar vacía")
    if not faq_entry.respuesta.strip():
        raise HTTPException(status_code=400, detail="La respuesta no puede estar vacía")

    db_faq = FAQEntry(**faq_entry.model_dump())
    db.add(db_faq)
    db.commit()
    db.refresh(db_faq)

    return db_faq


@router.get("/{faq_id}", response_model=FAQEntryResponse)
def get_faq_entry(faq_id: int, db: Session = Depends(get_db)):
    faq_entry = db.query(FAQEntry).filter(FAQEntry.id == faq_id).first()
    if not faq_entry:
        raise HTTPException(status_code=404, detail=f"La entrada FAQ con ID {faq_id} no fue encontrada")

    return faq_entry


@router.get("/search", response_model=List[FAQEntryResponse])
def search_faq_entries(
    query: str = Query(..., description="Texto de la pregunta del cliente"),
    limit: int = Query(3, description="Número máximo de resultados"),
    db: Session = Depends(get_db)
):
    if not query.strip():
        raise HTTPException(status_code=400, detail="El parámetro 'query' no puede estar vacío")

    search_term = f"%{query.strip().lower()}%"

    results = db.query(FAQEntry).filter(
        FAQEntry.activa == True,
        or_(
            func.lower(FAQEntry.pregunta_clave).like(search_term),
            func.lower(FAQEntry.ejemplo_pregunta_cliente).like(search_term)
        )
    ).order_by(FAQEntry.veces_usada.desc(), FAQEntry.created_at.desc()).limit(limit).all()

    for faq in results:
        faq.veces_usada += 1
    if results:
        db.commit()

    return results


@router.patch("/{faq_id}", response_model=FAQEntryResponse)
def update_faq_entry(faq_id: int, updates: FAQEntryUpdate, db: Session = Depends(get_db)):
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

    db.commit()
    db.refresh(faq_entry)

    return faq_entry
