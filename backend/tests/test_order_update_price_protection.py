import pytest
from pydantic import ValidationError

from app.schemas import OrderUpdate


def test_order_update_accepts_operational_item_fields_without_price():
    update = OrderUpdate.model_validate(
        {
            "items": [
                {
                    "product_id": 10,
                    "cantidad": 2,
                    "imeis": ["111111111111111", "222222222222222"],
                }
            ]
        }
    )

    assert update.items is not None
    assert update.items[0].product_id == 10
    assert update.items[0].cantidad == 2
    assert update.items[0].precio_unitario is None
    assert update.items[0].costo_unitario is None
    assert update.items[0].es_regalo_promocion is False


def test_order_update_rejects_client_supplied_unit_price():
    with pytest.raises(ValidationError) as exc:
        OrderUpdate.model_validate(
            {
                "items": [
                    {
                        "product_id": 10,
                        "cantidad": 1,
                        "precio_unitario": "1.00",
                    }
                ]
            }
        )

    assert "precio_unitario no puede modificarse" in str(exc.value)


def test_order_update_rejects_client_supplied_unit_cost():
    with pytest.raises(ValidationError) as exc:
        OrderUpdate.model_validate(
            {
                "items": [
                    {
                        "product_id": 10,
                        "cantidad": 1,
                        "costo_unitario": "1.00",
                    }
                ]
            }
        )

    assert "costo_unitario no puede modificarse" in str(exc.value)


def test_order_update_rejects_gift_flag_injection():
    with pytest.raises(ValidationError) as exc:
        OrderUpdate.model_validate(
            {
                "items": [
                    {
                        "product_id": 10,
                        "cantidad": 1,
                        "es_regalo_promocion": True,
                    }
                ]
            }
        )

    assert "es_regalo_promocion no puede activarse" in str(exc.value)
