"""Esquemas endurecidos para edición de órdenes.

La edición operativa permite cambiar productos, cantidades e IMEIs. Los campos
financieros enviados por clientes antiguos se aceptan por compatibilidad pero se
neutralizan antes de entrar al flujo de stock. El endpoint canónico reconstruye
los términos válidos desde la orden persistida y el catálogo del backend.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import Field, model_validator

from .order import OrderItemUpdate as BaseOrderItemUpdate
from .order import OrderUpdate as BaseOrderUpdate


class OrderItemUpdate(BaseOrderItemUpdate):
    """Ítem editable cuyos overrides financieros del cliente no tienen efecto."""

    @model_validator(mode="after")
    def neutralize_client_financial_overrides(self):
        # Compatibilidad: clientes antiguos todavía pueden enviar estos campos.
        # No fallamos la petición, pero tampoco permitimos que controlen el precio,
        # el costo o la condición de regalo de la orden persistida.
        self.precio_unitario = None
        self.costo_unitario = None
        self.es_regalo_promocion = False
        return self


class OrderUpdate(BaseOrderUpdate):
    """Actualización de orden que usa ítems con campos financieros protegidos."""

    items: Optional[List[OrderItemUpdate]] = Field(None, min_length=1)


__all__ = ["OrderItemUpdate", "OrderUpdate"]
