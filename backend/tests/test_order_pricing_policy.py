from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.utils.order_pricing import enforce_sale_price_policy


def _item(*, base: str = "10000.00", sale: str = "10000.00", gift: bool = False):
    product = SimpleNamespace(
        precio=Decimal(base),
        nombre="iPhone de prueba",
        sku="TEST-001",
    )
    return SimpleNamespace(
        product=product,
        precio_unitario=Decimal(sale),
        es_regalo_promocion=gift,
    )


def _user(*, owner: bool = False):
    return SimpleNamespace(is_superuser=owner)


def test_catalog_price_is_allowed():
    enforce_sale_price_policy([_item()], current_user=_user())


def test_unauthenticated_manual_discount_is_rejected():
    with pytest.raises(HTTPException) as exc:
        enforce_sale_price_policy([_item(sale="9800.00")], current_user=None)

    assert exc.value.status_code == 403
    assert "sin un usuario autenticado" in str(exc.value.detail)


def test_two_percent_discount_is_allowed_with_gift():
    enforce_sale_price_policy(
        [
            _item(sale="9800.00"),
            _item(base="500.00", sale="500.00", gift=True),
        ],
        current_user=_user(),
    )


def test_more_than_two_percent_is_rejected_when_order_has_gift():
    with pytest.raises(HTTPException) as exc:
        enforce_sale_price_policy(
            [
                _item(sale="9700.00"),
                _item(base="500.00", sale="500.00", gift=True),
            ],
            current_user=_user(),
        )

    assert exc.value.status_code == 403
    assert "solo admite hasta 2%" in str(exc.value.detail)


def test_three_percent_discount_is_allowed_without_gifts():
    enforce_sale_price_policy([_item(sale="9700.00")], current_user=_user())


def test_discount_above_three_percent_requires_owner():
    with pytest.raises(HTTPException) as exc:
        enforce_sale_price_policy([_item(sale="9699.00")], current_user=_user())

    assert exc.value.status_code == 403
    assert "requiere aprobación del propietario" in str(exc.value.detail)


def test_four_percent_discount_is_allowed_for_owner_without_gifts():
    enforce_sale_price_policy(
        [_item(sale="9600.00")],
        current_user=_user(owner=True),
    )


def test_four_percent_discount_is_rejected_for_non_owner():
    with pytest.raises(HTTPException) as exc:
        enforce_sale_price_policy(
            [_item(sale="9600.00")],
            current_user=_user(owner=False),
        )

    assert exc.value.status_code == 403


def test_discount_above_four_percent_is_rejected_even_for_owner():
    with pytest.raises(HTTPException) as exc:
        enforce_sale_price_policy(
            [_item(sale="9599.00")],
            current_user=_user(owner=True),
        )

    assert exc.value.status_code == 403
    assert "máximo permitido del 4%" in str(exc.value.detail)


def test_manual_price_above_catalog_is_rejected():
    with pytest.raises(HTTPException) as exc:
        enforce_sale_price_policy(
            [_item(sale="10000.01")],
            current_user=_user(owner=True),
        )

    assert exc.value.status_code == 400
    assert "no puede superar el precio de catálogo" in str(exc.value.detail)
