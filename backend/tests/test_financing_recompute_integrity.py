import json
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.utils.order_financing import recompute_financing_from_details


def test_recompute_preserves_financing_formula_for_valid_persisted_details():
    details = json.dumps(
        {
            "bank_id": 7,
            "bank_name": "Banco Histórico",
            "months": "12",
            "rate": "0.10",
            "down_payment": "1000.00",
        }
    )

    total, recomputed = recompute_financing_from_details(
        financing_details=details,
        metodo_pago="financiamiento",
        total_after_tradeins=Decimal("10000.00"),
    )

    assert total == Decimal("10900.0000")
    assert recomputed is not None
    parsed = json.loads(recomputed)
    assert parsed["months"] == 12
    assert parsed["rate"] == 0.1
    assert parsed["down_payment"] == 1000.0
    assert parsed["financed_amount"] == 9000.0
    assert parsed["surcharge"] == 900.0
    assert parsed["monthly_payment"] == 825.0


@pytest.mark.parametrize(
    "details",
    [
        "{not-json",
        "[]",
        json.dumps({"months": 12, "down_payment": 0}),
        json.dumps({"months": "12.5", "rate": "0.10", "down_payment": 0}),
        json.dumps({"months": 12, "rate": "NaN", "down_payment": 0}),
        json.dumps({"months": 12, "rate": "-0.10", "down_payment": 0}),
        json.dumps({"months": 12, "rate": "0.10", "down_payment": "no-numero"}),
        json.dumps({"months": 12, "rate": "0.10", "down_payment": "10000.01"}),
    ],
)
def test_recompute_rejects_corrupt_persisted_financing_instead_of_dropping_surcharge(details):
    with pytest.raises(HTTPException) as exc_info:
        recompute_financing_from_details(
            financing_details=details,
            metodo_pago="financiamiento",
            total_after_tradeins=Decimal("10000.00"),
        )

    assert exc_info.value.status_code == 409
    assert "detalles de financiamiento guardados son inválidos" in exc_info.value.detail.lower()


def test_switching_away_from_financing_does_not_require_parsing_historical_details():
    total, recomputed = recompute_financing_from_details(
        financing_details="{legacy-corrupt",
        metodo_pago="efectivo",
        total_after_tradeins=Decimal("10000.00"),
    )

    assert total == Decimal("10000.00")
    assert recomputed is None
