from decimal import Decimal
from types import SimpleNamespace

from app.routers.order_state_integrity import _build_financially_safe_edit_items


def _current_item(*, item_id: int, product_id: int, quantity: int, price: str, gift: bool):
    return SimpleNamespace(
        id=item_id,
        product_id=product_id,
        cantidad=quantity,
        precio_unitario=Decimal(price),
        es_regalo_promocion=gift,
    )


def _requested_item(*, product_id: int, quantity: int, imeis=None):
    return SimpleNamespace(
        product_id=product_id,
        cantidad=quantity,
        imeis=imeis,
    )


def test_edit_preserves_existing_discount_but_not_for_added_quantity():
    safe = _build_financially_safe_edit_items(
        [
            _current_item(
                item_id=1,
                product_id=10,
                quantity=1,
                price="9600.00",
                gift=False,
            )
        ],
        [
            _requested_item(
                product_id=10,
                quantity=2,
                imeis=["111111111111111", "222222222222222"],
            )
        ],
    )

    assert len(safe) == 2
    assert safe[0]["cantidad"] == 1
    assert safe[0]["precio_unitario"] == Decimal("9600.00")
    assert safe[0]["es_regalo_promocion"] is False
    assert safe[0]["imeis"] == ["111111111111111"]

    assert safe[1]["cantidad"] == 1
    assert safe[1]["precio_unitario"] is None
    assert safe[1]["es_regalo_promocion"] is False
    assert safe[1]["imeis"] == ["222222222222222"]


def test_edit_preserves_existing_gift_but_does_not_multiply_it():
    safe = _build_financially_safe_edit_items(
        [
            _current_item(
                item_id=1,
                product_id=20,
                quantity=1,
                price="500.00",
                gift=True,
            )
        ],
        [_requested_item(product_id=20, quantity=3)],
    )

    assert safe[0]["cantidad"] == 1
    assert safe[0]["es_regalo_promocion"] is True
    assert safe[0]["precio_unitario"] == Decimal("500.00")

    assert safe[1]["cantidad"] == 2
    assert safe[1]["es_regalo_promocion"] is False
    assert safe[1]["precio_unitario"] is None


def test_new_product_never_inherits_terms_from_another_product():
    safe = _build_financially_safe_edit_items(
        [
            _current_item(
                item_id=1,
                product_id=10,
                quantity=1,
                price="9600.00",
                gift=False,
            )
        ],
        [_requested_item(product_id=99, quantity=1)],
    )

    assert safe == [
        {
            "product_id": 99,
            "cantidad": 1,
            "precio_unitario": None,
            "es_regalo_promocion": False,
            "imeis": None,
        }
    ]
