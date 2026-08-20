"""Cross-cutting order integrity rules.

These guards live at the SQLAlchemy transaction boundary so they also protect
Super Admin corrections, API integrations and future callers that bypass the
normal UI/router helpers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import json
from typing import Any, Iterable

from fastapi import HTTPException
from sqlalchemy import event, func, inspect as sa_inspect
from sqlalchemy.orm import Session


FINAL_SALE_STATUSES = {"completada", "validada"}
_INSTALLED = False


def normalize_transfer_reference(reference: str | None) -> str | None:
    if reference is None:
        return None
    raw = str(reference).strip().upper()
    if not raw:
        return None
    normalized = "".join(char for char in raw if char.isalnum())
    return normalized or None


def _payment_entries(raw: Any) -> list[dict[str, Any]]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=400, detail="El desglose de pagos no es JSON válido") from exc
    else:
        parsed = raw

    if not isinstance(parsed, list):
        raise HTTPException(status_code=400, detail="El desglose de pagos debe ser una lista")

    entries: list[dict[str, Any]] = []
    for item in parsed:
        if hasattr(item, "model_dump"):
            item = item.model_dump()
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail="Cada pago del desglose debe ser un objeto válido")
        method = item.get("method")
        if hasattr(method, "value"):
            method = method.value
        entries.append({**item, "method": str(method or "")})
    return entries


def payment_breakdown_total(raw: Any) -> Decimal:
    total = Decimal("0.00")
    for entry in _payment_entries(raw):
        try:
            amount = Decimal(str(entry.get("amount")))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="El desglose contiene un monto inválido") from exc
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Cada monto del desglose debe ser mayor a cero")
        total += amount
    return total.quantize(Decimal("0.01"))


def validate_payment_breakdown_total(raw: Any, expected_total: Any) -> None:
    entries = _payment_entries(raw)
    if not entries:
        return
    try:
        expected = Decimal(str(expected_total or 0)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="El total de la orden no es válido") from exc
    actual = payment_breakdown_total(entries)
    if abs(actual - expected) > Decimal("0.01"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"La suma del desglose de pagos ({actual:.2f}) debe coincidir "
                f"con el total de la orden ({expected:.2f})."
            ),
        )


def effective_sale_at(order: Any) -> datetime | None:
    """Return the best available timestamp for when revenue became final."""
    return getattr(order, "completed_at", None) or getattr(order, "validada_at", None) or getattr(order, "created_at", None)


def effective_sale_column(Order: Any):
    """SQL expression equivalent of :func:`effective_sale_at` for reports."""
    return func.coalesce(Order.completed_at, Order.validada_at, Order.created_at)


def _validate_transfer_integrity(session: Session, order: Any, entries: Iterable[dict[str, Any]]) -> None:
    from app.models import Order

    transfer_entries = [entry for entry in entries if entry.get("method") == "transferencia"]
    uses_transfer = getattr(order, "metodo_pago", None) == "transferencia" or bool(transfer_entries)
    if not uses_transfer:
        order.transfer_reference_normalized = None
        return

    entry = transfer_entries[0] if transfer_entries else {}
    bank_name = (getattr(order, "transfer_bank_name", None) or entry.get("bank_name") or "").strip()
    reference = (getattr(order, "transfer_reference", None) or entry.get("reference") or "").strip()
    if not bank_name:
        raise HTTPException(status_code=400, detail="Debe indicar el banco cuando hay pago por transferencia")
    if not reference:
        raise HTTPException(status_code=400, detail="Debe indicar la referencia cuando hay pago por transferencia")

    normalized = normalize_transfer_reference(reference)
    if not normalized:
        raise HTTPException(status_code=400, detail="La referencia de transferencia no es válida")

    order.transfer_bank_name = bank_name
    order.transfer_reference = reference
    order.transfer_reference_normalized = normalized

    with session.no_autoflush:
        duplicate_query = session.query(Order.id).filter(Order.transfer_reference_normalized == normalized)
        if getattr(order, "id", None) is not None:
            duplicate_query = duplicate_query.filter(Order.id != order.id)
        duplicate = duplicate_query.first()
    if duplicate:
        raise HTTPException(status_code=409, detail="La referencia de transferencia ya fue utilizada en otra orden")


def _guard_order(session: Session, order: Any) -> None:
    from app.models import Return

    state = sa_inspect(order)
    status_history = state.attrs.estado.history
    old_status = status_history.deleted[0] if status_history.deleted else None
    new_status = getattr(order, "estado", None)

    if new_status in FINAL_SALE_STATUSES and getattr(order, "completed_at", None) is None:
        order.completed_at = datetime.now(UTC)

    if status_history.has_changes() and new_status == "cancelada" and old_status in FINAL_SALE_STATUSES:
        if getattr(order, "id", None) is not None:
            with session.no_autoflush:
                has_return = session.query(Return.id).filter(Return.order_id == order.id).first()
            if has_return:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "No se puede cancelar una venta que ya tiene devoluciones. "
                        "Use únicamente el flujo de devoluciones/garantías para evitar reponer inventario dos veces."
                    ),
                )

    entries = _payment_entries(getattr(order, "payment_breakdown", None))
    if entries:
        validate_payment_breakdown_total(entries, getattr(order, "total", None))
    _validate_transfer_integrity(session, order, entries)


def _before_flush(session: Session, flush_context: Any, instances: Any) -> None:  # noqa: ARG001
    from app.models import Order

    candidates = set(session.new).union(session.dirty)
    for candidate in candidates:
        if isinstance(candidate, Order):
            _guard_order(session, candidate)


def install_order_integrity_guards() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    event.listen(Session, "before_flush", _before_flush)
    _INSTALLED = True
