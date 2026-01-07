"""Schemas expuestos en endpoints públicos (catálogo, landing)."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from .product import CategoriaEnum, CondicionEnum


class PublicProductResponse(BaseModel):
    id: int
    nombre: str
    marca: str
    modelo: str
    categoria: CategoriaEnum
    condicion: CondicionEnum
    precio: Decimal
    moneda: str
    capacidad: Optional[str] = None
    color: Optional[str] = None
    in_stock: bool

    model_config = ConfigDict(from_attributes=True)
