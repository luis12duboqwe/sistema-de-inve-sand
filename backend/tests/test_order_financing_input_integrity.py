import json
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models import Bank, FinancingOption
from app.utils.order_financing import compute_financing_from_payload


def _bank_with_option(db_session):
    bank = Bank(name="Banco Integridad", active=True, normal_card_rate=Decimal("0.05"))
    db_session.add(bank)
    db_session.flush()
    option = FinancingOption(
        bank_id=bank.id,
        months=12,
        rate=Decimal("0.10"),
        active=True,
    )
    db_session.add(option)
    db_session.commit()
    return bank


def test_financing_rejects_negative_down_payment(db_session):
    bank = _bank_with_option(db_session)

    with pytest.raises(HTTPException) as exc_info:
        compute_financing_from_payload(
            db_session,
            {"bank_id": bank.id, "months": 12, "down_payment": "-1"},
            "financiamiento",
            Decimal("10000.00"),
            Decimal("0.00"),
        )

    assert exc_info.value.status_code == 400
    assert "prima" in exc_info.value.detail.lower()


def test_financing_rejects_down_payment_above_total(db_session):
    bank = _bank_with_option(db_session)

    with pytest.raises(HTTPException) as exc_info:
        compute_financing_from_payload(
            db_session,
            {"bank_id": bank.id, "months": 12, "down_payment": "10000.01"},
            "financiamiento",
            Decimal("10000.00"),
            Decimal("0.00"),
        )

    assert exc_info.value.status_code == 400
    assert "exceder" in exc_info.value.detail.lower()


@pytest.mark.parametrize(
    ("payload", "expected_fragment"),
    [
        ({"bank_id": "abc", "months": 12, "down_payment": 0}, "banco"),
        ({"bank_id": 1, "months": "12.5", "down_payment": 0}, "plazo"),
        ({"bank_id": 1, "months": -12, "down_payment": 0}, "plazo"),
        ({"bank_id": 1, "months": 12, "down_payment": "no-numero"}, "prima"),
    ],
)
def test_financing_rejects_malformed_untyped_payload_values(db_session, payload, expected_fragment):
    with pytest.raises(HTTPException) as exc_info:
        compute_financing_from_payload(
            db_session,
            payload,
            "financiamiento",
            Decimal("10000.00"),
            Decimal("0.00"),
        )

    assert exc_info.value.status_code == 400
    assert expected_fragment in exc_info.value.detail.lower()


def test_financing_accepts_numeric_strings_without_changing_formula(db_session):
    bank = _bank_with_option(db_session)

    total, details_json = compute_financing_from_payload(
        db_session,
        {"bank_id": str(bank.id), "months": "12", "down_payment": "1000.00"},
        "financiamiento",
        Decimal("10000.00"),
        Decimal("0.00"),
    )

    assert total == Decimal("10900.0000")
    details = json.loads(details_json)
    assert details["bank_id"] == bank.id
    assert details["months"] == 12
    assert details["down_payment"] == 1000.0
    assert details["financed_amount"] == 9000.0
    assert details["surcharge"] == 900.0
    assert details["monthly_payment"] == 825.0
