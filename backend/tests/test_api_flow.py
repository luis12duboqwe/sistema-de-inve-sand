from app.models import Location, Order

from .helpers import seed_location_and_sales_profile, seed_product


def _order_payload(
    sales_profile,
    location,
    product,
    *,
    phone: str = "99999999",
    payment=None,
    imei: str = "111111111111111",
):
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
                "imeis": [imei],
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
                    "condition": "defectuoso",
                    "action": "warranty_exchange",
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
                    "condition": "defectuoso",
                    "action": "warranty_exchange",
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
                    "condition": "defectuoso",
                    "action": "warranty_exchange",
                    "imei": "999999999999999",
                }
            ],
        },
    )
    assert bad_imei_res.status_code == 400


def test_warranty_exchange_accepts_finalized_sale_and_tracks_stock(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    sold_imei = "111111111111111"
    replacement_imei = "222222222222222"
    product = seed_product(
        client,
        location.id,
        imei_values=[sold_imei, replacement_imei],
    )

    create_res = client.post(
        "/api/orders",
        json=_order_payload(sales_profile, location, product, phone="77777777", imei=sold_imei),
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
                    "condition": "defectuoso",
                    "action": "warranty_exchange",
                    "imei": sold_imei,
                    "replacement_imei": replacement_imei,
                }
            ],
        },
    )
    assert ret_res.status_code == 201, ret_res.text
    assert ret_res.json()["items"][0]["action"] == "warranty_exchange"

    product_after_return = client.get("/api/products?per_page=50").json()["items"]
    exchanged = next(p for p in product_after_return if p["id"] == product["id"])
    assert exchanged["stock_disponible"] == 0

    imeis_available = client.get(f"/api/products/{product['id']}/imeis?location_id={location.id}").json()
    assert sold_imei not in imeis_available
    assert replacement_imei not in imeis_available


def test_sale_with_warranty_cannot_be_cancelled_or_double_restocked(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    sold_imei = "111111111111111"
    replacement_imei = "222222222222222"
    product = seed_product(
        client,
        location.id,
        imei_values=[sold_imei, replacement_imei],
    )
    created = client.post(
        "/api/orders",
        json=_order_payload(sales_profile, location, product, phone="70000002", imei=sold_imei),
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
                    "condition": "defectuoso",
                    "action": "warranty_exchange",
                    "imei": sold_imei,
                    "replacement_imei": replacement_imei,
                }
            ],
        },
    )
    assert returned.status_code == 201, returned.text

    cancel = client.post(f"/api/orders/{order_id}/cancel?reason=should-not-double-restock")
    assert cancel.status_code == 409, cancel.text

    products = client.get("/api/products?per_page=50").json()["items"]
    exchanged = next(p for p in products if p["id"] == product["id"])
    assert exchanged["stock_disponible"] == 0

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

def test_mixed_card_payment_applies_surcharge_only_to_card_portion(client, db_session):
    from decimal import Decimal
    from uuid import uuid4
    from app.models import Bank, Order

    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id)
    bank = Bank(name="Banco Mixto " + uuid4().hex[:10], normal_card_rate=Decimal("0.0500"), active=True)
    db_session.add(bank)
    db_session.commit()
    payload = _order_payload(sales_profile, location, product, phone="70008821", payment=[
        {"method": "efectivo", "amount": "600.00"},
        {"method": "tarjeta", "amount": "420.00"},
    ])
    payload["financing_data"] = {"bank_id": bank.id, "months": 0, "down_payment": 0}
    result = client.post("/api/orders", json=payload)
    assert result.status_code == 201, result.text
    order = db_session.query(Order).filter(Order.customer_phone == "70008821").one()
    assert Decimal(str(order.total)) == Decimal("1020.00")
    assert '"surcharge": 20.0' in (order.financing_details or "")


def test_mixed_card_rejects_wrong_surcharge_without_creating_order(client, db_session):
    from decimal import Decimal
    from uuid import uuid4
    from app.models import Bank, Order

    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id)
    bank = Bank(name="Banco Mixto Rechazo " + uuid4().hex[:8], normal_card_rate=Decimal("0.0500"), active=True)
    db_session.add(bank)
    db_session.commit()
    payload = _order_payload(sales_profile, location, product, phone="70008822", payment=[
        {"method": "efectivo", "amount": "600.00"},
        {"method": "tarjeta", "amount": "400.00"},
    ])
    payload["financing_data"] = {"bank_id": bank.id, "months": 0}
    result = client.post("/api/orders", json=payload)
    assert result.status_code == 400, result.text
    db_session.expire_all()
    assert db_session.query(Order).filter(Order.customer_phone == "70008822").count() == 0


