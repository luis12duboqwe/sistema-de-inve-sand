"""Esquemas y utilidades compartidas entre dominios."""

from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Respuesta genérica para listados paginados."""

    items: List[T]
    total: int
    page: int
    per_page: int
    pages: int
