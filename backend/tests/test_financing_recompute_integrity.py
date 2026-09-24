import json
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Bank, FinancingOption, Order, OrderItem
from app.utils.order_financing import recompute_financing_from_details

from .helpers import seed_location_and_sales_profile, seed_product


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


def test_item_edit_with_corrupt_financing_fails_without_mutating_order(
    client: TestClient,
    db_session: Session,
):
    suffix = uuid4().hex[:10]
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(
        client,
        location.id,
        stock_inicial=4,
        is_serialized=False,
        categoria="accesorio",
    )

    bank = Bank(
        name=f"Banco edición {suffix}",
        active=True,
        normal_card_rate=Decimal("0.05"),
    )
    db_session.add(bank)
    db_session.flush()
    db_session.add(
        FinancingOption(
            bank_id=bank.id,
            months=12,
            rate=Decimal("0.10"),
            active=True,
        )
    )
    db_session.commit()

    created = client.post(
        "/api/orders",
        json={
            "sales_profile_slug": sales_profile.slug,
            "source_location_id": location.id,
            "canal": "tienda",
            "customer_name": "Cliente financiamiento corrupto",
            "customer_phone": "73334444",
            "metodo_pago": "financiamiento",
            "items": [
                {
                    "product_id": product["id"],
                    "cantidad": 1,
                    "precio_unitario": 1000,
                }
            ],
            "financing_data": {
                "bank_id": bank.id,
                "months": 12,
                "down_payment": 0,
            },
        },
    )
    assert created.status_code == 201, created.text
    order_id = int(created.json()["id"])

    order = db_session.query(Order).filter(Order.id == order_id).one()
    original_total = Decimal(str(order.total))
    original_quantity = (
        db_session.query(OrderItem)
        .filter(OrderItem.order_id == order_id, OrderItem.product_id == product["id"])
        .one()
        .cantidad
    )
    order.financing_details = "{legacy-corrupt"
    db_session.commit()

    response = client.put(
        f"/api/orders/{order_id}",
        json={
            "items": [
                {
                    "product_id": product["id"],
                    "cantidad": 2,
                    "precio_unitario": 1000,
                }
            ]
        },
    )
    assert response.status_code == 409, response.text
    assert "detalles de financiamiento guardados son inválidos" in response.json()["detail"].lower()

    db_session.expire_all()
    persisted_order = db_session.query(Order).filter(Order.id == order_id).one()
    persisted_item = (
        db_session.query(OrderItem)
        .filter(OrderItem.order_id == order_id, OrderItem.product_id == product["id"])
        .one()
    )
    assert Decimal(str(persisted_order.total)) == original_total
    assert persisted_order.financing_details == "{legacy-corrupt"
    assert persisted_item.cantidad == original_quantity == 1
