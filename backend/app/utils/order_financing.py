from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, Optional, Tuple, Sequence

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


def _compute_mixed_card_payment(
    payment_breakdown: Sequence[Any],
    total_before_surcharge: Decimal,
    card_rate: Decimal,
) -> tuple[Decimal, Decimal, Decimal] | None:
    """Return (gross total, card base, surcharge) if a card splits with other methods.

    The client sends gross card amount INCLUDING card-only surcharge; cash and
    bank transfer are amounts actually collected. Never tax cash/transfer with
    the card rate. Exact cent reconciliation is mandatory.
    """
    if not payment_breakdown:
        return None

    entries: list[tuple[str, Decimal]] = []
    for item in payment_breakdown:
        method = getattr(item, "method", None)
        if isinstance(item, dict):
            method = item.get("method")
        method = str(getattr(method, "value", method) or "")
        raw_amount = item.get("amount") if isinstance(item, dict) else getattr(item, "amount", None)
        try:
            amount = Decimal(str(raw_amount))
        except (TypeError, InvalidOperation) as exc:
            raise HTTPException(status_code=400, detail="Monto de pago mixto inválido") from exc
        if not amount.is_finite() or amount <= 0:
            raise HTTPException(status_code=400, detail="Monto de pago mixto inválido")
        entries.append((method, amount))

    card_amounts = [amount for method, amount in entries if method == "tarjeta"]
    non_card_amounts = [amount for method, amount in entries if method != "tarjeta"]
    if not card_amounts or not non_card_amounts:
        return None
    if len(card_amounts) != 1:
        raise HTTPException(status_code=400, detail="Un pago mixto solo puede incluir un cargo de tarjeta")

    non_card = sum(non_card_amounts, Decimal("0.00"))
    card_base = total_before_surcharge - non_card
    if card_base <= 0:
        raise HTTPException(status_code=400, detail="La porción de tarjeta debe ser mayor que cero")

    cents = Decimal("0.01")
    surcharge = (card_base * card_rate).quantize(cents, rounding=ROUND_HALF_UP)
    gross_card_expected = (card_base + surcharge).quantize(cents, rounding=ROUND_HALF_UP)
    gross_card_actual = card_amounts[0].quantize(cents, rounding=ROUND_HALF_UP)
    if gross_card_actual != gross_card_expected:
        raise HTTPException(
            status_code=400,
            detail=f"El cobro bruto de tarjeta debe ser {gross_card_expected:.2f}, no {gross_card_actual:.2f}",
        )
    return (total_before_surcharge + surcharge).quantize(cents), card_base, surcharge


def compute_financing_from_payload(
    db: Session,
    financing_data: Optional[Dict[str, Any]],
    metodo_pago: str,
    total_after_tradeins: Decimal,
    trade_in_total: Decimal,
    payment_breakdown: Optional[Sequence[Any]] = None,
) -> Tuple[Decimal, Optional[str]]:
    """Calcula financiamiento a partir del payload de la orden.

    Devuelve (total_actualizado, financing_details_json) manteniendo el formato existente.
    """
    if not financing_data:
        return total_after_tradeins, None

    has_mixed_card = bool(
        payment_breakdown
        and any(str(getattr(getattr(p, "method", None), "value", getattr(p, "method", ""))) == "tarjeta"
                for p in payment_breakdown)
        and any(str(getattr(getattr(p, "method", None), "value", getattr(p, "method", ""))) != "tarjeta"
                for p in payment_breakdown)
    )
    if metodo_pago not in FINANCING_METHODS and not has_mixed_card:
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

    if has_mixed_card:
        if months != 0 or down_payment != 0:
            raise HTTPException(
                status_code=400,
                detail="Pagos mixtos con tarjeta normal no admiten plazos ni prima adicionales",
            )
        reconciled = _compute_mixed_card_payment(
            payment_breakdown or [], total_after_tradeins, Decimal(str(bank.normal_card_rate)),
        )
        if reconciled is None:
            raise HTTPException(status_code=400, detail="Desglose de tarjeta mixta inválido")
        mixed_total, card_base, mixed_surcharge = reconciled
        non_card = total_after_tradeins - card_base
        return mixed_total, json.dumps({
            "bank_id": bank_id,
            "bank_name": bank.name,
            "months": 0,
            "rate": float(bank.normal_card_rate),
            "surcharge": float(mixed_surcharge),
            "monthly_payment": float(card_base + mixed_surcharge),
            "original_total": float(total_after_tradeins + trade_in_total),
            "down_payment": float(non_card),
            "financed_amount": float(card_base),
            "mixed_card_payment": True,
        })

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