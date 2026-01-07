from .helpers import seed_location_and_sales_profile, seed_product


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

    order_payload = {
        "sales_profile_slug": sales_profile.slug,
        "source_location_id": location.id,
        "canal": "whatsapp",
        "customer_name": "Cliente Test",
        "customer_phone": "99999999",
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

    create_res = client.post("/api/orders", json=order_payload)
    assert create_res.status_code == 201, create_res.text
    order = create_res.json()
    assert order["estado"] == "pendiente"

    # Stock debe quedar en 0 tras la venta
    list_after_sale = client.get("/api/products?per_page=50").json()["items"]
    sold_product = next(p for p in list_after_sale if p["id"] == product["id"])
    assert sold_product["stock_disponible"] == 0

    cancel_res = client.post(f"/api/orders/{order['id']}/cancel?reason=test")
    assert cancel_res.status_code == 200, cancel_res.text
    cancelled = cancel_res.json()
    assert cancelled["estado"] == "cancelada"

    list_after_cancel = client.get("/api/products?per_page=50").json()["items"]
    restored_product = next(p for p in list_after_cancel if p["id"] == product["id"])
    assert restored_product["stock_disponible"] == 1


def test_returns_reject_over_return_and_invalid_imei(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id)

    order_payload = {
        "sales_profile_slug": sales_profile.slug,
        "source_location_id": location.id,
        "canal": "whatsapp",
        "customer_name": "Cliente Test",
        "customer_phone": "88888888",
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

    create_res = client.post("/api/orders", json=order_payload)
    assert create_res.status_code == 201, create_res.text
    order = create_res.json()

    # Over-return (quantity > purchased)
    return_payload = {
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
    }
    over_res = client.post("/api/returns", json=return_payload)
    assert over_res.status_code == 400

    # Wrong IMEI (not in order)
    return_payload_bad_imei = {
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
    }
    bad_imei_res = client.post("/api/returns", json=return_payload_bad_imei)
    assert bad_imei_res.status_code == 400


def test_return_accepts_valid_imei_and_restocks(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id)

    order_payload = {
        "sales_profile_slug": sales_profile.slug,
        "source_location_id": location.id,
        "canal": "whatsapp",
        "customer_name": "Cliente Test",
        "customer_phone": "77777777",
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

    create_res = client.post("/api/orders", json=order_payload)
    assert create_res.status_code == 201, create_res.text
    order = create_res.json()

    return_payload = {
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
    }

    ret_res = client.post("/api/returns", json=return_payload)
    assert ret_res.status_code == 201, ret_res.text

    product_after_return = client.get("/api/products?per_page=50").json()["items"]
    restored = next(p for p in product_after_return if p["id"] == product["id"])
    assert restored["stock_disponible"] == 1

    imeis_available = client.get(f"/api/products/{product['id']}/imeis?location_id={location.id}").json()
    assert "111111111111111" in imeis_available


def test_stock_transfer_confirm_moves_stock(client, db_session):
    # Origen y destino
    location_from, _ = seed_location_and_sales_profile(db_session)
    # Crear ubicación destino
    from app.models import Location

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

    # Al reservar, el stock libre en origen debe quedar en 0
    product_after_reserve = client.get("/api/products?per_page=50").json()["items"]
    reserved = next(p for p in product_after_reserve if p["id"] == product["id"])
    assert reserved["stock_disponible"] == 0

    confirm_payload = {
        "confirmed_by": "tester",
        "scanned_imeis": ["111111111111111"],
    }
    confirm_res = client.post(f"/api/stock-transfers/{transfer['id']}/confirm", json=confirm_payload)
    assert confirm_res.status_code == 200, confirm_res.text
    confirmed = confirm_res.json()
    assert confirmed["estado"] == "confirmada"

    product_after_confirm = client.get("/api/products?per_page=50").json()["items"]
    moved = next(p for p in product_after_confirm if p["id"] == product["id"])
    assert moved["stock_disponible"] == 1

    # Validar stock_items por ubicación
    stock_items = moved.get("stock_items") or []
    origin_entry = next(s for s in stock_items if s["location_id"] == location_from.id)
    dest_entry = next(s for s in stock_items if s["location_id"] == location_to.id)
    assert origin_entry["cantidad_disponible"] == 0
    assert origin_entry["cantidad_reservada"] == 0
    assert dest_entry["cantidad_disponible"] == 1


def test_pending_transfer_blocks_sale_until_cancelled(client, db_session):
    location_from, sales_profile = seed_location_and_sales_profile(db_session)

    from app.models import Location

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
    assert transfer["estado"] == "pendiente"

    order_payload = {
        "sales_profile_slug": sales_profile.slug,
        "source_location_id": location_from.id,
        "canal": "whatsapp",
        "customer_name": "Cliente Conflicto",
        "customer_phone": "66666666",
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

    # Mientras la transferencia está pendiente, el stock está reservado y la venta debe fallar
    sale_res = client.post("/api/orders", json=order_payload)
    assert sale_res.status_code == 409, sale_res.text

    # Cancelar la transferencia debe liberar la reserva
    cancel_res = client.delete(f"/api/stock-transfers/{transfer['id']}")
    assert cancel_res.status_code == 204, cancel_res.text

    # Ahora la venta debe permitirse
    sale_res_2 = client.post("/api/orders", json=order_payload)
    assert sale_res_2.status_code == 201, sale_res_2.text


def test_pending_transfer_blocks_sale_until_rejected(client, db_session):
    location_from, sales_profile = seed_location_and_sales_profile(db_session)

    from app.models import Location

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
    assert transfer["estado"] == "pendiente"

    order_payload = {
        "sales_profile_slug": sales_profile.slug,
        "source_location_id": location_from.id,
        "canal": "whatsapp",
        "customer_name": "Cliente Rechazo",
        "customer_phone": "55555555",
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

    sale_res = client.post("/api/orders", json=order_payload)
    assert sale_res.status_code == 409, sale_res.text

    reject_payload = {"rejection_reason": "test"}
    reject_res = client.post(f"/api/stock-transfers/{transfer['id']}/reject", json=reject_payload)
    assert reject_res.status_code == 200, reject_res.text
    assert reject_res.json()["estado"] == "rechazada"

    sale_res_2 = client.post("/api/orders", json=order_payload)
    assert sale_res_2.status_code == 201, sale_res_2.text


def test_confirm_transfer_requires_reserved_stock_and_moves_imeis(client, db_session):
    # Origen y destino
    location_from, sales_profile = seed_location_and_sales_profile(db_session)
    from app.models import Location, Stock

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
    assert transfer["estado"] == "pendiente"

    # Confirmación exitosa con IMEI escaneado
    confirm_payload = {
        "confirmed_by": "tester",
        "scanned_imeis": ["111111111111111"],
    }
    confirm_res = client.post(f"/api/stock-transfers/{transfer['id']}/confirm", json=confirm_payload)
    assert confirm_res.status_code == 200, confirm_res.text
    assert confirm_res.json()["estado"] == "confirmada"

    # Crear una nueva transferencia para provocar conflicto de reserva faltante
    transfer_payload_conflict = {
        "product_id": product["id"],
        "from_location_id": location_from.id,
        "to_location_id": location_to.id,
        "cantidad": 1,
        "imeis": ["111111111111111"],
        "created_by": "tester",
    }
    create_transfer_conflict = client.post("/api/stock-transfers", json=transfer_payload_conflict)
    assert create_transfer_conflict.status_code == 409
    assert "Stock insuficiente" in create_transfer_conflict.json().get("detail", "")
