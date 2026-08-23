from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routers.imeis import (
    _build_imei_status,
    _build_warranty_expiration,
    _validate_imei_digits,
)


def test_validate_imei_digits_trims_and_accepts_exact_15_digits():
    assert _validate_imei_digits(" 123456789012345 ") == "123456789012345"


@pytest.mark.parametrize(
    "value",
    [
        "12345678901234",
        "1234567890123456",
        "12345678901234A",
        "",
        "   ",
    ],
)
def test_validate_imei_digits_rejects_non_15_digit_values(value):
    with pytest.raises(HTTPException) as exc_info:
        _validate_imei_digits(value)

    assert exc_info.value.status_code == 400
    assert "15 dígitos" in exc_info.value.detail


def test_build_imei_status_prioritizes_transfer_then_sale_then_stock():
    assert _build_imei_status(SimpleNamespace(transfer_id=8, vendido=True)) == "en_transito"
    assert _build_imei_status(SimpleNamespace(transfer_id=None, vendido=True)) == "vendido"
    assert _build_imei_status(SimpleNamespace(transfer_id=None, vendido=False)) == "en_stock"


def test_build_warranty_expiration_requires_sale_product_and_positive_warranty():
    sold_at = datetime(2026, 8, 23, 10, 0)

    record = SimpleNamespace(
        sold_at=sold_at,
        product=SimpleNamespace(garantia_meses=12),
    )
    assert _build_warranty_expiration(record) == sold_at + timedelta(days=360)

    assert _build_warranty_expiration(SimpleNamespace(sold_at=None, product=record.product)) is None
    assert _build_warranty_expiration(SimpleNamespace(sold_at=sold_at, product=None)) is None
    assert _build_warranty_expiration(
        SimpleNamespace(sold_at=sold_at, product=SimpleNamespace(garantia_meses=0))
    ) is None
