from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Bank, FinancingOption


FINANCING_METHODS = {"tarjeta", "financiamiento"}


def _parse_positive_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise HTTPException(status_code=400, detail=f"{field_name} no es válido")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"{field_name} no es válido")
    if not parsed.is_finite() or parsed <= 0 or parsed != parsed.to_integral_value():
        raise HTTPException(status_code=400, detail=f"{field_name} no es válido")
    return int(parsed)


def _parse_financing_months(value: Any) -> int:
    if value in (None, "", 0, "0"):
        return 0
    if isinstance(value, bool):
        raise HTTPException(status_code=400, detail="El plazo de financiamiento no es válido")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="El plazo de financiamiento no es válido")
    if not parsed.is_finite() or parsed < 0 or parsed != parsed.to_integral_value():
        raise HTTPException(status_code=400, detail="El plazo de financiamiento no es válido")
    return int(parsed)


def _parse_down_payment(value: Any, total_after_tradeins: Decimal) -> Decimal:
    try:
        down_payment = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="La prima no es válida")
    if not down_payment.is_finite() or down_payment < 0:
        raise HTTPException(status_code=400, detail="La prima no puede ser negativa")
    if down_payment > total_after_tradeins:
        raise HTTPException(status_code=400, detail="La prima no puede exceder el total a pagar")
    return down_payment


def _invalid_persisted_financing() -> HTTPException:
    return HTTPException(
        status_code=409,
        detail=(
            "Los detalles de financiamiento guardados son inválidos. "
            "No se puede recalcular el total automáticamente; corrija el financiamiento "
            "antes de modificar los productos de la orden."
        ),
    )


def _parse_persisted_nonnegative_decimal(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise _invalid_persisted_financing()
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise _invalid_persisted_financing() from exc
    if not parsed.is_finite() or parsed < 0:
        raise _invalid_persisted_financing()
    return parsed


def _parse_persisted_months(value: Any) -> int:
    if value in (None, "", 0, "0"):
        return 0
    if isinstance(value, bool):
        raise _invalid_persisted_financing()
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise _invalid_persisted_financing() from exc
    if not parsed.is_finite() or parsed < 0 or parsed != parsed.to_integral_value():
        raise _invalid_persisted_financing()
    return int(parsed)


def compute_financing_from_payload(
    db: Session,
    financing_data: Optional[Dict[str, Any]],
    metodo_pago: str,
    total_after_tradeins: Decimal,
    trade_in_total: Decimal
) -> Tuple[Decimal, Optional[str]]:
    """Calcula financiamiento a partir del payload de la orden.

    Devuelve (total_actualizado, financing_details_json) manteniendo el formato existente.
    """
    if not financing_data:
        return total_after_tradeins, None

    if metodo_pago not in FINANCING_METHODS:
        raise HTTPException(
            status_code=400,
            detail="Datos de financiamiento solo válidos para pago con Tarjeta o Financiamiento"
        )

    bank_id_raw = financing_data.get("bank_id")
    if bank_id_raw in (None, ""):
        raise HTTPException(status_code=400, detail="Falta seleccionar el banco")
    bank_id = _parse_positive_int(bank_id_raw, "El banco")
    months = _parse_financing_months(financing_data.get("months"))
    down_payment = _parse_down_payment(financing_data.get("down_payment", 0), total_after_tradeins)

    bank = db.query(Bank).filter(Bank.id == bank_id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Banco no encontrado")
    if not bank.active:
        raise HTTPException(status_code=400, detail="El banco seleccionado está inactivo para nuevas ventas")

    amount_to_finance = total_after_tradeins - down_payment

    rate = Decimal("0.00")
    monthly_payment = Decimal("0.00")

    if months > 0:
        option = db.query(FinancingOption).filter(
            FinancingOption.bank_id == bank_id,
            FinancingOption.months == months,
            FinancingOption.active == True
        ).first()

        if not option:
            raise HTTPException(status_code=400, detail="Opción de financiamiento no válida o inactiva")

        rate = option.rate
        surcharge_amount = amount_to_finance * rate
        total_with_surcharge = amount_to_finance + surcharge_amount
        monthly_payment = total_with_surcharge / months

    else:
        rate = bank.normal_card_rate
        surcharge_amount = amount_to_finance * rate
        total_with_surcharge = amount_to_finance + surcharge_amount
        monthly_payment = total_with_surcharge

    updated_total = down_payment + total_with_surcharge

    financing_details_json = json.dumps({
        "bank_id": bank_id,
        "bank_name": bank.name,
        "months": months,
        "rate": float(rate),
        "surcharge": float(surcharge_amount),
        "monthly_payment": float(monthly_payment),
        "original_total": float(total_after_tradeins + trade_in_total),
        "down_payment": float(down_payment),
        "financed_amount": float(amount_to_finance)
    })

    return updated_total, financing_details_json


def recompute_financing_from_details(
    financing_details: Optional[str],
    metodo_pago: str,
    total_after_tradeins: Decimal
) -> Tuple[Decimal, Optional[str]]:
    """Recalcula financiamiento a partir de ``financing_details`` existente.

    Los datos persistidos son parte del valor monetario histórico de la orden. Si el
    JSON existe pero está corrupto, fallamos de forma cerrada en vez de eliminar el
    recargo silenciosamente durante una edición de productos.
    """
    if metodo_pago not in FINANCING_METHODS or not financing_details:
        return total_after_tradeins, None

    try:
        data = json.loads(financing_details)
    except (json.JSONDecodeError, TypeError) as exc:
        raise _invalid_persisted_financing() from exc

    if not isinstance(data, dict) or "rate" not in data:
        raise _invalid_persisted_financing()

    down_payment = _parse_persisted_nonnegative_decimal(
        data.get("down_payment", data.get("prima", 0) or 0)
    )
    rate = _parse_persisted_nonnegative_decimal(data["rate"])
    months = _parse_persisted_months(data.get("months", data.get("plazo", 0) or 0))
    bank_id = data.get("bank_id")
    bank_name = data.get("bank_name")

    if down_payment > total_after_tradeins:
        raise _invalid_persisted_financing()

    amount_to_finance = total_after_tradeins - down_payment

    try:
        surcharge_amount = amount_to_finance * rate
        total_with_surcharge = amount_to_finance + surcharge_amount
        if months > 0:
            monthly_payment = total_with_surcharge / Decimal(months)
        else:
            monthly_payment = total_with_surcharge
        total_final = down_payment + total_with_surcharge
    except (InvalidOperation, OverflowError, ValueError) as exc:
        raise _invalid_persisted_financing() from exc

    if not all(
        value.is_finite()
        for value in (
            amount_to_finance,
            surcharge_amount,
            total_with_surcharge,
            monthly_payment,
            total_final,
        )
    ):
        raise _invalid_persisted_financing()

    recomputed_financing = json.dumps({
        "bank_id": bank_id,
        "bank_name": bank_name,
        "months": months,
        "rate": float(rate),
        "surcharge": float(surcharge_amount),
        "monthly_payment": float(monthly_payment),
        "original_total": float(total_after_tradeins),
        "down_payment": float(down_payment),
        "financed_amount": float(amount_to_finance)
    })

    return total_final, recomputed_financing