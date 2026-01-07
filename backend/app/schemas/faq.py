"""Schemas para entradas de preguntas frecuentes (FAQ)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class FAQEntryCreate(BaseModel):
    """Campos requeridos para crear una entrada FAQ."""

    pregunta_clave: str
    ejemplo_pregunta_cliente: Optional[str] = None
    respuesta: str
    categoria: str
    nivel_seriedad: str = "normal"
    activa: bool = True
    created_by: Optional[str] = None


class FAQEntryUpdate(BaseModel):
    """Campos editables para una entrada FAQ."""

    pregunta_clave: Optional[str] = None
    ejemplo_pregunta_cliente: Optional[str] = None
    respuesta: Optional[str] = None
    categoria: Optional[str] = None
    nivel_seriedad: Optional[str] = None
    activa: Optional[bool] = None


class FAQEntryResponse(BaseModel):
    """Respuesta serializada para entradas FAQ."""

    id: int
    pregunta_clave: str
    ejemplo_pregunta_cliente: Optional[str]
    respuesta: str
    categoria: str
    nivel_seriedad: str
    activa: bool
    veces_usada: int
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
