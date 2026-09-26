"""Esquemas endurecidos para edición de órdenes.

La edición operativa permite cambiar productos, cantidades e IMEIs, pero no
acepta precio, costo ni condición de regalo/promoción inyectados por el cliente.
Los precios se reconstruyen siempre desde el catálogo del backend. Los descuentos
y regalías se autorizan al crear la venta, donde pasan por la política central.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import Field, model_validator

from .order import OrderItemUpdate as BaseOrderItemUpdate
from .order import OrderUpdate as BaseOrderUpdate


class OrderItemUpdate(BaseOrderItemUpdate):
    """Ítem editable sin capacidad de alterar precio, costo o regalías."""

    @model_validator(mode="after")
    def reject_client_financial_overrides(self):
        if self.precio_unitario is not None:
            raise ValueError(
                "precio_unitario no puede modificarse al editar una orden; "
                "el backend usa el precio vigente de catálogo"
            )
        if self.costo_unitario is not None:
            raise ValueError(
                "costo_unitario no puede modificarse desde la edición de órdenes"
            )
        if self.es_regalo_promocion:
            raise ValueError(
                "es_regalo_promocion no puede activarse al editar una orden; "
                "las regalías deben autorizarse al crear la venta"
            )
        return self


class OrderUpdate(BaseOrderUpdate):
    """Actualización de orden que usa ítems con campos financieros protegidos."""

    items: Optional[List[OrderItemUpdate]] = Field(None, min_length=1)


__all__ = ["OrderItemUpdate", "OrderUpdate"]
