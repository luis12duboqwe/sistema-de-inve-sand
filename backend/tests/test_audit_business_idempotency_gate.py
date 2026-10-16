"""A rejected network response cannot be safely retried unless it has a stable identity."""
import pytest
from fastapi import HTTPException

from app.models import BusinessRequestKey
from app.utils.business_idempotency import claim_business_request, save_business_response


def test_business_creation_requires_stable_key_in_production_gate(db_session):
    with pytest.raises(HTTPException) as error:
        claim_business_request(
            db_session,
            key=None, require_key=True, identity_id=19,
            endpoint="POST /api/orders", payload={"total": 100},
        )
    assert error.value.status_code == 428
    assert db_session.query(BusinessRequestKey).count() == 0


def test_business_creation_key_replays_exact_result(db_session):
    options = dict(
        key="business-replay-2026", require_key=True,
        identity_id=19, endpoint="POST /api/orders",
        payload={"items": [{"id": 7}], "total": 100},
    )
    first = claim_business_request(db_session, **options)
    assert first.entry is not None
    assert first.replay is None
    save_business_response(first, {"id": 47, "total": 100})
    db_session.commit()

    again = claim_business_request(db_session, **options)
    assert again.replay == {"id": 47, "total": 100}
    assert again.entry is None

    with pytest.raises(HTTPException) as error:
        claim_business_request(db_session, **{**options, "payload": {"total": 200}})
    assert error.value.status_code == 409


def test_nonproduction_legacy_calls_can_use_unkeyed_requests(db_session):
    claim = claim_business_request(
        db_session,
        key=None, require_key=False, identity_id=5,
        endpoint="POST /api/stock-transfers", payload={"cantidad": 1},
    )
    assert claim.entry is None and claim.replay is None


def test_order_network_retry_replays_original_order_without_double_selling_imei(
    client, db_session,
):
    from uuid import uuid4
    from app.models import Order, ProductIMEI, Stock
    from .helpers import seed_location_and_sales_profile, seed_product

    location, profile = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id)
    payload = {
        "sales_profile_slug": profile.slug,
        "source_location_id": location.id,
        "canal": "tienda",
        "customer_name": "Pedido idempotente",
        "customer_phone": "50495550119",
        "metodo_pago": "efectivo",
        "items": [{
            "product_id": product["id"], "cantidad": 1,
            "precio_unitario": 1000,
            "imeis": ["111111111111111"],
        }],
    }
    key = f"order-{uuid4().hex}"
    headers = {"Idempotency-Key": key}
    before = db_session.query(Order).count()
    first = client.post("/api/orders", json=payload, headers=headers)
    assert first.status_code == 201, first.text
    # The first response is assumed to have disappeared at the network boundary.
    replay = client.post("/api/orders", json=payload, headers=headers)
    assert replay.status_code == 201, replay.text
    assert replay.json()["id"] == first.json()["id"]

    db_session.expire_all()
    assert db_session.query(Order).count() == before + 1
    assert db_session.query(ProductIMEI).filter_by(
        product_id=product["id"], vendido=True,
    ).count() == 1
    stock = db_session.query(Stock).filter_by(
        product_id=product["id"], location_id=location.id,
    ).one()
    assert stock.cantidad_disponible == 0

    changed = client.post(
        "/api/orders", json={**payload, "customer_name": "Otro pedido"},
        headers=headers,
    )
    assert changed.status_code == 409, changed.text
    assert db_session.query(Order).count() == before + 1
