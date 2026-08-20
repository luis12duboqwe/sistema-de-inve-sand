from app.models import Location, Order

from .helpers import seed_location_and_sales_profile, seed_product


def _order_payload(sales_profile, location, product, *, phone: str = "99999999", payment=None):
    payload = {
        "sales_profile_slug": sales_profile.slug,
        "source_location_id": location.id,
        "canal": "whatsapp",
        "customer_name": "Cliente Test",
        "customer_phone": phone,
        "metodo_pago": "efectivo",
        "items": [
            {
                "product_id": product["id"],
                "cantidad": 1,
                "imeis": ["111111111111111"],
                "precio_unitario": 1000,
            }
        ],
    }
    if payment is not None:
        payload["payment_breakdown"] = payment
    return payload


def _complete_order(client, order_id: int):
    response = client.put(
        f"/api/orders/{order_id}/status",
        json={"estado": "completada"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["estado"] == "completada"
    return response.json()


def test_health_ok(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    payload = res.json()
    assert payload.get("status") in {"healthy", "ok"}


def test_product_creation_and_listing(client, db_session):
    location, _ = seed_location_and_sales_profile(db_session)
    created = seed_product(client, location.id)

    assert created["stock_disponible"] == 1
    assert created.get("imeis") == ["111111111111111"]

    res = client.get("/api/products?per_page=50")
    assert res.status_code == 200
    items = res.json().get("items", [])
    sku_list = [p["sku"] for p in items]
    assert created["sku"] in sku_list


def test_order_create_and_cancel_restores_stock(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id)

    create_res = client.post("/api/orders", json=_order_payload(sales_profile, location, product))
    assert create_res.status_code == 201, create_res.text
    order = create_res.json()
    assert order["estado"] == "pendiente"

    list_after_sale = client.get("/api/products?per_page=50").json()["items"]
    sold_product = next(p for p in list_after_sale if p["id"] == product["id"])
    assert sold_product["stock_disponible"] == 0

    cancel_res = client.post(f"/api/orders/{order['id']}/cancel?reason=test")
    assert cancel_res.status_code == 200, cancel_res.text
    assert cancel_res.json()["estado"] == "cancelada"

    list_after_cancel = client.get("/api/products?per_page=50").json()["items"]
    restored_product = next(p for p in list_after_cancel if p["id"] == product["id"])
    assert restored_product["stock_disponible"] == 1


def test_pending_order_cannot_be_returned(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id)
    create_res = client.post(
        "/api/orders",
        json=_order_payload(sales_profile, location, product, phone="70000001"),
    )
    assert create_res.status_code == 201, create_res.text

    return_res = client.post(
        "/api/returns",
        json={
            "order_id": create_res.json()["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 1,
                    "condition": "nuevo",
                    "action": "refund",
                    "imei": "111111111111111",
                }
            ],
        },
    )
    assert return_res.status_code == 400
    assert "después de completar" in return_res.json().get("detail", "")


def test_returns_reject_over_return_and_invalid_imei(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id)

    create_res = client.post(
        "/api/orders",
        json=_order_payload(sales_profile, location, product, phone="88888888"),
    )
    assert create_res.status_code == 201, create_res.text
    order = create_res.json()
    _complete_order(client, order["id"])

    over_res = client.post(
        "/api/returns",
        json={
            "order_id": order["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 2,
                    "condition": "nuevo",
                    "action": "refund",
                    "imei": "111111111111111",
                }
            ],
        },
    )
    assert over_res.status_code == 400

    bad_imei_res = client.post(
        "/api/returns",
        json={
            "order_id": order["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 1,
                    "condition": "nuevo",
                    "action": "refund",
                    "imei": "999999999999999",
                }
            ],
        },
    )
    assert bad_imei_res.status_code == 400


def test_return_accepts_finalized_sale_and_restocks(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id)

    create_res = client.post(
        "/api/orders",
        json=_order_payload(sales_profile, location, product, phone="77777777"),
    )
    assert create_res.status_code == 201, create_res.text
    order = create_res.json()
    _complete_order(client, order["id"])

    ret_res = client.post(
        "/api/returns",
        json={
            "order_id": order["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 1,
                    "condition": "nuevo",
                    "action": "refund",
                    "imei": "111111111111111",
                }
            ],
        },
    )
    assert ret_res.status_code == 201, ret_res.text

    product_after_return = client.get("/api/products?per_page=50").json()["items"]
    restored = next(p for p in product_after_return if p["id"] == product["id"])
    assert restored["stock_disponible"] == 1

    imeis_available = client.get(f"/api/products/{product['id']}/imeis?location_id={location.id}").json()
    assert "111111111111111" in imeis_available