def test_sale_audit_failure_rolls_back_order_stock_and_imei(client, db_session, monkeypatch):
    import pytest
    from app.models import Order, Stock, ProductIMEI
    from app.routers import orders as orders_router

    location, profile = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id)
    before_stock = db_session.query(Stock).filter_by(
        product_id=product["id"], location_id=location.id,
    ).one().cantidad_disponible

    def failed_audit(*args, **kwargs):
        raise RuntimeError("injected audit storage failure")

    monkeypatch.setattr(orders_router, "log_audit_event", failed_audit)
    payload = _order_payload(profile, location, product, phone="70000980")
    with pytest.raises(RuntimeError, match="injected audit"):
        client.post("/api/orders", json=payload)

    db_session.expire_all()
    assert db_session.query(Order).filter_by(customer_phone="70000980").count() == 0
    stock = db_session.query(Stock).filter_by(
        product_id=product["id"], location_id=location.id,
    ).one()
    assert stock.cantidad_disponible == before_stock
    imei = db_session.query(ProductIMEI).filter_by(imei="111111111111111").one()
    assert imei.vendido is False
    assert imei.order_id is None


def test_manual_nonserialized_stock_audit_failure_rollback(client, db_session, monkeypatch):
    import pytest
    from decimal import Decimal
    from uuid import uuid4
    from app.models import Product, Stock, Location, StockHistory
    from app.routers import products as products_router

    tag = uuid4().hex[:12]
    location = Location(nombre=f"Ajuste Seguro {tag}", tipo="tienda", activo=True)
    product = Product(sku=f"SAFE-STOCK-{tag}", nombre="Accesorio prueba",
                      categoria="accesorio", marca="Test", modelo=tag,
                      condicion="nuevo", precio=Decimal("50"), activo=True,
                      is_serialized=False)
    db_session.add_all([location, product])
    db_session.flush()
    stock = Stock(product_id=product.id, location_id=location.id, cantidad_disponible=5)
    db_session.add(stock)
    db_session.commit()

    def failed_audit(*args, **kwargs):
        raise RuntimeError("injected stock audit failure")

    monkeypatch.setattr(products_router, "log_audit_event", failed_audit)
    with pytest.raises(RuntimeError, match="injected stock audit"):
        client.post(f"/api/products/{product.id}/stock/location/{location.id}?cantidad=7")

    db_session.expire_all()
    persisted = db_session.query(Stock).filter_by(
        product_id=product.id, location_id=location.id,
    ).one()
    assert persisted.cantidad_disponible == 5
    assert db_session.query(StockHistory).filter_by(
        product_id=product.id, referencia_tipo="manual_adjustment",
    ).count() == 0


def test_dashboard_and_location_stock_value_convert_usd_to_hnl(client, db_session):
    from decimal import Decimal
    from uuid import uuid4
    from app.models import Product, Stock, Location

    tag = uuid4().hex[:10]
    location = Location(nombre=f"Sede Divisa {tag}", tipo="tienda", activo=True)
    usd = Product(
        sku=f"USD-{tag}", nombre="Accesorio USD", categoria="accesorio",
        marca="Test", modelo="Dolar", condicion="nuevo", precio=Decimal("100"),
        costo=Decimal("100"), moneda="USD", activo=True, is_serialized=False,
    )
    hnl = Product(
        sku=f"HNL-{tag}", nombre="Accesorio HNL", categoria="accesorio",
        marca="Test", modelo="Lempira", condicion="nuevo", precio=Decimal("100"),
        costo=Decimal("100"), moneda="Lps", activo=True, is_serialized=False,
    )
    db_session.add_all([location, usd, hnl])
    db_session.flush()
    db_session.add_all([
        Stock(product_id=usd.id, location_id=location.id, cantidad_disponible=1),
        Stock(product_id=hnl.id, location_id=location.id, cantidad_disponible=1),
    ])
    db_session.commit()

    dashboard = client.get(f"/api/reports/dashboard?location_id={location.id}")
    assert dashboard.status_code == 200, dashboard.text
    assert Decimal(str(dashboard.json()["total_inventory_value"])) == Decimal("2600")

    summary = client.get("/api/reports/stock-summary-by-location")
    assert summary.status_code == 200, summary.text
    row = next(item for item in summary.json() if item["location_id"] == location.id)
    assert Decimal(str(row["valor_inventario"])) == Decimal("2600")
