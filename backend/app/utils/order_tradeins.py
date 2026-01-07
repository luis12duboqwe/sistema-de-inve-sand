from decimal import Decimal
from typing import Iterable


def compute_trade_in_total(trade_ins: Iterable) -> Decimal:
    """Suma valor_estimado de trade-ins en forma segura.

    trade_ins puede ser una lista de esquemas o modelos con atributo valor_estimado.
    """
    total = Decimal("0.00")
    for trade_in in trade_ins or []:
        try:
            total += Decimal(str(getattr(trade_in, "valor_estimado", 0) or 0))
        except Exception:
            continue
    return total