def test_sale_with_return_cannot_be_cancelled_or_double_restocked(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id)
    created = client.post(
        "/api/orders",
        json=_order_payload(sales_profile, location, product, phone="70000002"),
    )
    assert created.status_code == 201, created.text
    order_id = created.json()["id"]
    _complete_order(client, order_id)

    returned = client.post(
        "/api/returns",
        json={
            "order_id": order_id,
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 1,
                    "condition": "nuevo",
                    "action": "refund",
                    "imei": "111111111111111",
                }
            ],
        },
    )
    assert returned.status_code == 201, returned.text

    cancel = client.post(f"/api/orders/{order_id}/cancel?reason=should-not-double-restock")
    assert cancel.status_code == 409, cancel.text

    products = client.get("/api/products?per_page=50").json()["items"]
    restored = next(p for p in products if p["id"] == product["id"])
    assert restored["stock_disponible"] == 1

    order = db_session.query(Order).filter(Order.id == order_id).first()
    assert order is not None
    assert order.estado == "completada"


def test_completing_sale_sets_real_completion_timestamp(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id)
    created = client.post(
        "/api/orders",
        json=_order_payload(sales_profile, location, product, phone="70000003"),
    )
    assert created.status_code == 201, created.text
    order_id = created.json()["id"]

    _complete_order(client, order_id)
    db_session.expire_all()
    stored = db_session.query(Order).filter(Order.id == order_id).first()
    assert stored is not None
    assert stored.completed_at is not None
    assert stored.validada_at is None


def test_backend_rejects_mixed_payment_breakdown_that_does_not_match_total(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id)
    payload = _order_payload(
        sales_profile,
        location,
        product,
        phone="70000004",
        payment=[
            {"method": "efectivo", "amount": 600},
            {"method": "tarjeta", "amount": 300},
        ],
    )
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 400, response.text
    assert "desglose de pagos" in response.json().get("detail", "")

    db_session.expire_all()
    assert db_session.query(Order).filter(Order.customer_phone == "70000004").count() == 0


def test_backend_accepts_balanced_mixed_payment_breakdown(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id)
    payload = _order_payload(
        sales_profile,
        location,
        product,
        phone="70000005",
        payment=[
            {"method": "efectivo", "amount": 600},
            {"method": "tarjeta", "amount": 400},
        ],
    )
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 201, response.text


def test_serialized_product_rejects_numeric_only_stock_adjustment(client, db_session):
    location, _ = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id)
    response = client.post(
        f"/api/products/{product['id']}/stock/location/{location.id}?cantidad=2"
    )
    assert response.status_code == 409, response.text
    assert "serializados" in response.json().get("detail", "")


def test_stock_history_is_read_only(client):
    response = client.post("/api/stock-history/", json={})
    assert response.status_code == 405, response.text


def test_stock_transfer_confirm_moves_stock(client, db_session):
    location_from, _ = seed_location_and_sales_profile(db_session)
    location_to = Location(nombre="Bodega Test", tipo="bodega", direccion="", telefono=None, activo=True)
    db_session.add(location_to)
    db_session.commit()
    db_session.refresh(location_to)

    product = seed_product(client, location_from.id)
    transfer_payload = {
        "product_id": product["id"],
        "from_location_id": location_from.id,
        "to_location_id": location_to.id,
        "cantidad": 1,
        "imeis": ["111111111111111"],
        "created_by": "tester",
    }

    create_transfer_res = client.post("/api/stock-transfers", json=transfer_payload)
    assert create_transfer_res.status_code == 201, create_transfer_res.text
    transfer = create_transfer_res.json()
    assert transfer["estado"] == "pendiente"

    product_after_reserve = client.get("/api/products?per_page=50").json()["items"]
    reserved = next(p for p in product_after_reserve if p["id"] == product["id"])
    assert reserved["stock_disponible"] == 0

    confirm_res = client.post(
        f"/api/stock-transfers/{transfer['id']}/confirm",
        json={"confirmed_by": "tester", "scanned_imeis": ["111111111111111"]},
    )
    assert confirm_res.status_code == 200, confirm_res.text
    assert confirm_res.json()["estado"] == "confirmada"

    product_after_confirm = client.get("/api/products?per_page=50").json()["items"]
    moved = next(p for p in product_after_confirm if p["id"] == product["id"])
    assert moved["stock_disponible"] == 1
    stock_items = moved.get("stock_items") or []
    origin_entry = next(s for s in stock_items if s["location_id"] == location_from.id)
    dest_entry = next(s for s in stock_items if s["location_id"] == location_to.id)
    assert origin_entry["cantidad_disponible"] == 0
    assert origin_entry["cantidad_reservada"] == 0
    assert dest_entry["cantidad_disponible"] == 1


def test_pending_transfer_blocks_sale_until_cancelled(client, db_session):
    location_from, sales_profile = seed_location_and_sales_profile(db_session)
    location_to = Location(nombre="Bodega Destino", tipo="bodega", direccion="", telefono=None, activo=True)
    db_session.add(location_to)
    db_session.commit()
    db_session.refresh(location_to)
    product = seed_product(client, location_from.id)

    transfer_payload = {
        "product_id": product["id"],
        "from_location_id": location_from.id,
        "to_location_id": location_to.id,
        "cantidad": 1,
        "imeis": ["111111111111111"],
        "created_by": "tester",
    }
    create_transfer_res = client.post("/api/stock-transfers", json=transfer_payload)
    assert create_transfer_res.status_code == 201, create_transfer_res.text
    transfer = create_transfer_res.json()

    order_payload = _order_payload(sales_profile, location_from, product, phone="66666666")
    sale_res = client.post("/api/orders", json=order_payload)
    assert sale_res.status_code == 409, sale_res.text

    cancel_res = client.delete(f"/api/stock-transfers/{transfer['id']}")
    assert cancel_res.status_code == 204, cancel_res.text

    sale_res_2 = client.post("/api/orders", json=order_payload)
    assert sale_res_2.status_code == 201, sale_res_2.text


def test_pending_transfer_blocks_sale_until_rejected(client, db_session):
    location_from, sales_profile = seed_location_and_sales_profile(db_session)
    location_to = Location(nombre="Bodega Destino 2", tipo="bodega", direccion="", telefono=None, activo=True)
    db_session.add(location_to)
    db_session.commit()
    db_session.refresh(location_to)
    product = seed_product(client, location_from.id)

    transfer_payload = {
        "product_id": product["id"],
        "from_location_id": location_from.id,
        "to_location_id": location_to.id,
        "cantidad": 1,
        "imeis": ["111111111111111"],
        "created_by": "tester",
    }
    create_transfer_res = client.post("/api/stock-transfers", json=transfer_payload)
    assert create_transfer_res.status_code == 201, create_transfer_res.text
    transfer = create_transfer_res.json()

    order_payload = _order_payload(sales_profile, location_from, product, phone="55555555")
    sale_res = client.post("/api/orders", json=order_payload)
    assert sale_res.status_code == 409, sale_res.text

    reject_res = client.post(
        f"/api/stock-transfers/{transfer['id']}/reject",
        json={"rejection_reason": "test"},
    )
    assert reject_res.status_code == 200, reject_res.text
    assert reject_res.json()["estado"] == "rechazada"

    sale_res_2 = client.post("/api/orders", json=order_payload)
    assert sale_res_2.status_code == 201, sale_res_2.text


def test_confirm_transfer_requires_reserved_stock_and_moves_imeis(client, db_session):
    location_from, _ = seed_location_and_sales_profile(db_session)
    location_to = Location(nombre="Bodega Confirm", tipo="bodega", direccion="", telefono=None, activo=True)
    db_session.add(location_to)
    db_session.commit()
    db_session.refresh(location_to)
    product = seed_product(client, location_from.id)

    transfer_payload = {
        "product_id": product["id"],
        "from_location_id": location_from.id,
        "to_location_id": location_to.id,
        "cantidad": 1,
        "imeis": ["111111111111111"],
        "created_by": "tester",
    }
    create_transfer_res = client.post("/api/stock-transfers", json=transfer_payload)
    assert create_transfer_res.status_code == 201, create_transfer_res.text
    transfer = create_transfer_res.json()

    confirm_res = client.post(
        f"/api/stock-transfers/{transfer['id']}/confirm",
        json={"confirmed_by": "tester", "scanned_imeis": ["111111111111111"]},
    )
    assert confirm_res.status_code == 200, confirm_res.text
    assert confirm_res.json()["estado"] == "confirmada"

    create_transfer_conflict = client.post("/api/stock-transfers", json=transfer_payload)
    assert create_transfer_conflict.status_code == 409
    assert "Stock insuficiente" in create_transfer_conflict.json().get("detail", "")
